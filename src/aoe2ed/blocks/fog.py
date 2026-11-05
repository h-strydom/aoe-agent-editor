"""Fog of war: start a player with part of the map explored."""
from __future__ import annotations

import math

from ..datasets import object_id
from .base import Ctx, spread

# Map revealers by line of sight in tiles (Return of Rome's data, 2026-11-05; AoE2 has the same ids): 837 sees 4,
# MAP_REVEALER_MEDIUM 10, MAP_REVEALER_GIANT 20.
REVEALERS = (("MAP_REVEALER_GIANT", 20), ("MAP_REVEALER_MEDIUM", 10), ("MAP_REVEALER", 4))


def reveal(ctx: Ctx, *, area, player: int = 1, keep: bool = False, name: str | None = None) -> dict:
    """Start `player` with `area` explored: map revealers cover it, then disappear after a second, leaving it
    explored under fog (keep=True leaves them, so the area stays in sight all game).

    Triggers created: "<name>" (default "Reveal P<player> <x1>,<y1>"), unless keep."""
    x1, y1, x2, y2 = ctx.area(area)
    w, h = x2 - x1 + 1, y2 - y1 + 1
    unit, sight = next(((u, s) for u, s in REVEALERS if min(w, h) >= s), REVEALERS[-1])
    step = sight * 1.4                                     # overlapping circles leave no gaps
    n = math.ceil(w / step) * math.ceil(h / step)
    um = ctx.scenario.unit_manager
    oid = object_id(unit)
    placed = [um.add_unit(player=player, unit_const=oid, x=x + 0.5, y=y + 0.5).reference_id
              for x, y in spread((x1, y1, x2, y2), n)]
    out = {"unit": unit, "revealers": len(placed), "triggers": []}
    if not keep:
        name = name or f"Reveal P{player} {x1},{y1}"
        ctx.trigger(name, [{"type": "timer", "timer": 1}],
                    [{"type": "remove_object", "source_player": player, "selected_object_ids": placed}])
        out["triggers"] = [name]
    return out
