"""Player-level setup blocks."""
from __future__ import annotations

from ..datasets import object_id
from .base import Ctx


def anchor(ctx: Ctx, *, player: int, at=(1, 1), unit: str | int = "BARRACKS", name: str | None = None) -> dict:
    """Keep `player` alive while it has no army (e.g. an enemy that only spawns waves).

    Verified in game: a player whose only objects are Houses is defeated at once, which hands
    the other side an instant victory even with the victory condition set to Custom. This
    places a building that counts for survival, then makes it unattackable, untargetable and
    unselectable at game start. Put it in a corner nobody visits."""
    x, y = ctx.point(at)
    um = ctx.scenario.unit_manager
    for other in um.get_units_in_area(x1=x - 2, y1=y - 2, x2=x + 3, y2=y + 3):  # trees, resources
        um.remove_unit(unit=other)
    u = ctx.scenario.unit_manager.add_unit(player=player, unit_const=object_id(unit), x=x + 0.5, y=y + 0.5)
    sel = {"selected_object_ids": [u.reference_id], "source_player": player}
    name = name or f"Anchor P{player}"
    ctx.trigger(name, [], [{"type": "disable_unit_attackable", **sel},
                           {"type": "disable_unit_targeting", **sel},
                           {"type": "disable_object_selection", **sel}])
    return {"triggers": [name], "unit_ref": u.reference_id}
