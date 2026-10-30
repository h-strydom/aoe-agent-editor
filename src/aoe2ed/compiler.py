"""Compile a campaign spec (YAML/JSON) into scenarios, previews and a .aoe2campaign.

Spec shape (see specs/campaign.schema.md and examples/):

  name: crucible                 # internal campaign name; the campaign bank is scoped by it
  title: The Crucible            # optional display text
  missions:
    - id: hub
      file: crucible_1_hub       # scenario file name (no extension)
      map: {...}                 # aoe2ed.mapgen.MapSpec as a dict   (or)  base: <scenario path/name>
      areas: {name: [x1,y1,x2,y2]}   points: {name: [x,y]}   # added to the map's named areas
      players: {1: {civilization: BRITONS, ...}}             # player_set fields
      diplomacy: [{player: 1, others: [2], state: ENEMY}]
      options: {...}  messages: {...}
      units: [{player, type, x, y} | {player, type, at: <area/point name>}]
      blocks: [{use: <block name>, ...params}]               # aoe2ed.blocks.BLOCKS
      triggers: [<trigger dict>]                             # raw triggers, after blocks
      xs: "<extra XS>"
      telemetry: true | {players, track_vars, interval_sec, events}

Inside block params and triggers:
  {"$helper": "escalating", ...kwargs}  is replaced by the helper's result
  {"$secs": 2700}                        game seconds, scaled in test mode like block timers
  "area": "<name>" / "location": "<name>"  resolve to the named area / point
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import blocks as B
from . import triggers as T
from .campaign import Campaign
from .config import paths
from .session import SESSIONS, backup_file
from .tools import load_all

TOOLS = load_all()


@dataclass
class MissionResult:
    id: str
    file: str
    scenario_path: str
    preview: str | None
    triggers: int
    variables: dict[str, int]
    areas: dict[str, list[int]]
    xs_ok: bool
    xs_diagnostics: list[dict] = field(default_factory=list)
    telemetry: dict | None = None
    handle: str | None = None


def load_spec(spec: str | Path | dict) -> dict:
    if isinstance(spec, dict):
        return spec
    p = Path(spec)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".yaml", ".yml"):
        import yaml
        return yaml.safe_load(text)
    return json.loads(text)


# ---------------------------------------------------------------- value directives

def _expand(value: Any, ctx: B.Ctx) -> Any:
    if isinstance(value, dict):
        if "$secs" in value:
            return ctx.secs(value["$secs"])
        if "$helper" in value:
            args = {k: _expand(v, ctx) for k, v in value.items() if k != "$helper"}
            name = value["$helper"]
            if name not in B.HELPERS:
                raise ValueError(f"Unknown helper '{name}'. Helpers: {sorted(B.HELPERS)}")
            fn = B.HELPERS[name]
            if next(iter(inspect.signature(fn).parameters), None) == "ctx":
                return fn(ctx, **args)
            return fn(**args)
        out = {}
        for k, v in value.items():
            v = _expand(v, ctx)
            if k == "area" and isinstance(v, str):
                v = list(ctx.area(v))
            elif k == "location" and isinstance(v, str):
                v = list(ctx.point(v))
            out[k] = v
        return out
    if isinstance(value, list):
        return [_expand(v, ctx) for v in value]
    return value


# ---------------------------------------------------------------- one mission

def build_mission(m: dict, *, out_dir: Path, time_scale: float = 1.0, render: bool = True) -> MissionResult:
    mid = m["id"]
    file = m.get("file", mid)
    if "map" in m:
        from .mapgen import generate
        gen = generate(m["map"])
        o = SESSIONS.adopt(gen.scenario)
        areas = {k: tuple(v) for k, v in gen.areas.items()}
    elif "base" in m:
        o = SESSIONS.get(TOOLS["scenario_open"](path=m["base"])["handle"])
        areas = {}
    else:
        o = SESSIONS.new(m.get("map_size", 120))
        areas = {}
    h, s = o.handle, o.scenario
    areas.update({k: tuple(v) for k, v in (m.get("areas") or {}).items()})
    points = {k: tuple(v) for k, v in (m.get("points") or {}).items()}
    ctx = B.Ctx(s, areas=areas, points=points, time_scale=time_scale, test_mode=time_scale != 1.0)

    for pid, fields in (m.get("players") or {}).items():
        TOOLS["player_set"](handle=h, player=int(pid), fields=fields)
    for d in m.get("diplomacy") or []:
        TOOLS["diplomacy_set"](handle=h, **d)
    if m.get("options"):
        TOOLS["options_set"](handle=h, fields=m["options"])
    if m.get("messages"):
        TOOLS["messages_set"](handle=h, fields=m["messages"])
    units = []
    for u in m.get("units") or []:
        u = dict(u)
        if "at" in u:
            x, y = ctx.point(u.pop("at"))
            u.setdefault("x", x + 0.5)
            u.setdefault("y", y + 0.5)
        units.append(u)
    if units:
        TOOLS["units_add"](handle=h, units=units)

    for i, blk in enumerate(m.get("blocks") or []):
        blk = dict(blk)
        name = blk.pop("use")
        if name not in B.BLOCKS:
            raise ValueError(f"[{mid}] block {i}: unknown block '{name}'. Blocks: {sorted(B.BLOCKS)}")
        try:
            B.BLOCKS[name](ctx, **_expand(blk, ctx))
        except TypeError as e:
            raise ValueError(f"[{mid}] block {i} ({name}): {e}") from None
    if m.get("triggers"):
        T.add_triggers(s, _expand(m["triggers"], ctx))
    if m.get("xs"):
        ctx.xs(m["xs"])

    telem = None
    if m.get("telemetry"):
        tcfg = {} if m["telemetry"] is True else dict(m["telemetry"])
        tcfg.setdefault("track_vars", [v.name for v in s.trigger_manager.variables][:16])
        events = tcfg.pop("events", None)
        if events is None:  # mark every block-created end/complete trigger by default
            names = [t.name for t in s.trigger_manager.triggers]
            events = {n: i + 1 for i, n in enumerate(
                n for n in names if n.endswith((" End", " Complete")) or n.startswith("Wave "))}
            events = {n: i for n, i in list(events.items())[:200] if "+" not in n and "Keepalive" not in n}
        telem = B.telemetry_harness(ctx, events=events, **tcfg)
        telem["event_names"] = {v: k for k, v in events.items()}
    ctx.flush_xs()

    from .xs import check
    xs_code = "\n".join(e.message for t in s.trigger_manager.triggers for e in t.effects
                        if e.effect_type == 55 and e.message)
    xs = check(code=xs_code) if xs_code else {"ok": True, "diagnostics": []}

    out_dir.mkdir(parents=True, exist_ok=True)
    scen_path = out_dir / f"{file}.aoe2scenario"
    SESSIONS.save(h, scen_path, overwrite=True)
    preview = None
    if render:
        from .render import render_scenario
        preview = str(out_dir / f"{file}.png")
        render_scenario(s, preview, show_areas=dict(areas), title=f"{file}")
    variables = {v.name: v.variable_id for v in s.trigger_manager.variables}
    return MissionResult(mid, file, str(scen_path), preview, len(s.trigger_manager.triggers), variables,
                         {k: list(v) for k, v in areas.items()}, xs["ok"], xs["diagnostics"], telem, h)


# ---------------------------------------------------------------- campaign

def compile_campaign(spec: str | Path | dict, *, out_dir: str | Path = "out/build", test_mode: bool = False,
                     time_scale: float | None = None, install: bool = False, render: bool = True) -> dict:
    """Build every mission, lint XS, write the campaign file and a build report."""
    spec = load_spec(spec)
    out = Path(out_dir)
    scale = time_scale if time_scale is not None else (
        (spec.get("test_mode") or {}).get("time_scale", 0.1) if test_mode else 1.0)
    results = [build_mission(m, out_dir=out, time_scale=scale, render=render) for m in spec["missions"]]
    report: dict[str, Any] = {"name": spec.get("name"), "time_scale": scale, "missions": []}
    for r in results:
        report["missions"].append({
            "id": r.id, "file": r.file, "scenario": r.scenario_path, "preview": r.preview, "triggers": r.triggers,
            "xs_ok": r.xs_ok, "xs_errors": [d for d in r.xs_diagnostics if d["severity"] == "error"],
            "variables": r.variables, "areas": r.areas,
            "telemetry": None if not r.telemetry else {
                "xsdat": f"{r.file}.xsdat", "var_names": {str(i): n for n, i in r.telemetry["var_ids"].items()},
                "event_names": {str(k): v for k, v in r.telemetry["event_names"].items()}},
        })
    camp_path = None
    if spec.get("name") and (len(results) > 1 or spec.get("campaign", True)):
        camp = Campaign(spec["name"])
        for r in results:
            camp.add_scenario_file(r.scenario_path)
        camp_path = camp.write(out / f"{spec['name']}.aoe2campaign")
        report["campaign"] = str(camp_path)
    report["ok"] = all(r.xs_ok for r in results)
    if install:
        from .game import install as install_file
        installed = []
        for r in results:
            installed.append(install_file(r.scenario_path)["installed"])
        if camp_path:
            dest = paths().user_dir("campaign") / camp_path.name
            if dest.exists():
                backup_file(dest)
            installed.append(install_file(camp_path)["installed"])
        report["installed"] = installed
    (out / "build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for r in results:
        SESSIONS.close(r.handle)
    return report
