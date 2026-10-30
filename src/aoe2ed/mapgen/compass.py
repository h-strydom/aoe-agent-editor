"""Map compass: how grid coordinates relate to the in-game diamond view.

AoE2 draws the square tile grid as a diamond. Tile (0, 0) is the west (left) corner. This
module is the single place that fixes which way the axes run, so that names like
`spawn_north` mean the same thing in the generator, the renderer and the game.

Convention: x grows towards the north (top) corner, y grows towards the south (bottom) corner.
So the corners are W=(0,0), N=(max,0), E=(max,max), S=(0,max), and the edges are
NW: y=0, NE: x=max, SE: y=max, SW: x=0.
"""
from __future__ import annotations

DIRECTIONS = ("n", "ne", "e", "se", "s", "sw", "w", "nw")
NAMES = {"n": "north", "ne": "northeast", "e": "east", "se": "southeast",
         "s": "south", "sw": "southwest", "w": "west", "nw": "northwest"}
_ALIASES = {v: k for k, v in NAMES.items()}

# Unit vectors in (x, y) for each direction, relative to the map center.
VECTORS: dict[str, tuple[int, int]] = {
    "n": (1, -1), "ne": (1, 0), "e": (1, 1), "se": (0, 1),
    "s": (-1, 1), "sw": (-1, 0), "w": (-1, -1), "nw": (0, -1),
}


def normalize(direction: str) -> str:
    d = direction.lower().strip()
    d = _ALIASES.get(d, d)
    if d not in VECTORS:
        raise ValueError(f"Unknown direction {direction!r}; use one of {DIRECTIONS}")
    return d


def edge_point(direction: str, size: int, inset: int = 0) -> tuple[int, int]:
    """The tile at the map edge (or corner) in `direction`, moved `inset` tiles inwards."""
    vx, vy = VECTORS[normalize(direction)]
    hi, mid = size - 1, (size - 1) // 2

    def coord(v: int) -> int:
        return mid if v == 0 else (inset if v < 0 else hi - inset)

    return coord(vx), coord(vy)


def corner_names(size: int) -> dict[str, tuple[int, int]]:
    """Grid corners keyed by compass letter (for labelling renders)."""
    return {d: edge_point(d, size) for d in ("n", "e", "s", "w")}
