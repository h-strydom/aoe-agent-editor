"""Story mechanics: escorts and player choices."""
from __future__ import annotations

from ..datasets import object_id
from .base import Ctx


def escort(ctx: Ctx, *, unit: str | int, count: int, start, destination, waypoints: list | None = None,
           player: int = 1, speed: float | None = None, count_var: str = "arrived",
           store_key: str | None = None, min_arrived: int = 1, done_effects: list[dict] | None = None,
           lost_effects: list[dict] | None = None, controllable: bool = False, name: str = "Escort") -> dict:
    """A convoy of `count` `unit`s placed at `start` that moves on its own through `waypoints` to
    `destination` (area). Each unit that reaches the destination is removed and counted in
    `count_var`. When none are left on the map: if count_var >= min_arrived, "<name> Done" runs
    `done_effects` (and stores count_var under `store_key`), otherwise "<name> Lost" runs
    `lost_effects` (e.g. declare defeat). `speed` sets the unit type's movement speed.
    controllable=False (default) makes the convoy unselectable so the player can't stop or
    redirect it (verified in game: owned carts otherwise take orders).

    Triggers created: "<name> Start", "<name> Arrive" (looping), "<name> Done", "<name> Lost".
    Unverified in game: queued task_object moves and remove_object with max_units_affected: 1."""
    from .waves import near_tiles
    uid = object_id(unit)
    var = ctx.var(count_var)
    dest = list(ctx.area(destination))
    refs = []
    for x, y in near_tiles(ctx, start, count):
        u = ctx.scenario.unit_manager.add_unit(player=player, unit_const=uid, x=x + 0.5, y=y + 0.5)
        refs.append(u.reference_id)
    route = [ctx.point(w) for w in (waypoints or [])] + [ctx.point(destination)]
    start_effects = [] if controllable else [
        {"type": "disable_object_selection", "source_player": player, "selected_object_ids": refs}]
    if speed is not None:
        start_effects.append({"type": "modify_attribute", "object_list_unit_id": uid, "source_player": player,
                              "object_attributes": "MOVEMENT_SPEED", "operation": "SET", "quantity": float(speed)})
    for i, (x, y) in enumerate(route):
        start_effects.append({"type": "task_object", "source_player": player, "selected_object_ids": refs,
                              "location": [x, y], "action_type": "MOVE", **({"queue_action": 1} if i else {})})
    ctx.triggers(
        {"name": f"{name} Start", "effects": start_effects},
        {"name": f"{name} Arrive", "looping": True,
         "conditions": [{"type": "objects_in_area", "source_player": player, "object_list": uid, "area": dest,
                         "quantity": 1}],
         "effects": [{"type": "remove_object", "source_player": player, "object_list_unit_id": uid, "area": dest,
                      "max_units_affected": 1},
                     {"type": "change_variable", "variable": var, "operation": "ADD", "quantity": 1}]},
        {"name": f"{name} Done",
         "conditions": [{"type": "own_fewer_objects", "source_player": player, "object_list": uid, "quantity": 0},
                        {"type": "variable_value", "variable": var, "comparison": "LARGER_OR_EQUAL",
                         "quantity": min_arrived}],
         "effects": [{"type": "deactivate_trigger", "trigger_id": f"{name} Lost"},
                     *([{"type": "store_key_value", "variable": var, "message": store_key}] if store_key else []),
                     *(done_effects or [])]},
        {"name": f"{name} Lost",
         "conditions": [{"type": "own_fewer_objects", "source_player": player, "object_list": uid, "quantity": 0},
                        {"type": "variable_value", "variable": var, "comparison": "LESS", "quantity": min_arrived}],
         "effects": [{"type": "deactivate_trigger", "trigger_id": f"{name} Done"}, *(lost_effects or [])]},
    )
    return {"triggers": [f"{name} {t}" for t in ("Start", "Arrive", "Done", "Lost")], "unit_refs": refs,
            "count_var": var}


def choice(ctx: Ctx, *, prompt: str, options: list[dict], var: str, at: int | None = None,
           conditions: list[dict] | None = None, store_key: str | None = None, default_option: int | None = None,
           timeout_sec: int | None = None, name: str = "Choice") -> dict:
    """A two-option decision popup. options: [{"label": "Rebuild the bridge", "value": 1,
    "effects": [...]}, {...}] (exactly 2). The pick sets `var` to the option's value (default 1/2),
    optionally stores it under `store_key`, and runs the option's effects.
    Shown at `at` seconds, or when `conditions` hold. With `timeout_sec` and `default_option`, an
    unanswered popup resolves to that option.

    Triggers created: "<name>", "<name> 1", "<name> 2", "<name> Timeout" (if timeout)."""
    if len(options) != 2:
        raise ValueError("choice needs exactly 2 options (the engine's decision popup has two buttons)")
    var = ctx.var(var)
    did = ctx.next_decision_id()
    conds = list(conditions or [])
    if at is not None:
        conds.append({"type": "timer", "timer": ctx.secs(at)})

    def resolve(i: int) -> list[dict]:
        opt = options[i - 1]
        other = 2 if i == 1 else 1
        return [{"type": "deactivate_trigger", "trigger_id": f"{name} {other}"},
                *([{"type": "deactivate_trigger", "trigger_id": f"{name} Timeout"}] if timeout_sec else []),
                {"type": "change_variable", "variable": var, "operation": "SET", "quantity": opt.get("value", i)},
                *([{"type": "store_key_value", "variable": var, "message": store_key}] if store_key else []),
                *opt.get("effects", [])]

    specs = [
        {"name": name, "conditions": conds, "effects": [
            {"type": "create_decision", "decision_id": did, "message": prompt,
             "message_option1": options[0]["label"], "message_option2": options[1]["label"]},
            *([{"type": "activate_trigger", "trigger_id": f"{name} Timeout"}] if timeout_sec else [])]},
        {"name": f"{name} 1", "conditions": [{"type": "decision_triggered", "decision_id": did, "decision_option": 1}],
         "effects": resolve(1)},
        {"name": f"{name} 2", "conditions": [{"type": "decision_triggered", "decision_id": did, "decision_option": 2}],
         "effects": resolve(2)},
    ]
    if timeout_sec:
        if default_option not in (1, 2):
            raise ValueError("timeout_sec needs default_option 1 or 2")
        specs.append({"name": f"{name} Timeout", "enabled": False,
                      "conditions": [{"type": "timer", "timer": ctx.secs(timeout_sec)}],
                      "effects": [{"type": "deactivate_trigger", "trigger_id": f"{name} 1"},
                                  {"type": "deactivate_trigger", "trigger_id": f"{name} 2"},
                                  *[e for e in resolve(default_option) if e["type"] != "deactivate_trigger"]]})
    ctx.triggers(*specs)
    return {"triggers": [s["name"] for s in specs], "decision_id": did, "var": var}


def say_var(ctx: Ctx, *, text: str, var: str, player: int = 1) -> dict:
    """Effect dict: chat `text` with %d replaced by the variable's current value (via XS), e.g.
    {$helper: say_var, text: "Carts delivered: %d", var: carts_arrived}."""
    name = ctx.var(var)
    vid = next(v.variable_id for v in ctx.scenario.trigger_manager.variables if v.name == name)
    fn = f"aoe2edSay{ctx.next_id()}"
    safe = text.replace("\\", "\\\\").replace('"', '\\"')
    return {"type": "script_call",
            "message": f'void {fn}() {{ xsChatData("{safe}", xsTriggerVariable({vid})); }}'}
