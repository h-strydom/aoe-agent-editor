"""Regenerate the trigger reference shipped with the aoe2-triggers skill.

    uv run python scripts/gen_trigger_reference.py

Writes skills/aoe2-triggers/reference/{effects,conditions,enums}.md from the parser's
schemas for the latest scenario version, so the reference never drifts from what the tools accept.
"""
from __future__ import annotations

from pathlib import Path

from aoe2ed import triggers as T
from aoe2ed.datasets import ENUM_DATASETS
from aoe2ed.session import SESSIONS

OUT = Path(__file__).resolve().parents[1] / "skills" / "aoe2-triggers" / "reference"

# Short purpose lines for the effects/conditions agents reach for most; everything else is listed
# with its parameters only.
NOTES = {
    "activate_trigger": "Enable another trigger (by name in aoe2ed).",
    "attack_move": "Order units (filter by player/area/type) to attack-move to a location.",
    "change_variable": "Set/Add/Subtract/Multiply/Divide a trigger variable.",
    "count_units_into_variable": "Count matching units into variable2.",
    "create_decision": "Two-option popup; pair with the decision_triggered condition.",
    "create_object": "Spawn one unit/building at location.",
    "declare_victory": "End the scenario with victory (enabled=true) for source_player.",
    "display_instructions": "Show a message in the instructions panel for display_time seconds.",
    "display_timer": "Countdown on screen; message may contain %d. Pair with display_timer_triggered.",
    "load_key_value": "Campaign bank: load key `message` into variable; quantity is the default.",
    "store_key_value": "Campaign bank: store variable under key `message` (campaign-scoped, persists).",
    "delete_key": "Campaign bank: delete key `message`.",
    "modify_attribute": "Change a unit type's stat. Integer stats take whole numbers only.",
    "modify_attribute_for_class": "Change a stat for a whole class (object_group2) / type (object_type2).",
    "modify_resource": "Set/Add/Subtract a player's resource (tribute_list = Attribute).",
    "modify_resource_by_variable": "Resource <- variable.",
    "modify_variable_by_resource": "Variable <- resource.",
    "modify_variable_by_variable": "variable (op)= variable2.",
    "script_call": "Runs the XS function defined in `message`, e.g. 'void f() { ... }'.",
    "send_chat": "Chat message to source_player.",
    "task_object": "Order units with any action_type (move, patrol, garrison, ...).",
    "teleport_object": "Move matching units instantly to location.",
}
CONDITION_NOTES = {
    "accumulate_attribute": "True when player's resource/attribute >= quantity (inverted: <).",
    "objects_in_area": "True when >= quantity matching objects of source_player are in area.",
    "own_objects": "True when player owns >= quantity matching objects.",
    "own_fewer_objects": "True when player owns <= quantity matching objects (0 = none left).",
    "timer": "True `timer` seconds after this trigger became active.",
    "variable_value": "Compare a variable to quantity.",
    "chance": "True with quantity % probability each check.",
    "decision_triggered": "The player chose option 1/2 of decision_id.",
    "research_technology": "Player researched technology.",
    "script_call": "True when the XS function in xs_function returns true.",
    "difficulty_level": "Compare the game difficulty.",
}


def _table(kind: str, types: list[dict], schema_fn, notes: dict) -> str:
    lines = [f"# {kind.title()} ({len(types)})", "",
             "Generated from AoE2ScenarioParser schemas. Use `effect_schema`/`condition_schema` for defaults.",
             "Values in `[Dataset]` accept names (see enums.md, or `lookup`/`enum_values`).", ""]
    for t in types:
        sch = schema_fn(t["type"])
        params = ", ".join(f"`{p['name']}`" + (f" [{p['dataset']}]" if p.get("dataset") and p["dataset"] not in ("str", "bool") else "")
                           for p in sch["params"] if p["name"] != "quantity_float")
        note = notes.get(t["type"], "")
        lines.append(f"- **{t['type']}** ({t['id']}){': ' + note if note else ''}  \n  {params or '(no params)'}")
    return "\n".join(lines) + "\n"


def main() -> None:
    SESSIONS.new()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "effects.md").write_text(_table("effects", T.effect_types(), T.effect_schema, NOTES), encoding="utf-8")
    (OUT / "conditions.md").write_text(_table("conditions", T.condition_types(), T.condition_schema, CONDITION_NOTES), encoding="utf-8")
    skip = {"TerrainId"}  # big; use lookup(kinds=['terrain'])
    lines = ["# Trigger enums", "", "Names accepted for enum-typed parameters (case-insensitive).", ""]
    for name, ds in sorted(ENUM_DATASETS.items()):
        if name in skip:
            continue
        members = [m.name for m in ds]
        if len(members) > 80:
            lines.append(f"- **{name}** ({len(members)} values): use `enum_values('{name}')`")
        else:
            lines.append(f"- **{name}**: " + ", ".join(members))
    (OUT / "enums.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
