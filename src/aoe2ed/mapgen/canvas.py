"""In-memory map the generator steps draw on, before it is written into a scenario."""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field

# Tile flags
WATER = 1          # not walkable
BLOCKED = 2        # occupied by a unit / object footprint
NOTREE = 4         # forests stay out
CLEAR = 8          # forests and resources stay out
FLAT = 16          # hills stay out
FOREST = 32        # forest tile (has a tree)
ROAD = 64
WALL = 128         # choke walls: forest step fills these

Tile = tuple[int, int]


@dataclass
class PlacedUnit:
    player: int
    unit_const: int
    x: float
    y: float
    rotation: float = 0.0


@dataclass
class Canvas:
    size: int
    terrain: list[int] = field(default_factory=list)
    elevation: list[int] = field(default_factory=list)
    flags: bytearray = field(default_factory=bytearray)
    units: list[PlacedUnit] = field(default_factory=list)

    def __post_init__(self):
        n = self.size * self.size
        self.terrain = self.terrain or [0] * n
        self.elevation = self.elevation or [0] * n
        self.flags = self.flags or bytearray(n)

    # -------------------------------------------------- tiles
    def i(self, x: int, y: int) -> int:
        return x + y * self.size

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def has(self, x: int, y: int, flag: int) -> bool:
        return bool(self.flags[x + y * self.size] & flag)

    def mark(self, tiles: Iterable[Tile], flag: int) -> None:
        for x, y in tiles:
            self.flags[x + y * self.size] |= flag

    def unmark(self, tiles: Iterable[Tile], flag: int) -> None:
        for x, y in tiles:
            self.flags[x + y * self.size] &= ~flag & 0xFF

    def paint(self, tiles: Iterable[Tile], terrain: int) -> None:
        for x, y in tiles:
            self.terrain[x + y * self.size] = terrain

    def free(self, x: int, y: int, avoid: int = WATER | BLOCKED) -> bool:
        return self.inside(x, y) and not self.flags[x + y * self.size] & avoid

    # -------------------------------------------------- shapes (all clipped to the map)
    def rect(self, x1: int, y1: int, x2: int, y2: int) -> list[Tile]:
        x1, y1, x2, y2 = self.clip_rect((x1, y1, x2, y2))
        return [(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1)]

    def disc(self, cx: float, cy: float, r: float) -> list[Tile]:
        out = []
        for y in range(max(0, math.floor(cy - r)), min(self.size, math.ceil(cy + r) + 1)):
            for x in range(max(0, math.floor(cx - r)), min(self.size, math.ceil(cx + r) + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    out.append((x, y))
        return out

    def line(self, a: tuple[float, float], b: tuple[float, float], width: float = 1) -> list[Tile]:
        """Tiles within width/2 of the segment a-b."""
        (ax, ay), (bx, by) = a, b
        r = max(0.5, width / 2)
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy or 1e-9
        out = []
        for y in range(max(0, math.floor(min(ay, by) - r)), min(self.size, math.ceil(max(ay, by) + r) + 1)):
            for x in range(max(0, math.floor(min(ax, bx) - r)), min(self.size, math.ceil(max(ax, bx) + r) + 1)):
                t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / ll))
                px, py = ax + t * dx - x, ay + t * dy - y
                if px * px + py * py <= r * r:
                    out.append((x, y))
        return out

    def clip_rect(self, r) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = (int(round(v)) for v in r)
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        hi = self.size - 1
        return max(0, x1), max(0, y1), min(hi, x2), min(hi, y2)

    def neighbors(self, x: int, y: int, diagonal: bool = False) -> Iterator[Tile]:
        steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
        if diagonal:
            steps += ((1, 1), (1, -1), (-1, 1), (-1, -1))
        for dx, dy in steps:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                yield nx, ny

    def grow(self, start: Tile, n: int, rng: random.Random, ok: Callable[[int, int], bool],
             weight: Callable[[int, int], float] | None = None) -> list[Tile]:
        """Grow an organic blob of up to n tiles from start through tiles where ok(x, y)."""
        if not ok(*start):
            return []
        got, seen, frontier = [start], {start}, []

        def push(t):
            for nb in self.neighbors(*t):
                if nb not in seen:
                    seen.add(nb)
                    if ok(*nb):
                        frontier.append(nb)

        push(start)
        while frontier and len(got) < n:
            if weight:  # best of a few random frontier tiles: compact blobs with noisy edges
                picks = [rng.randrange(len(frontier)) for _ in range(min(len(frontier), 4))]
                k = max(picks, key=lambda j: weight(*frontier[j]) + rng.random() * 0.25)
                frontier[k], frontier[-1] = frontier[-1], frontier[k]
                t = frontier.pop()
            else:
                t = frontier.pop(rng.randrange(len(frontier)))
            got.append(t)
            push(t)
        return got

    # -------------------------------------------------- units
    def footprint(self, x: float, y: float, size: int) -> list[Tile]:
        """Tiles covered by a square object of `size` centered at (x, y)."""
        h = size / 2
        x1, y1 = math.floor(x - h + 1e-6), math.floor(y - h + 1e-6)
        return [(tx, ty) for ty in range(y1, y1 + size) for tx in range(x1, x1 + size)]

    def can_place(self, x: float, y: float, size: int = 1, avoid: int = WATER | BLOCKED) -> bool:
        return all(self.free(tx, ty, avoid) for tx, ty in self.footprint(x, y, size))

    def place(self, unit_const: int, player: int, x: float, y: float, size: int = 1,
              rotation: float = 0.0, block: bool = True) -> PlacedUnit:
        u = PlacedUnit(player, int(unit_const), float(x), float(y), rotation)
        self.units.append(u)
        if block:
            self.mark([t for t in self.footprint(x, y, size) if self.inside(*t)], BLOCKED)
        return u

    def remove_units_in(self, tiles: Iterable[Tile]) -> None:
        ts = set(tiles)
        self.units = [u for u in self.units if (int(u.x), int(u.y)) not in ts]
        self.unmark(ts, BLOCKED | FOREST)
