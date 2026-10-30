"""Objectives: survive a duration, generic objectives, on-screen timers."""
from __future__ import annotations

from .base import Ctx


def survive(ctx: Ctx, minutes: float, *, player: int = 1, text: str | None = None,
            timer_slot: int = 0, timer_message: str = "Survive: %d", on_complete: list[dict] | None = None,
            name: str = "Survive") -> dict:
    """Survive `minutes`. Shows a countdown and an objective line; when time is up runs
    `on_complete` effects (default: declare victory for `player`).
    Triggers created: "<name> Timer", "<name> Objective", "<name> Complete" (disabled until the
    timer finishes; hook other blocks onto it)."""
    secs = ctx.secs(minutes * 60)
    text = text or f"Survive for {minutes:g} minutes."
    complete = f"{name} Complete"
    ctx.triggers(
        {"name": f"{name} Timer", "effects": [
            {"type": "display_timer", "timer": timer_slot, "display_time": secs, "time_unit": "SECONDS",
             "message": timer_message}]},
        {"name": f"{name} Objective", "display_as_objective": True, "display_on_screen": True,
         "description": text, "short_description": text,
         "conditions": [{"type": "timer", "timer": secs}],
         "effects": [{"type": "activate_trigger", "trigger_id": complete}]},
        {"name": complete, "enabled": False,
         "effects": on_complete if on_complete is not None else
         [{"type": "declare_victory", "source_player": player, "enabled": True}]},
    )
    return {"triggers": [f"{name} Timer", f"{name} Objective", complete], "complete_trigger": complete,
            "seconds": secs}


def objective(ctx: Ctx, name: str, text: str, conditions: list[dict], effects: list[dict] | None = None,
              *, order: int = 0, enabled: bool = True) -> dict:
    """An objective line that ticks off when `conditions` are met, then runs `effects`.

    Triggers created: "<name>"."""
    ctx.trigger(name, conditions, effects or [], display_as_objective=True, display_on_screen=True,
                description=text, short_description=text, description_order=order, enabled=enabled)
    return {"triggers": [name]}


def lose_if_destroyed(ctx: Ctx, *, player: int, unit_type: str | int, effects: list[dict],
                      name: str = "Core Lost") -> dict:
    """Run `effects` when `player` has no `unit_type` left (e.g. their Town Center or Wonder).

    Triggers created: "<name>" (default "Core Lost")."""
    ctx.trigger(name, [{"type": "own_fewer_objects", "source_player": player, "object_list": unit_type,
                        "quantity": 0}], effects)
    return {"triggers": [name]}
