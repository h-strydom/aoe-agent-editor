"""Generator steps. Each step is `step(ctx)` and reads its part of the spec from ctx.spec.

Steps are registered in STEPS by name and run in DEFAULT_PIPELINE order. Each step gets its
own RNG seeded from (spec.seed, step name), so adding or removing a step never changes what
the other steps produce. A compiler can drive the generator by choosing a pipeline and
filling in the spec; steps communicate only through the canvas, ctx.areas and ctx.data.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable

from . import compass
from .canvas import BLOCKED, CLEAR, FLAT, FOREST, NOTREE, ROAD, WALL, WATER, Canvas
from .names import cliff_ids, terrain_id, tree_for_forest, unit_id
from .noise import ValueNoise
from .spec import Biome, MapSpec, Point, Rect

TOWN_CENTER, VILLAGER, SCOUT = unit_id("TOWN_CENTER"), unit_id("VILLAGER_MALE"), unit_id("SCOUT_CAVALRY")
GOLD, STONE, BERRIES = unit_id("GOLD_MINE"), unit_id("STONE_MINE"), unit_id("FORAGE_BUSH")
SHEEP, DEER, FISH = unit_id("SHEEP"), unit_id("DEER"), unit_id("FISH_PERCH")
MAX_ELEVATION = 7


@dataclass
class GenContext:
    spec: MapSpec
    canvas: Canvas
    areas: dict[str, Rect] = field(default_factory=dict)
    data: dict = field(default_factory=dict)   # starts, water bodies, ... shared between steps

    @property
    def size(self) -> int:
        return self.canvas.size

    @property
    def biome(self) -> Biome:
        return self.spec.biome_spec

    def rng(self, step: str) -> random.Random:
        return random.Random(f"{self.spec.seed}/{step}")

    def noise(self, step: str, period: float, octaves: int = 3) -> ValueNoise:
        return ValueNoise(self.rng(step + "/noise").getrandbits(64), period, octaves)

    def add_area(self, name: str, rect) -> Rect:
        self.areas[name] = self.canvas.clip_rect(rect)
        return self.areas[name]

    def point(self, ref: Point) -> tuple[int, int]:
        """Resolve a Point reference (see mapgen.spec) to a tile inside the map."""
        hi = self.size - 1
        if isinstance(ref, (list, tuple)):
            x, y = int(round(ref[0])), int(round(ref[1]))
        elif ref == "center":
            x = y = hi // 2
        elif ref.startswith("edge:"):
            parts = ref.split(":")
            x, y = compass.edge_point(parts[1], self.size, int(parts[2]) if len(parts) > 2 else 4)
        elif ref.startswith("player") and ref[6:].isdigit():
            starts = self.data.get("starts", [])
            k = int(ref[6:])
            if not 1 <= k <= len(starts):
                raise ValueError(f"{ref}: no such player start (have {len(starts)})")
            x, y = starts[k - 1]
        elif ref in self.areas:
            x1, y1, x2, y2 = self.areas[ref]
            x, y = (x1 + x2) // 2, (y1 + y2) // 2
        else:
            raise ValueError(f"Unknown point {ref!r}: use [x,y], 'center', 'edge:<dir>[:inset]', "
                             f"'player<N>' or an area name ({sorted(self.areas)})")
        return max(0, min(hi, x)), max(0, min(hi, y))


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _quantile_mask(ctx: GenContext, field_fn: Callable[[int, int], float], coverage: float,
                   eligible: Callable[[int, int], bool]) -> list[tuple[int, int]]:
    tiles = [(x, y) for y in range(ctx.size) for x in range(ctx.size) if eligible(x, y)]
    if not tiles or coverage <= 0:
        return []
    scored = sorted(tiles, key=lambda t: field_fn(*t), reverse=True)
    return scored[:int(len(scored) * min(1.0, coverage))]


# ======================================================================== steps

def base_terrain(ctx: GenContext) -> None:
    """Fill the map with the biome's base terrain plus noisy accent patches."""
    c, b = ctx.canvas, ctx.biome
    base = terrain_id(b.base)
    c.terrain[:] = [base] * (ctx.size * ctx.size)
    c.elevation[:] = [0] * (ctx.size * ctx.size)
    if not b.accents:
        return
    each = b.accent_coverage / len(b.accents)
    taken: set = set()
    for k, accent in enumerate(b.accents):
        nz = ctx.noise(f"accent{k}", period=max(6.0, ctx.size / 10))
        tiles = _quantile_mask(ctx, nz, each, lambda x, y: (x, y) not in taken)
        taken.update(tiles)
        c.paint(tiles, terrain_id(accent))


def players(ctx: GenContext) -> None:
    """Decide start positions and reserve a flat, tree-free base around each one."""
    spec, c, n = ctx.spec, ctx.canvas, ctx.size
    rng = ctx.rng("players")
    count = len(spec.players)
    mid = (n - 1) / 2
    starts = []
    angle0 = rng.random() * 2 * math.pi
    for k, p in enumerate(spec.players):
        if p.position is not None:
            pos = ctx.point(p.position)
        elif count == 1 or spec.player_layout == "center":
            pos = (round(mid), round(mid))
        elif spec.player_layout == "line":
            t = (k + 0.5) / count
            pos = (round(n * 0.15 + t * n * 0.7), round(mid))
        else:  # ring
            a = angle0 + 2 * math.pi * k / count
            r = spec.player_distance * n
            pos = (round(mid + r * math.cos(a)), round(mid + r * math.sin(a)))
        margin = p.base_radius // 2 + 3
        pos = (max(margin, min(n - 1 - margin, pos[0])), max(margin, min(n - 1 - margin, pos[1])))
        starts.append(pos)
        base = c.disc(pos[0], pos[1], p.base_radius)
        c.mark(base, NOTREE | FLAT)
        if ctx.biome.base_floor is not None:
            c.paint(c.disc(pos[0] - 0.5, pos[1] - 0.5, 3.6), terrain_id(ctx.biome.base_floor))
        r = p.base_radius
        ctx.add_area(f"player{k + 1}_base", (pos[0] - r, pos[1] - r, pos[0] + r, pos[1] + r))
    ctx.data["starts"] = starts


def zones(ctx: GenContext) -> None:
    """Named zones: rects, edge spawns, circles (plazas) and choke points."""
    c, n = ctx.canvas, ctx.size
    for z in ctx.spec.zones:
        kind = z.kind
        if kind == "rect":
            if z.rect is None:
                raise ValueError(f"zone {z.name}: rect zones need `rect`")
            rect = ctx.add_area(z.name, z.rect)
            tiles = c.rect(*rect)
        elif kind == "edge":
            d = compass.normalize(z.side or "n")
            vx, vy = compass.VECTORS[d]
            span = []
            for v in (vx, vy):
                if v == 0:
                    lo = (n - z.width) // 2
                    span.append((lo, lo + z.width - 1))
                elif v < 0:
                    span.append((0, z.depth - 1))
                else:
                    span.append((n - z.depth, n - 1))
            rect = ctx.add_area(z.name, (span[0][0], span[1][0], span[0][1], span[1][1]))
            tiles = c.rect(*rect)
        elif kind == "circle":
            cx, cy = ctx.point(z.center or "center")
            tiles = c.disc(cx, cy, z.radius)
            ctx.add_area(z.name, (cx - z.radius, cy - z.radius, cx + z.radius, cy + z.radius))
        elif kind == "choke":
            tiles = _choke(ctx, z)
        else:
            raise ValueError(f"zone {z.name}: unknown kind {kind!r} (rect | edge | circle | choke)")
        flags = (CLEAR | NOTREE if z.clear else 0) | (FLAT if z.flat else 0)
        if flags:
            c.mark(tiles, flags)
        if z.terrain is not None:
            c.paint(tiles, terrain_id(z.terrain))


def _choke(ctx: GenContext, z) -> list[tuple[int, int]]:
    c = ctx.canvas
    if len(z.between) != 2:
        raise ValueError(f"zone {z.name}: choke zones need `between: [A, B]`")
    a, b = ctx.point(z.between[0]), ctx.point(z.between[1])
    length = _dist(a, b) or 1
    dx, dy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    px, py = -dy, dx
    mx, my = a[0] + (b[0] - a[0]) * z.at, a[1] + (b[1] - a[1]) * z.at
    half = z.gap / 2
    gap = c.line((mx - px * half, my - py * half), (mx + px * half, my + py * half), 5)
    walls = []
    for sgn in (-1, 1):
        s0, s1 = half + 0.5, half + z.wall_length
        walls += c.line((mx + sgn * px * s0, my + sgn * py * s0), (mx + sgn * px * s1, my + sgn * py * s1), 3.2)
    gapset = set(gap)
    walls = [t for t in walls if t not in gapset]
    if z.wall == "cliff":
        ctx.data.setdefault("cliff_lines", []).append(
            [(mx + px * (half + 1), my + py * (half + 1)), (mx + px * (half + z.wall_length), my + py * (half + z.wall_length))])
        ctx.data["cliff_lines"].append(
            [(mx - px * (half + 1), my - py * (half + 1)), (mx - px * (half + z.wall_length), my - py * (half + z.wall_length))])
    else:
        c.mark(walls, WALL)
    xs, ys = [t[0] for t in gap], [t[1] for t in gap]
    ctx.add_area(z.name, (min(xs), min(ys), max(xs), max(ys)))
    return gap


def water(ctx: GenContext) -> None:
    """Lakes and rivers, with beaches, shallow fords and fish spots."""
    c, b, n = ctx.canvas, ctx.biome, ctx.size
    rng = ctx.rng("water")
    w_med, w_deep, w_shallow = terrain_id(b.water), terrain_id(b.deep_water), terrain_id(b.shallows)
    bodies = ctx.data.setdefault("water_bodies", [])
    for k, w in enumerate(ctx.spec.water, start=1):
        name = w.name or f"{w.kind}_{k}"
        nz = ctx.noise(f"water{k}", period=max(4.0, w.radius / 1.5), octaves=2)
        if w.kind == "lake":
            center = ctx.point(w.center) if w.center is not None else _free_spot(ctx, rng, w.radius + 3)
            r = w.radius
            tiles = [t for t in c.disc(center[0], center[1], r * 1.3)
                     if _dist(t, center) <= r * (0.75 + 0.5 * nz(*t))]
            tiles = [t for t in tiles if not c.has(*t, CLEAR | FLAT)]
            depth = {t: _dist(t, center) / r for t in tiles}
            for t in tiles:
                c.paint([t], w_deep if depth[t] < 0.45 else w_med)
            c.mark(tiles, WATER | NOTREE)
            shore = _shore(c, tiles)
            c.paint(shore, w_shallow)
            c.unmark(shore, WATER)
            c.mark(shore, NOTREE)
            if b.beach is not None:
                beach = [t for t in _shore(c, tiles + shore) if not c.has(*t, CLEAR)]
                c.paint(beach, terrain_id(b.beach))
                c.mark(beach, NOTREE)
            ctx.add_area(name, _bbox(tiles + shore))
            bodies.append({"name": name, "tiles": tiles, "fish": w.fish})
        elif w.kind == "river":
            pts = [ctx.point(p) for p in w.points] or [
                compass.edge_point(w.start, n, 0), ctx.point("center"), compass.edge_point(w.end, n, 0)]
            path = _wobbly_path(pts, rng, wobble=n / 25)
            tiles: list = []
            seen = set()
            for a, bb in zip(path, path[1:]):
                for t in c.line(a, bb, w.width):
                    if t not in seen:
                        seen.add(t)
                        tiles.append(t)
            c.paint(tiles, w_med)
            c.mark(tiles, WATER | NOTREE)
            banks = _shore(c, tiles)
            c.paint(banks, w_shallow if b.beach is None else terrain_id(b.beach))
            c.mark(banks, NOTREE)
            for f in range(w.fords):
                t = (f + 1) / (w.fords + 1)
                ia = min(len(path) - 2, int(t * (len(path) - 1)))
                (ax, ay), (bx, by) = path[ia], path[ia + 1]
                fx, fy = (ax + bx) / 2, (ay + by) / 2
                ford = [p for p in c.disc(fx, fy, w.width / 2 + 2.5) if c.has(*p, WATER)]
                c.paint(ford, w_shallow)
                c.unmark(ford, WATER)
                if ford:
                    ctx.add_area(f"{name}_ford_{f + 1}", _bbox(ford))
            ctx.add_area(name, _bbox(tiles))
            bodies.append({"name": name, "tiles": [t for t in tiles if c.has(*t, WATER)], "fish": w.fish})
        else:
            raise ValueError(f"water {name}: unknown kind {w.kind!r} (lake | river)")


def _bbox(tiles) -> Rect:
    xs, ys = [t[0] for t in tiles], [t[1] for t in tiles]
    return min(xs), min(ys), max(xs), max(ys)


def _shore(c: Canvas, tiles) -> list[tuple[int, int]]:
    inside = set(tiles)
    out, seen = [], set()
    for t in tiles:
        for nb in c.neighbors(*t, diagonal=True):
            if nb not in inside and nb not in seen and not c.has(*nb, WATER):
                seen.add(nb)
                out.append(nb)
    return out


def _wobbly_path(pts, rng: random.Random, wobble: float, step: float = 6.0) -> list[tuple[float, float]]:
    out = [tuple(map(float, pts[0]))]
    for a, b in zip(pts, pts[1:]):
        d = _dist(a, b)
        k = max(1, int(d / step))
        px, py = (-(b[1] - a[1]) / (d or 1), (b[0] - a[0]) / (d or 1))
        off = 0.0
        for j in range(1, k + 1):
            t = j / k
            off = 0.0 if j == k else max(-wobble, min(wobble, off + rng.uniform(-wobble, wobble) * 0.6))
            out.append((a[0] + (b[0] - a[0]) * t + px * off, a[1] + (b[1] - a[1]) * t + py * off))
    return out


def _free_spot(ctx: GenContext, rng: random.Random, radius: float, tries: int = 300) -> tuple[int, int]:
    """A random spot whose disc avoids bases, zones and water."""
    c, n = ctx.canvas, ctx.size
    starts = ctx.data.get("starts", [])
    best, best_score = None, -1.0
    for _ in range(tries):
        x, y = rng.randrange(int(radius), n - int(radius)), rng.randrange(int(radius), n - int(radius))
        bad = sum(1 for t in c.disc(x, y, radius) if c.has(*t, CLEAR | FLAT | WATER))
        score = min([_dist((x, y), s) for s in starts] or [n]) - bad * 3
        if bad == 0 and score > radius + 6:
            return x, y
        if score > best_score:
            best, best_score = (x, y), score
    return best


def elevation(ctx: GenContext) -> None:
    """Hills, smoothed so neighbouring tiles differ by at most one level."""
    c, n, es = ctx.canvas, ctx.size, ctx.spec.elevation
    rng = ctx.rng("elevation")
    hills = [(ctx.point(h.center), h.height, h.radius, h.name) for h in es.explicit]
    for _ in range(es.hills):
        r = rng.randint(*es.radius)
        hills.append((_free_spot(ctx, rng, r * 0.7), rng.randint(*es.height), r, None))
    target = [0] * (n * n)
    for k, (center, h, r, name) in enumerate(hills, start=1):
        h = max(0, min(MAX_ELEVATION, h))
        nz = ctx.noise(f"hill{k}", period=max(3.0, r / 1.5), octaves=2)
        for x, y in c.disc(center[0], center[1], r * 1.3):
            d = _dist((x, y), center) / (r * (0.75 + 0.5 * nz(x, y)))
            if d < 1:
                v = round(h * min(1.0, (1 - d) / 0.45))
                i = c.i(x, y)
                target[i] = max(target[i], v)
        ctx.add_area(name or f"hill_{k}", (center[0] - r, center[1] - r, center[0] + r, center[1] + r))
    for i, f in enumerate(c.flags):
        if f & (WATER | FLAT):
            target[i] = 0
    c.elevation[:] = _limit_slope(target, n)


def _limit_slope(e: list[int], n: int) -> list[int]:
    """Lower tiles until 8-neighbours differ by at most 1 (two-pass chamfer)."""
    e = list(e)
    for y in range(n):
        for x in range(n):
            i = x + y * n
            v = e[i]
            if x > 0:
                v = min(v, e[i - 1] + 1)
            if y > 0:
                v = min(v, e[i - n] + 1)
                if x > 0:
                    v = min(v, e[i - n - 1] + 1)
                if x < n - 1:
                    v = min(v, e[i - n + 1] + 1)
            e[i] = v
    for y in range(n - 1, -1, -1):
        for x in range(n - 1, -1, -1):
            i = x + y * n
            v = e[i]
            if x < n - 1:
                v = min(v, e[i + 1] + 1)
            if y < n - 1:
                v = min(v, e[i + n] + 1)
                if x < n - 1:
                    v = min(v, e[i + n + 1] + 1)
                if x > 0:
                    v = min(v, e[i + n - 1] + 1)
            e[i] = v
    return e


def roads(ctx: GenContext) -> None:
    """Paint roads along point paths; water on the way becomes a shallow ford."""
    c = ctx.canvas
    rng = ctx.rng("roads")
    shallows = terrain_id(ctx.biome.shallows)
    for k, r in enumerate(ctx.spec.roads, start=1):
        pts = [ctx.point(p) for p in r.points]
        if len(pts) < 2:
            raise ValueError("roads need at least two points")
        path = _wobbly_path(pts, rng, r.wobble, step=5) if r.wobble else [tuple(map(float, p)) for p in pts]
        tid = terrain_id(r.terrain if r.terrain is not None else ctx.biome.road)
        tiles, seen = [], set()
        for a, b in zip(path, path[1:]):
            for t in c.line(a, b, r.width):
                if t not in seen:
                    seen.add(t)
                    tiles.append(t)
        wet = [t for t in tiles if c.has(*t, WATER)]
        dry = [t for t in tiles if not c.has(*t, WATER)]
        c.paint(dry, tid)
        c.paint(wet, shallows)
        c.unmark(wet, WATER)
        c.mark(tiles, ROAD | NOTREE | CLEAR)
        c.unmark(tiles, WALL)
        if r.name:
            ctx.add_area(r.name, _bbox(tiles))


def cliffs(ctx: GenContext) -> None:
    """Experimental: cliff objects every 3 tiles along polylines (spec.cliffs and cliff choke walls)."""
    c = ctx.canvas
    ids = cliff_ids(ctx.biome.cliff)
    lines = [([ctx.point(p) for p in cs.points], cs.name) for cs in ctx.spec.cliffs]
    lines += [(pts, None) for pts in ctx.data.get("cliff_lines", [])]
    for k, (pts, name) in enumerate(lines, start=1):
        covered = []
        for a, b in zip(pts, pts[1:]):
            d = _dist(a, b)
            steps = max(1, int(d / 3))
            # Piece choice by the segment's direction in the diamond view (left-right, up-down, diagonal).
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180
            piece = ids[int(((ang + 22.5) % 180) // 45) * 2]
            for j in range(steps + 1):
                x = a[0] + (b[0] - a[0]) * j / steps
                y = a[1] + (b[1] - a[1]) * j / steps
                tx, ty = int(x), int(y)
                if not c.inside(tx, ty) or c.has(tx, ty, WATER):
                    continue
                c.place(piece, 0, tx + 0.5, ty + 0.5, size=1, block=False)
                fp = [t for t in c.disc(tx + 0.5, ty + 0.5, 1.6)]
                c.mark(fp, BLOCKED | NOTREE | CLEAR)
                covered += fp
        if covered:
            ctx.add_area(name or f"cliff_{k}", _bbox(covered))


def units(ctx: GenContext) -> None:
    """Explicit unit/building placements from spec.units (trees in the way are not planted)."""
    from ..render.colors import building_size, object_class
    c = ctx.canvas
    for u in ctx.spec.units:
        const = unit_id(u.unit)
        bx, by = ctx.point(u.position)
        size = building_size(const) if object_class(const) == "building" else 1
        x = bx + u.offset[0] + (0.5 if size % 2 else 0.0)
        y = by + u.offset[1] + (0.5 if size % 2 else 0.0)
        c.place(const, u.player, x, y, size=size, rotation=u.rotation)
        c.mark([t for t in c.footprint(x, y, size + 2) if c.inside(*t)], NOTREE)


def player_units(ctx: GenContext) -> None:
    """Town center, villagers and scout for each player start."""
    c = ctx.canvas
    for k, (p, (sx, sy)) in enumerate(zip(ctx.spec.players, ctx.data.get("starts", [])), start=1):
        if p.town_center:
            c.place(TOWN_CENTER, k, sx, sy, size=4)
        spots = [(sx - 3.5, sy + 0.5 + j) for j in range(-2, 3)] + [(sx + 0.5 + j, sy - 3.5) for j in range(-2, 3)]
        for x, y in spots[:p.villagers]:
            c.place(VILLAGER, k, x, y)
        if p.scout:
            c.place(SCOUT, k, sx + 3.5, sy + 3.5)


def forests(ctx: GenContext) -> None:
    """Choke walls, border ring, player woodlines, then clumps up to the coverage target."""
    c, n, fs, b = ctx.canvas, ctx.size, ctx.spec.forests, ctx.biome
    rng = ctx.rng("forests")
    nz = ctx.noise("forests", period=max(5.0, n / 14))

    def ok(x, y):
        return not c.flags[x + y * n] & (WATER | BLOCKED | NOTREE | CLEAR | ROAD | FOREST)

    chosen: list = []

    def take(tiles):
        for t in tiles:
            if ok(*t):
                c.flags[c.i(*t)] |= FOREST
                chosen.append(t)

    take([(x, y) for y in range(n) for x in range(n) if c.has(x, y, WALL)])
    if fs.border > 0:
        bn = ctx.noise("border", period=6)
        take([(x, y) for y in range(n) for x in range(n)
              if min(x, y, n - 1 - x, n - 1 - y) < fs.border * (0.6 + 0.8 * bn(x, y))])
    starts = ctx.data.get("starts", [])
    for (sx, sy), p in zip(starts, ctx.spec.players):
        for w in range(fs.player_woodlines):
            a = rng.random() * 2 * math.pi
            for _ in range(40):
                d = p.base_radius + rng.uniform(1.5, 5)
                x, y = int(sx + d * math.cos(a)), int(sy + d * math.sin(a))
                if c.inside(x, y) and ok(x, y):
                    take(c.grow((x, y), fs.woodline_size, rng, ok, weight=nz))
                    break
                a += 0.7
    target = int(fs.coverage * n * n)
    clump = max(12, (target - len(chosen)) // max(1, fs.clumps))
    attempts = 0
    while len(chosen) < target and attempts < fs.clumps * 20:
        attempts += 1
        x, y = rng.randrange(n), rng.randrange(n)
        if not ok(x, y) or nz(x, y) < 0.42:
            continue
        take(c.grow((x, y), int(clump * rng.uniform(0.5, 1.5)), rng, ok, weight=nz))
    for (sx, sy), p in zip(starts, ctx.spec.players):
        for _ in range(fs.stragglers):
            for _ in range(30):
                a, d = rng.random() * 2 * math.pi, rng.uniform(4.5, max(5.0, p.base_radius - 1))
                x, y = int(sx + d * math.cos(a)), int(sy + d * math.sin(a))
                if c.inside(x, y) and not c.has(x, y, WATER | BLOCKED | CLEAR | ROAD | FOREST):
                    c.flags[c.i(x, y)] |= FOREST
                    chosen.append((x, y))
                    break
    forest_t, tree = terrain_id(b.forest), unit_id(b.tree) if b.tree is not None else tree_for_forest(b.forest)
    for x, y in chosen:
        c.terrain[c.i(x, y)] = forest_t
        c.place(tree, 0, x + 0.5, y + 0.5)
    ctx.data["forest_tiles"] = len(chosen)


def resources(ctx: GenContext) -> None:
    """Per-player gold, stone, berries, sheep and deer; neutral piles; fish in water bodies."""
    c, rs = ctx.canvas, ctx.spec.resources
    rng = ctx.rng("resources")
    starts = ctx.data.get("starts", [])
    avoid = WATER | BLOCKED | CLEAR | ROAD

    def fits(tx, ty):
        return (c.inside(tx, ty) and not c.has(tx, ty, avoid)
                and not any(c.has(*nb, BLOCKED) for nb in c.neighbors(tx, ty, True)))

    def pile(const, count, center, band, player=0):
        for _ in range(80):
            a, d = rng.random() * 2 * math.pi, rng.uniform(*band)
            x, y = int(center[0] + d * math.cos(a)), int(center[1] + d * math.sin(a))
            cluster = c.grow((x, y), count, rng, fits)
            if len(cluster) < count:
                continue
            for tx, ty in cluster:
                c.place(const, player, tx + 0.5, ty + 0.5)
            return cluster
        return []

    for k, s in enumerate(starts, start=1):
        for size in rs.gold:
            pile(GOLD, size, s, rs.gold_distance)
        for size in rs.stone:
            pile(STONE, size, s, rs.stone_distance)
        if rs.berries:
            pile(BERRIES, rs.berries, s, rs.berries_distance)
        for _ in range(rs.sheep):
            pile(SHEEP, 1, s, (3.5, 6.5), player=k)
        for _ in range(rs.deer):
            pile(DEER, 1, s, rs.deer_distance)
    n = ctx.size
    far = (n * 0.2, n * 0.45)
    center = ((n - 1) / 2, (n - 1) / 2)
    for size in rs.neutral_gold:
        pile(GOLD, size, center, far)
    for size in rs.neutral_stone:
        pile(STONE, size, center, far)
    for body in ctx.data.get("water_bodies", []):
        deep = [t for t in body["tiles"]
                if c.has(*t, WATER) and all(c.has(*nb, WATER) for nb in c.neighbors(*t, True))]
        rng.shuffle(deep)
        placed = []
        for t in deep:
            if len(placed) >= body["fish"]:
                break
            if all(_dist(t, q) >= 3 for q in placed):
                placed.append(t)
                c.place(FISH, 0, t[0] + 0.5, t[1] + 0.5, block=False)


STEPS: dict[str, Callable[[GenContext], None]] = {
    "base_terrain": base_terrain,
    "players": players,
    "zones": zones,
    "water": water,
    "elevation": elevation,
    "roads": roads,
    "cliffs": cliffs,
    "units": units,
    "player_units": player_units,
    "forests": forests,
    "resources": resources,
}
DEFAULT_PIPELINE = list(STEPS)
