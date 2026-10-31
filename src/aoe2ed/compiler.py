"""Compile a campaign spec (YAML/JSON) into scenarios, previews and a .aoe2campaign.

Spec shape (full guide: guide("campaign-spec"); examples/):

  name: crucible                 # internal campaign name; the campaign bank is scoped by it
  title: The Crucible            # optional display text
  defaults: {...}                # mission keys every mission inherits (dict values merge one level)
  missions:
    - id: hub
      file: crucible_1_hub       # scenario file name (no extension)
      map: {...}                 # generated map (map spec)   (or)  base: <scenario path/name>
      areas: {name: [x1,y1,x2,y2]}   points: {name: [x,y]}   # added to the map's named areas
      players: {1: {civilization: BRITONS, ...}}             # player_set fields
      diplomacy: [{player: 1, others: [2], state: ENEMY}]
      options: {...}  messages: {...}
      units: [{player, type, x, y} | {player, type, at: <area/point name>, count: N, min_dist: 0}]
      blocks: [{use: <block name>, when: [conditions]?, ...params}]   # aoe2ed.blocks.BLOCKS
      triggers: [<trigger dict>]                             # raw triggers, after blocks
      xs: "<extra XS>"
      telemetry: true | {players, track_vars, interval_sec, events}

Inside block params and triggers:
  {"$helper": "escalating", ...kwargs}  is replaced by the helper's result (a list result inside a
                                         list is spliced in)
  {"$secs": 2700}                        game seconds, scaled in test mode like block timers
  "area": "<name>" / "location": "<name>"  resolve to the named area / point
"""
from __future__ import annotations

import inspect
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import blocks as B
from . import triggers as T
from .blocks.waves import near_tiles
from .campaign import Campaign
from .config import paths
from .session import SESSIONS, backup_file
from .tools import load_all

TOOLS = load_all()

TOP_KEYS = {"name", "title", "test_mode", "missions", "campaign", "defaults", "description"}
MISSION_KEYS = {"id", "file", "title", "description", "map", "base", "map_size", "areas", "points", "players",
                "diplomacy", "options", "messages", "units", "blocks", "triggers", "xs", "telemetry",
                "reveal_map"}
# REVEAL_MAP player resource (203) values, mirroring the lobby's Reveal Map setting.
REVEAL_VALUES = {"explored": 1, "visible": 2, "all_visible": 2}


class CompileError(ValueError):
    """A spec problem, with the mission and block/trigger it came from in the message."""


def _err(e: Exception) -> str:
    return str(e.args[0]) if isinstance(e, KeyError) and e.args else str(e)


def _unknown(keys, allowed: set[str], where: str) -> list[str]:
    return [f"{where}: unknown key '{k}' (ignored). Known keys: {sorted(allowed)}"
            for k in keys if k not in allowed and not str(k).startswith("x-")]


def _with_defaults(mission: dict, defaults: dict) -> dict:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in defaults.items()}
    for k, v in mission.items():
        out[k] = {**out[k], **v} if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


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
    warnings: list[str] = field(default_factory=list)


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
        out_list = []
        for v in value:
            x = _expand(v, ctx)
            if isinstance(v, dict) and "$helper" in v and isinstance(x, list):
                out_list.extend(x)  # e.g. spawn inside a longer effects list
            else:
                out_list.append(x)
        return out_list
    return value


# ---------------------------------------------------------------- one mission

def build_mission(m: dict, *, out_dir: Path, time_scale: float = 1.0, render: bool = True,
                  reveal_map: str | None = None) -> MissionResult:
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

    def step(where: str, fn):
        try:
            return fn()
        except CompileError:
            raise
        except Exception as e:
            raise CompileError(f"[{mid}] {where}: {_err(e)}") from None

    for pid, fields in (m.get("players") or {}).items():
        step(f"players.{pid}", lambda: TOOLS["player_set"](handle=h, player=int(pid), fields=fields))
    # Verified in game: the default AI resigns once it thinks it has lost (frontier M3 resigned after
    # one building fell), ending trigger-driven missions early. Computer players get no AI script
    # unless the spec asks for one with players.<n>.ai.
    # Every active player except 1 counts as a computer player (blank scenarios mark them human, and
    # the game then fills the slot with the default AI) unless the spec sets `human` or `ai`.
    specified = {int(k) for k, v in (m.get("players") or {}).items()
                 if isinstance(v, dict) and ("ai" in v or "human" in v)}
    from .tools.world import set_ai
    for p in s.player_manager.players[2:]:
        if p.active and p.player_id not in specified:
            p.human = False
            set_ai(p, "none")
    for d in m.get("diplomacy") or []:
        step("diplomacy", lambda: TOOLS["diplomacy_set"](handle=h, **d))
    if m.get("options"):
        step("options", lambda: TOOLS["options_set"](handle=h, fields=m["options"]))
    if m.get("messages"):
        step("messages", lambda: TOOLS["messages_set"](handle=h, fields=m["messages"]))
    units = []
    taken: set[tuple[int, int]] = set()  # tiles used by `at:` placements, so entries never stack
    for i, u in enumerate(m.get("units") or []):
        u = dict(u)
        count, min_dist = int(u.pop("count", 1)), float(u.pop("min_dist", 0))
        if "at" in u:
            at = u.pop("at")
            tiles = step(f"units {i}", lambda: near_tiles(ctx, at, count, min_dist, taken))
            for x, y in tiles:
                units.append({**u, "x": x + 0.5, "y": y + 0.5})
        elif count > 1:
            raise CompileError(f"[{mid}] units {i}: 'count' needs 'at' (a point or area name)")
        else:
            units.append(u)
    if units:
        step("units", lambda: TOOLS["units_add"](handle=h, units=units))

    tm = s.trigger_manager
    # Raw triggers exist as empty shells first so blocks can reference them by name (e.g.
    # done_effects: activate "Caravan Victory"); they are filled after the blocks and moved last.
    raw_specs = m.get("triggers") or []
    shells = step("triggers", lambda: T.create_shells(s, [
        {k: v for k, v in t.items() if k not in ("conditions", "effects")} for t in raw_specs]))
    for i, blk in enumerate(m.get("blocks") or []):
        blk = dict(blk)
        name = blk.pop("use", None)
        when = blk.pop("when", None)
        if name not in B.BLOCKS:
            raise CompileError(f"[{mid}] block {i}: unknown block '{name}'. Blocks: {sorted(B.BLOCKS)}")
        before = len(tm.triggers)
        step(f"block {i} ({name})", lambda: B.BLOCKS[name](ctx, **_expand(blk, ctx)))
        if when:
            new_names = [t.name for t in tm.triggers[before:]]
            step(f"block {i} ({name}) when", lambda: ctx.gate(new_names, _expand(when, ctx)))
    raw = []
    for i, t in enumerate(raw_specs):
        raw.append(step(f"trigger {i} ('{t.get('name', '?')}')", lambda: _expand(t, ctx)))
    if raw:
        step("triggers", lambda: T.fill_triggers(s, shells, raw))
        tm.move_triggers([t.trigger_id for t in shells], len(tm.triggers))
    warnings = T.stacked_spawns(raw)
    reveal = m.get("reveal_map", reveal_map)
    if reveal:
        if reveal not in REVEAL_VALUES:
            raise CompileError(f"[{mid}] reveal_map must be one of {sorted(REVEAL_VALUES)} or false")
        step("reveal_map", lambda: T.add_triggers(s, [{"name": "Reveal Map (test)", "effects": [
            {"type": "modify_resource", "tribute_list": "REVEAL_MAP", "source_player": 1,
             "quantity": REVEAL_VALUES[reveal], "operation": "SET"}]}]))
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
                         {k: list(v) for k, v in areas.items()}, xs["ok"], xs["diagnostics"], telem, h,
                         [f"[{mid}] {w}" for w in warnings])


# ---------------------------------------------------------------- campaign

def compile_campaign(spec: str | Path | dict, *, out_dir: str | Path = "out/build", test_mode: bool = False,
                     time_scale: float | None = None, install: bool = False, render: bool = True) -> dict:
    """Build every mission, lint XS, write the campaign file and a build report."""
    spec = load_spec(spec)
    out = Path(out_dir)
    if not isinstance(spec, dict) or not spec.get("missions"):
        raise CompileError("spec needs a 'missions' list")
    warnings = _unknown(spec, TOP_KEYS, "spec")
    defaults = spec.get("defaults") or {}
    warnings += _unknown(defaults, MISSION_KEYS - {"id", "file"}, "defaults")
    missions = []
    for i, m in enumerate(spec["missions"]):
        if "id" not in m:
            raise CompileError(f"mission {i}: missing 'id'")
        warnings += _unknown(m, MISSION_KEYS, f"[{m['id']}]")
        missions.append(_with_defaults(m, defaults))
    tm_cfg = spec.get("test_mode") or {}
    scale = time_scale if time_scale is not None else (tm_cfg.get("time_scale", 0.1) if test_mode else 1.0)
    # Test builds reveal the map for player 1 (so problems in the fog are visible) unless the spec's
    # test_mode sets reveal_map: false. Release builds only reveal where a mission asks for it.
    is_test = test_mode or scale != 1.0
    reveal = tm_cfg.get("reveal_map", "visible") if is_test else None
    # Build into a staging folder so a failed compile leaves out_dir untouched.
    out.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=out))
    results: list[MissionResult] = []
    try:
        for m in missions:
            results.append(build_mission(m, out_dir=staging, time_scale=scale, render=render, reveal_map=reveal))
        for f in staging.iterdir():
            os.replace(f, out / f.name)
        for r in results:
            r.scenario_path = str(out / Path(r.scenario_path).name)
            if r.preview:
                r.preview = str(out / Path(r.preview).name)
    finally:
        for r in results:
            if r.handle:
                SESSIONS.close(r.handle)
        shutil.rmtree(staging, ignore_errors=True)
    report: dict[str, Any] = {"name": spec.get("name"), "time_scale": scale, "reveal_map": reveal, "missions": [],
                              "warnings": warnings + [w for r in results for w in r.warnings]}
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
    return report
