"""Triggers, variables, effect/condition schemas, XS."""
from __future__ import annotations

from pathlib import Path

from .. import triggers as T
from ..session import SESSIONS
from . import tool


@tool
def effect_types(handle: str) -> list[dict]:
    """All effect types available at this scenario's version."""
    SESSIONS.get(handle)
    return T.effect_types()


@tool
def condition_types(handle: str) -> list[dict]:
    """All condition types available at this scenario's version."""
    SESSIONS.get(handle)
    return T.condition_types()


@tool
def effect_schema(handle: str, effect_type: str) -> dict:
    """Parameters of one effect type (name, dataset for value names, default)."""
    SESSIONS.get(handle)
    return T.effect_schema(effect_type)


@tool
def condition_schema(handle: str, condition_type: str) -> dict:
    """Parameters of one condition type."""
    SESSIONS.get(handle)
    return T.condition_schema(condition_type)


@tool
def triggers_list(handle: str) -> list[dict]:
    """Every trigger with its condition and effect type names, in index order."""
    return [T.trigger_summary(t) for t in SESSIONS.get(handle).scenario.trigger_manager.triggers]


@tool
def trigger_get(handle: str, trigger: int | str, verbose: bool = True) -> dict:
    """Full trigger as JSON (by index or name). verbose adds `_names` for enum/unit values."""
    return T.trigger_to_dict(T.find_trigger(SESSIONS.get(handle).scenario, trigger), verbose)


@tool
def triggers_add(handle: str, triggers: list[dict], create_variables: bool = True) -> dict:
    """Add triggers from JSON. Format:
    {"name", "enabled"?, "looping"?, "execute_on_load"?, "description"?, "short_description"?,
     "display_as_objective"?, "display_on_screen"?, "description_order"?,
     "conditions": [{"type": "timer", "timer": 60}, ...],
     "effects": [{"type": "send_chat", "source_player": 1, "message": "Hi"}, ...]}
    Values can be names (units 'ARCHER', players 'ONE', operation 'Add'). Shorthands:
    area [x1,y1,x2,y2], location [x,y], variable by name (auto-created), trigger_id by trigger
    name (even one defined later in the same call). Use effect_schema for params."""
    s = SESSIONS.get(handle).scenario
    return {"created": T.add_triggers(s, triggers, create_variables)}


@tool
def trigger_update(handle: str, trigger: int | str, changes: dict) -> dict:
    """Patch a trigger. Given 'conditions' or 'effects' lists replace the old ones entirely."""
    s = SESSIONS.get(handle).scenario
    t = T.find_trigger(s, trigger)
    return T.update_trigger(s, t.trigger_id, changes)


@tool
def triggers_remove(handle: str, triggers: list[int | str]) -> dict:
    """Remove triggers by index or name. Indices of later triggers shift down."""
    s = SESSIONS.get(handle).scenario
    ids = sorted({T.find_trigger(s, t).trigger_id for t in triggers}, reverse=True)
    for i in ids:
        s.trigger_manager.remove_trigger(i)
    return {"removed": ids, "remaining": len(s.trigger_manager.triggers)}


@tool
def triggers_reorder(handle: str, order: list[int]) -> dict:
    """Set the trigger order as a permutation of current indices (affects execution order)."""
    tm = SESSIONS.get(handle).scenario.trigger_manager
    tm.reorder_triggers(order)
    return {"order": [t.name for t in tm.triggers]}


@tool
def triggers_copy(src_handle: str, dst_handle: str, triggers: list[int | str] | None = None) -> dict:
    """Copy triggers (all if omitted) from one open scenario to another via JSON, re-resolving
    variables by name in the destination."""
    src = SESSIONS.get(src_handle).scenario
    dst = SESSIONS.get(dst_handle).scenario
    chosen = [T.find_trigger(src, t) for t in triggers] if triggers else list(src.trigger_manager.triggers)
    var_names = {v.variable_id: v.name for v in src.trigger_manager.variables}
    name_by_index = {t.trigger_id: t.name for t in src.trigger_manager.triggers}
    specs = []
    for t in chosen:
        d = T.trigger_to_dict(t)
        d.pop("index")
        for ce in d["conditions"] + d["effects"]:
            for k in ("variable", "variable2"):
                if k in ce and ce[k] in var_names:
                    ce[k] = var_names[ce[k]]
            if "trigger_id" in ce and ce["trigger_id"] in name_by_index:
                ce["trigger_id"] = name_by_index[ce["trigger_id"]]
        specs.append(d)
    return {"created": T.add_triggers(dst, specs)}


@tool
def variables_list(handle: str) -> list[dict]:
    """Trigger variables (id, name)."""
    return [{"id": v.variable_id, "name": v.name}
            for v in SESSIONS.get(handle).scenario.trigger_manager.variables]


@tool
def variable_add(handle: str, name: str, variable_id: int | None = None) -> dict:
    """Create a named trigger variable (ids 0-255)."""
    tm = SESSIONS.get(handle).scenario.trigger_manager
    v = tm.add_variable(name, variable_id) if variable_id is not None else tm.add_variable(name)
    return {"id": v.variable_id, "name": v.name}


@tool
def variable_rename(handle: str, variable: int | str, name: str) -> dict:
    tm = SESSIONS.get(handle).scenario.trigger_manager
    for v in tm.variables:
        if v.variable_id == variable or v.name == variable:
            v.name = name
            return {"id": v.variable_id, "name": v.name}
    raise KeyError(f"No variable '{variable}'")


# ---------------------------------------------------------------- XS

@tool
def xs_embed(handle: str, code: str | None = None, path: str | None = None) -> dict:
    """Embed XS into the scenario (inside a Script Call effect, so no external file is needed).
    Repeated calls append. Run xs_check first."""
    xm = SESSIONS.get(handle).scenario.xs_manager
    xm.add_script(xs_file_path=path or "", xs_string=code or "")
    return {"embedded_chars": len(xm.xs_trigger.effects[0].message)}


@tool
def xs_get(handle: str) -> dict:
    """Embedded XS (if any) plus the external script name the scenario references."""
    s = SESSIONS.get(handle).scenario
    xm = s.xs_manager
    embedded = []
    for t in s.trigger_manager.triggers:
        for e in t.effects:
            if e.effect_type == 55 and e.message:  # SCRIPT_CALL
                embedded.append({"trigger": t.name, "code": e.message})
    return {"script_name": xm.script_name, "script_calls": embedded}


@tool
def xs_set_script_name(handle: str, script_name: str) -> dict:
    """Reference an external XS file (in the profile's xs folder) as the scenario's script."""
    xm = SESSIONS.get(handle).scenario.xs_manager
    xm.script_name = script_name
    return {"script_name": xm.script_name}


@tool
def xs_check(code: str | None = None, path: str | None = None, context: str = "scenario") -> dict:
    """Lint XS with xs-check (static analysis: syntax, types, unknown functions).
    Pass code or a file path. context: "scenario" (default; calls that only exist in an AI script's XS, such
    as xsGetGoal, are errors) or "ai". Returns ok + diagnostics."""
    from ..xs import check
    if code is None and path is None:
        raise ValueError("Pass code or path")
    return check(code=code, path=Path(path) if path else None, context=context)


@tool
def xs_api(query: str, limit: int = 15, with_docs: bool = True) -> list[dict]:
    """Search the documented XS API (functions + constants) by name or doc text, e.g.
    'xsCreateFile', 'random', 'cAttributeGold', 'Trigger'. Returns signature + doc."""
    from ..xs import api_search
    return api_search(query, limit, with_docs)
