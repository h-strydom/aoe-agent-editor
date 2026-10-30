"""Higher-level tools: blocks, map generation, previews, the campaign compiler, bank, telemetry."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

from .. import blocks as B
from ..session import SESSIONS
from . import tool


@tool
def blocks_list() -> list[dict]:
    """Building blocks (survive, waves, pad_shop, bank_load, boon_offers, run_end, anchor, ...) and
    helpers, with their parameters and docs. Use them in a campaign spec as {use: <name>, ...}."""
    out = []
    for kind, reg in (("block", B.BLOCKS), ("helper", B.HELPERS)):
        for name, fn in reg.items():
            params = [p for p in inspect.signature(fn).parameters.values() if p.name != "ctx"]
            out.append({"name": name, "kind": kind,
                        "params": [{"name": p.name, **({} if p.default is inspect.Parameter.empty
                                                        else {"default": repr(p.default)})} for p in params],
                        "doc": inspect.getdoc(fn)})
    return out


@tool
def block_apply(handle: str, block: str, params: dict, areas: dict | None = None,
                points: dict | None = None, time_scale: float = 1.0) -> dict:
    """Apply one block to an open scenario (outside the compiler). areas/points name the
    rectangles and points the block's params refer to. XS the block needs is embedded at once."""
    from ..compiler import _expand
    ctx = B.Ctx(SESSIONS.get(handle).scenario, areas={k: tuple(v) for k, v in (areas or {}).items()},
                points={k: tuple(v) for k, v in (points or {}).items()}, time_scale=time_scale)
    if block not in B.BLOCKS:
        raise ValueError(f"Unknown block '{block}'. Blocks: {sorted(B.BLOCKS)}")
    res = B.BLOCKS[block](ctx, **_expand(params, ctx))
    ctx.flush_xs()
    return res


@tool
def map_generate(spec: dict, out: str | None = None, preview: str | None = None) -> dict:
    """Generate terrain, elevation, forests, resources, player starts and named areas from a map
    spec (see guide('campaign-spec'), "Map spec": size, seed, biome, players, zones, water, elevation, cliffs,
    roads, forests, resources, units). Opens the result as a new handle; optionally saves it and
    writes a PNG preview. Returns the handle and named areas for use by blocks."""
    from ..mapgen import generate
    m = generate(spec)
    o = SESSIONS.adopt(m.scenario)
    res = {"handle": o.handle, "areas": {k: list(v) for k, v in m.areas.items()}, "stats": m.stats}
    if out:
        res["saved"] = SESSIONS.save(o.handle, out, overwrite=True)["saved"]
    if preview:
        m.render(preview)
        res["preview"] = preview
    return res


@tool
def map_preview(handle: str, out: str, areas: dict | None = None, show_trigger_areas: bool = False,
                orientation: str = "square") -> dict:
    """Render an open scenario to a PNG (terrain, elevation, units in player colors, labelled
    areas). Look at the image to check a map. orientation: square | diamond (in-game view)."""
    from ..render import render_scenario
    render_scenario(SESSIONS.get(handle).scenario, out, show_areas=areas,
                    show_trigger_areas=show_trigger_areas, orientation=orientation)
    return {"preview": out}


@tool
def compile_campaign(spec: str | dict, out_dir: str = "out/build", test_mode: bool = False,
                     time_scale: float | None = None, install: bool = False) -> dict:
    """Build a whole campaign from a spec (YAML/JSON path or dict): maps, players, blocks,
    triggers, XS, telemetry. Then lint the XS and write scenarios, PNG previews, the .aoe2campaign
    and build_report.json. test_mode scales all timers (default x0.1) for quick playtests.
    install copies everything into the game's profile folders. See guide('campaign-spec')."""
    from ..compiler import compile_campaign as _compile
    return _compile(spec, out_dir=out_dir, test_mode=test_mode, time_scale=time_scale, install=install)


@tool
def telemetry_read(xsdat: str, build_report: str | None = None, mission: str | None = None,
                   last_samples: int = 5) -> dict:
    """Decode a telemetry .xsdat written during a playtest (name like 'crucible_2_the_long_night'
    or a path). With the compile's build_report.json (+ mission id), variables and events get names.
    Returns events, the last samples and the final state."""
    from .. import telemetry
    from ..game import read_xsdat
    path = Path(read_xsdat(xsdat)["path"])
    var_names, event_names = {}, {}
    if build_report:
        rep = json.loads(Path(build_report).read_text(encoding="utf-8"))
        for m in rep["missions"]:
            if (mission and m["id"] == mission) or (not mission and Path(m["scenario"]).stem == path.stem):
                t = m.get("telemetry") or {}
                var_names = {int(k): v for k, v in t.get("var_names", {}).items()}
                event_names = {int(k): v for k, v in t.get("event_names", {}).items()}
    d = telemetry.read(path, var_names=var_names, event_names=event_names)
    if "samples" in d:
        d["sample_count"] = len(d["samples"])
        d["samples"] = d["samples"][-last_samples:]
    return d


@tool
def bank_show(campaign: str | None = None) -> dict:
    """Read the campaign bank (Store/Load Key Value data) from the profile's Player.nfp.
    Without `campaign`, lists campaigns that have keys."""
    from .. import bank
    b = bank.load()
    return {"campaigns": b.campaigns()} if campaign is None else {"campaign": campaign, "keys": b.keys(campaign)}


@tool
def bank_set(campaign: str, values: dict[str, int], delete: list[str] | None = None) -> dict:
    """Set (or delete) campaign bank keys in the live profile, e.g. to start a playtest with 500
    currency. Backs up Player.nfp first and refuses while the game is running."""
    from .. import bank
    b = bank.load()
    for k, v in values.items():
        b.set(campaign, k, int(v))
    for k in delete or []:
        b.delete(campaign, k)
    backup = bank.save(b)
    return {"saved": str(b.path), "backup": str(backup) if backup else None, "keys": b.keys(campaign)}
