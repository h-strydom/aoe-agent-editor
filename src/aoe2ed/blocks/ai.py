"""Blocks that steer computer players from the scenario: start them on an event, hand over a base when found.

AI specs with `start: {trigger: N}` do nothing until the scenario's AI Script Goal effect sends N; the script
sees it as (event-detected trigger N). The effect reaches every computer player, so give AIs that start at
different moments different numbers.
"""
from __future__ import annotations

from .base import Ctx

OWNED_TYPES = ("BUILDING", "CIVILIAN", "MILITARY")       # not OTHER: trees, mines, flags stay Gaia's


def ai_signal(signal: int) -> dict:
    """The effect that starts AIs waiting for `signal` (AI spec `start: {trigger: signal}`)."""
    if not 0 <= int(signal) <= 255:
        raise ValueError(f"AI signals are 0-255, got {signal}")
    return {"type": "ai_script_goal", "ai_script_goal": int(signal)}


def start_ai(ctx: Ctx, *, signal: int = 1, conditions: list[dict] | None = None, effects: list[dict] | None = None,
             name: str | None = None) -> dict:
    """Start the AIs waiting for `signal` once `conditions` hold (none: at once). Extra `effects` run with it,
    such as a message to the player.

    Triggers created: "<name>" (default "Start AI <signal>")."""
    name = name or f"Start AI {signal}"
    ctx.trigger(name, conditions or [], [*(effects or []), ai_signal(signal)])
    return {"triggers": [name], "signal": int(signal)}


def claim_base(ctx: Ctx, *, area, player: int = 1, from_player: int = 0, signal: int | None = None,
               effects: list[dict] | None = None, name: str | None = None) -> dict:
    """When one of `player`'s units enters `area`, the buildings, villagers and soldiers `from_player` (Gaia by
    default) owns there become the player's: "find your base" missions. With `signal`, the AIs waiting for it start
    at the same moment.

    The check waits 2 seconds, so map revealers from the reveal block (gone after 1 second) don't count as finding it.

    Triggers created: "<name>" (default "Claim base P<player>")."""
    area = list(ctx.area(area))
    name = name or f"Claim base P{player}"
    take = [{"type": "change_ownership", "source_player": from_player, "target_player": player, "area": area,
             "object_type": t} for t in OWNED_TYPES]
    ctx.trigger(name, [{"type": "timer", "timer": 2},
                       {"type": "objects_in_area", "source_player": player, "area": area, "quantity": 1}],
                [*take, *(effects or []), *([ai_signal(signal)] if signal is not None else [])])
    return {"triggers": [name], "area": area}
