"""Lookups and the run_python escape hatch."""
from __future__ import annotations

import contextlib
import io
import traceback

from .. import datasets
from ..session import SESSIONS
from . import tool


@tool
def lookup(query: str, kinds: list[str] | None = None, limit: int = 25) -> list[dict]:
    """Find ids by name. kinds: unit, building, hero, other (gaia/resources), tech, terrain,
    enum (trigger enums like Operation, ObjectAttribute, DiplomacyState). Substring match."""
    return datasets.search(query, kinds, limit)


@tool
def enum_values(dataset: str | None = None, name: str | None = None) -> list[dict]:
    """All members of a dataset/enum, e.g. 'ObjectAttribute', 'Operation', 'TechInfo', 'TerrainId'.
    (`name` is accepted as an alias of `dataset`.)"""
    ds = dataset or name
    if not ds:
        raise ValueError("Pass dataset, e.g. enum_values('Operation')")
    if ds not in datasets.ENUM_DATASETS and ds not in datasets.INFO_DATASETS:
        raise ValueError(f"Unknown dataset '{ds}'. Datasets: "
                         f"{sorted(set(datasets.ENUM_DATASETS) | set(datasets.INFO_DATASETS))}")
    return datasets.enum_members(ds)


@tool
def run_python(code: str, handle: str | None = None) -> dict:
    """Escape hatch: run Python against the full AoE2ScenarioParser API. In scope:
    `scenario` (if handle given), `sessions`, `datasets`, `aoe2ed`, and the parser's
    managers via scenario.trigger_manager / unit_manager / map_manager / player_manager /
    xs_manager / option_manager / message_manager, plus raw `scenario.sections`.
    Assign to `result` to return a JSON value; print() output is captured."""
    import aoe2ed

    from .._parser import ConditionId, EffectId

    env = {"sessions": SESSIONS, "datasets": datasets, "aoe2ed": aoe2ed,
           "EffectId": EffectId, "ConditionId": ConditionId, "result": None}
    if handle:
        env["scenario"] = SESSIONS.get(handle).scenario
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(code, "<run_python>", "exec"), env)
        error = None
    except Exception:
        error = traceback.format_exc(limit=6)
    res = env.get("result")
    try:
        import json
        json.dumps(res)
    except TypeError:
        res = repr(res)
    return {"result": res, "stdout": buf.getvalue()[-20000:], "error": error}


def _examples_dir():
    from pathlib import Path

    import aoe2ed
    d = Path(aoe2ed.__file__).resolve().parents[2] / "examples"  # plugin / repo checkout layout
    return d if d.is_dir() else None


@tool
def examples() -> list[dict]:
    """Example campaign specs shipped with the toolkit, with absolute paths you can pass to
    compile_campaign or read as a starting point: crucible (roguelite hub + survival runs),
    frontier (story: escort, siege with a choice, counter-attack), factions (random factions)."""
    d = _examples_dir()
    if d is None:
        return []
    out = []
    for spec in sorted(d.glob("*/campaign.yaml")):
        first = spec.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        out.append({"name": spec.parent.name, "path": str(spec), "summary": first})
    return out


@tool
def guide(topic: str = "index") -> str:
    """Reference docs shipped with aoe2ed. Topics: campaign-spec (spec format for
    compile_campaign), engine-facts (game behaviour verified in playtests, read before relying on
    any mechanic), coverage (every editor feature and how an agent does it), index (this list)."""
    from importlib.resources import files
    docs = files("aoe2ed") / "docs"
    names = sorted(p.name[:-3] for p in docs.iterdir() if p.name.endswith(".md"))
    if topic == "index":
        return "Topics: " + ", ".join(names)
    if topic not in names:
        raise ValueError(f"Unknown topic '{topic}'. Topics: {names}")
    return (docs / f"{topic}.md").read_text(encoding="utf-8")
