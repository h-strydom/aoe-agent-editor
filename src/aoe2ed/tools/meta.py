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
def enum_values(dataset: str) -> list[dict]:
    """All members of a dataset/enum, e.g. 'ObjectAttribute', 'Operation', 'TechInfo', 'TerrainId'."""
    return datasets.enum_members(dataset)


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
