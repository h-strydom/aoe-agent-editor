"""Factions built from triggers, since the civilization itself can't be randomized in a campaign.

Verified in game: inside a campaign RANDOM civilizations always resolve to Britons, so a "random civ"
has to be emulated. A faction is a set of trigger effects on top of the scenario's civ: tech-tree
changes, unique units added to buildings, bonuses, free techs and a new civ name. Architecture and
unit voices stay those of the scenario's civ.
"""
from __future__ import annotations

from .base import Ctx


def faction_effects(f: dict, player: int) -> list[dict]:
    """Effect dicts that turn `player` into faction `f` (see random_faction for the keys)."""
    eff: list[dict] = []
    if f.get("civ_name"):
        eff.append({"type": "change_civilization_name", "source_player": player, "message": f["civ_name"]})
    for u in f.get("disable_units", []) + f.get("disable_buildings", []):
        eff.append({"type": "enable_disable_object", "source_player": player, "object_list_unit_id": u, "enabled": 0})
    for u in f.get("enable_units", []):
        eff.append({"type": "enable_disable_object", "source_player": player, "object_list_unit_id": u, "enabled": 1})
    for t in f.get("disable_techs", []):
        eff.append({"type": "enable_disable_technology", "source_player": player, "technology": t, "enabled": 0})
    for t in f.get("enable_techs", []):
        eff.append({"type": "enable_disable_technology", "source_player": player, "technology": t, "enabled": 1})
    for tr in f.get("train", []):
        eff.append({"type": "add_train_location", "source_player": player, "object_list_unit_id": tr["unit"],
                    "object_list_unit_id_2": tr["at"], "button_location": tr.get("button", "r1c4"),
                    **({"train_time": tr["train_time"]} if "train_time" in tr else {})})
    for t in f.get("free_techs", []):
        eff.append({"type": "research_technology", "source_player": player, "technology": t,
                    "force_research_technology": 1})
    eff += f.get("effects", [])
    return eff


def random_faction(ctx: Ctx, *, factions: list[dict], player: int = 1, var: str = "faction",
                   store_key: str | None = None, announce: bool = True, name: str = "Faction") -> dict:
    """Give `player` one of `factions` at random when the mission starts.

    factions: [{"name": "Norse Raiders", "civ_name": "Norse", "description": "Infantry +20 HP, Berserks",
                "disable_units": [...], "disable_buildings": [...], "enable_units": [...],
                "disable_techs": [...], "enable_techs": [...],
                "train": [{"unit": "BERSERK", "at": "BARRACKS", "button": "r1c4"}],
                "free_techs": [...], "effects": [<any effect dicts, e.g. stat bonuses>]}, ...]
    The pick (1..N) is kept in `var`. With `store_key`, the pick is loaded from the campaign bank and
    rolled only if it isn't set yet, then stored: the campaign keeps one faction across missions and
    replays (delete the key to re-roll). Use the same factions list and store_key in every mission.
    Without it, every start rolls again (Restart may repeat the roll; unverified).

    Triggers created: "<name> Load" (with store_key), "<name> Roll", "<name> <i>" for each faction."""
    if not 1 <= len(factions) <= 255:
        raise ValueError("random_faction needs 1..255 factions")
    var = ctx.var(var)
    vid = next(v.variable_id for v in ctx.scenario.trigger_manager.variables if v.name == var)
    n = len(factions)
    specs = []
    if store_key:
        specs.append({"name": f"{name} Load", "effects": [
            {"type": "load_key_value", "variable": var, "message": store_key, "quantity": 0}]})
    fn = f"aoe2edRollFaction{ctx.next_id()}"
    specs.append({"name": f"{name} Roll",
                  "conditions": [{"type": "timer", "timer": 1},
                                 {"type": "variable_value", "variable": var, "comparison": "EQUAL", "quantity": 0}],
                  "effects": [{"type": "script_call", "message":
                               f"void {fn}() {{ xsSetTriggerVariable({vid}, xsGetRandomNumberLH(1, {n + 1})); }}"}]})
    for i, f in enumerate(factions, 1):
        eff = faction_effects(f, player)
        if store_key:  # stored once the pick is known (not next to the XS roll, in case it isn't synchronous)
            eff.insert(0, {"type": "store_key_value", "variable": var, "message": store_key})
        if announce:
            text = f"Your people: {f['name']}." + (f" {f['description']}" if f.get("description") else "")
            eff.append({"type": "display_instructions", "source_player": player, "display_time": 15,
                        "instruction_panel_position": 0, "message": text})
        specs.append({"name": f"{name} {i}",
                      "conditions": [{"type": "timer", "timer": 2},
                                     {"type": "variable_value", "variable": var, "comparison": "EQUAL", "quantity": i}],
                      "effects": eff})
    ctx.triggers(*specs)
    return {"triggers": [s["name"] for s in specs], "var": var, "count": n}
