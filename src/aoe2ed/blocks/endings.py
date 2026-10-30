"""Run endings for roguelite missions: the mission always ends in a victory so earnings persist.

Whether the campaign keeps stores made in a mission that ends in defeat is unverified, so a
"failed" run shows a results message and then declares victory anyway.
"""
from __future__ import annotations

from .base import Ctx


def run_end(ctx: Ctx, *, player: int = 1, earned_var: str = "earned", meta_var: str = "meta_points",
            meta_key: str = "meta_points", success_trigger: str | None = None, success_bonus: int = 0,
            fail_conditions: list[dict] | None = None, extra_store: dict[str, str] | None = None,
            delay_sec: int = 8, name: str = "Run") -> dict:
    """success_trigger: an existing (disabled) trigger to hook, e.g. survive()'s '<x> Complete'; this
    block appends 'activate Run Success' to it. fail_conditions: when met the run ends early.
    On end: meta += earned (+ bonus on success), store meta (and extra_store {key: var}), show the
    result, then victory after delay_sec.

    Triggers created: "<name> Success", "<name> Failed", "<name> End", "<name> Victory"."""
    earned, meta = ctx.var(earned_var), ctx.var(meta_var)
    end, win = f"{name} End", f"{name} Victory"
    specs = [
        {"name": f"{name} Success", "enabled": False, "effects": [
            {"type": "change_variable", "variable": earned, "operation": "ADD", "quantity": success_bonus},
            {"type": "deactivate_trigger", "trigger_id": f"{name} Failed"},
            {"type": "display_instructions", "source_player": player, "display_time": 10,
             "message": "You survived!", "instruction_panel_position": 0},
            {"type": "activate_trigger", "trigger_id": end}]},
        {"name": f"{name} Failed", "enabled": bool(fail_conditions), "conditions": fail_conditions or [],
         "effects": [
             {"type": "deactivate_trigger", "trigger_id": f"{name} Success"},
             {"type": "display_instructions", "source_player": player, "display_time": 10,
              "message": "Your defences have fallen. The run is over.", "instruction_panel_position": 0},
             {"type": "activate_trigger", "trigger_id": end}]},
        {"name": end, "enabled": False, "effects": [
            {"type": "modify_variable_by_variable", "variable": meta, "operation": "ADD", "variable2": earned},
            {"type": "store_key_value", "variable": meta, "message": meta_key},
            *[{"type": "store_key_value", "variable": ctx.var(v), "message": k} for k, v in (extra_store or {}).items()],
            {"type": "script_call", "message":
                f"void aoe2edRunEnd{name}() {{ xsChatData(\"Run over. Earned: %d\", "
                f"xsTriggerVariable({_vid(ctx, earned)})); xsChatData(\"Total currency: %d\", "
                f"xsTriggerVariable({_vid(ctx, meta)})); }}"},
            {"type": "activate_trigger", "trigger_id": win}]},
        {"name": win, "enabled": False, "conditions": [{"type": "timer", "timer": delay_sec}],
         "effects": [{"type": "declare_victory", "source_player": player, "enabled": True}]},
    ]
    ctx.triggers(*specs)
    if success_trigger:
        from .. import triggers as T
        t = T.find_trigger(ctx.scenario, success_trigger)
        T.add_effect(t, {"type": "activate_trigger", "trigger_id": f"{name} Success"}, T.Resolver(ctx.scenario))
    return {"triggers": [s["name"] for s in specs]}


def earn(var: str = "earned", amount: int = 1) -> dict:
    """Effect dict: add to the run's earnings (use in waves(on_wave=...), objectives, kills...)."""
    return {"type": "change_variable", "variable": var, "operation": "ADD", "quantity": amount}


def _vid(ctx: Ctx, name: str) -> int:
    for v in ctx.scenario.trigger_manager.variables:
        if v.name == name:
            return v.variable_id
    raise KeyError(name)
