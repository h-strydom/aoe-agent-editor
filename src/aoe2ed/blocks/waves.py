"""Enemy waves: timed spawns that attack-move toward a target, optionally scaled by a variable."""
from __future__ import annotations

from .base import Ctx, spread


def escalating(duration_min: float, *, interval_sec: int = 90, first_at_sec: int = 60,
               pools: list[dict], base: int = 4, growth: float = 1.25, boss_every: int = 0,
               boss: dict | None = None) -> list[dict]:
    """Generate a wave list. pools: [{"from_min": 0, "units": ["MILITIA", "SPEARMAN"]}, ...] — the
    latest pool whose from_min has passed is used, its units split evenly. Every `boss_every`th
    wave adds `boss` ({TYPE: count})."""
    waves = []
    t, i = first_at_sec, 0
    while t < duration_min * 60:
        pool = [p for p in pools if p["from_min"] * 60 <= t][-1]
        count = max(1, round(base * growth ** i))
        units: dict[str, int] = {}
        for k in range(count):
            u = pool["units"][k % len(pool["units"])]
            units[u] = units.get(u, 0) + 1
        if boss and boss_every and (i + 1) % boss_every == 0:
            for u, n in boss.items():
                units[u] = units.get(u, 0) + n
        waves.append({"at": t, "units": units})
        t += interval_sec
        i += 1
    return waves


def waves(ctx: Ctx, *, enemy: int = 2, spawns: list, target, waves: list[dict],
          scale_var: str | None = None, scale_extra: dict[str, int] | None = None, scale_max: int = 5,
          announce: str | None = "Wave {n} incoming!", on_wave: list[dict] | None = None,
          keepalive_sec: int = 30, name: str = "Wave") -> dict:
    """Spawn `waves` ([{"at": seconds, "units": {TYPE: count}, "spawn": idx?}]) for `enemy`
    at the `spawns` areas (rotating unless a wave names one) and attack-move them to `target`.
    scale_var: for each level L in 1..scale_max with var >= L, `scale_extra` units are added
    to every wave (e.g. a difficulty/heat value loaded from the campaign bank).
    on_wave: extra effects run with each wave (e.g. pay the player for surviving it).
    A looping keep-alive re-issues attack-move for all enemy units every `keepalive_sec`."""
    tx, ty = ctx.point(target)
    areas = [ctx.area(s) for s in spawns]
    names = []
    for n, w in enumerate(waves, 1):
        area = areas[w.get("spawn", (n - 1) % len(areas))]
        total = sum(w["units"].values())
        spots = iter(spread(area, total))
        effects = [{"type": "create_object", "object_list_unit_id": u, "source_player": enemy,
                    "location": list(next(spots))}
                   for u, c in w["units"].items() for _ in range(c)]
        effects.append({"type": "attack_move", "source_player": enemy, "area": list(area),
                        "location": [tx, ty]})
        if announce:
            effects.append({"type": "display_instructions", "source_player": 1, "display_time": 6,
                            "message": announce.format(n=n), "instruction_panel_position": 0})
        effects += on_wave or []
        at = ctx.secs(w["at"])
        trig = f"{name} {n}"
        ctx.trigger(trig, [{"type": "timer", "timer": at}], effects)
        names.append(trig)
        if scale_var and scale_extra:
            for lvl in range(1, scale_max + 1):
                extra_spots = iter(spread(area, sum(scale_extra.values())))
                ex = [{"type": "create_object", "object_list_unit_id": u, "source_player": enemy,
                       "location": list(next(extra_spots))}
                      for u, c in scale_extra.items() for _ in range(c)]
                ex.append({"type": "attack_move", "source_player": enemy, "area": list(area),
                           "location": [tx, ty]})
                ctx.trigger(f"{trig} +{lvl}", [
                    {"type": "timer", "timer": at},
                    {"type": "variable_value", "variable": ctx.var(scale_var), "comparison": "LARGER_OR_EQUAL",
                     "quantity": lvl}], ex)
    if keepalive_sec:
        ctx.trigger(f"{name} Keepalive", [{"type": "timer", "timer": keepalive_sec}],
                    [{"type": "attack_move", "source_player": enemy, "location": [tx, ty],
                      "object_type": "MILITARY"}], looping=True)
    return {"triggers": names, "count": len(waves)}


def spawn(ctx: Ctx, *, unit: str | int, count: int, player: int = 1, at, min_dist: float = 0) -> list[dict]:
    """Effect dicts that create `count` units on distinct tiles near `at` (point or area name/rect),
    nearest first, at least `min_dist` tiles from its centre (e.g. 4 to clear a Town Center).
    Verified in game: several create_object effects on the same tile place only one unit."""
    cx, cy = ctx.point(at)
    tiles, r = [], 0
    while len(tiles) < count and r < 40:
        r += 1
        tiles = sorted(((x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)
                        if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 >= min_dist),
                       key=lambda t: ((t[0] - cx) ** 2 + (t[1] - cy) ** 2, t))
    return [{"type": "create_object", "object_list_unit_id": unit, "source_player": player,
             "location": [x, y]} for x, y in tiles[:count]]
