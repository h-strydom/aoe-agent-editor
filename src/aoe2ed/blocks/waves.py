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
          keepalive_sec: int = 30, chase: dict | None = None, name: str = "Wave") -> dict:
    """Spawn `waves` ([{"at": seconds, "units": {TYPE: count}, "spawn": idx?}]) for `enemy`
    at the `spawns` areas (rotating unless a wave names one) and attack-move them to `target`.
    scale_var: for each level L in 1..scale_max with var >= L, `scale_extra` units are added
    to every wave (e.g. a difficulty/heat value loaded from the campaign bank).
    on_wave: extra effects run with each wave (e.g. pay the player for surviving it).
    A looping keep-alive re-issues attack-move for all enemy units every `keepalive_sec`.
    chase: {"player": 1, "unit": "TRADE_CART_FULL", "interval_sec": 5} makes the wave units hunt
    the first living unit of that type instead (an XS rule re-targets them every interval); with
    none left they return to `target`. Unverified in game so far.

    Triggers created: "<name> 1".."<name> N", "<name> N +L" (scaling), "<name> Keepalive"."""
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
    if chase:
        ctx.xs(_chase_xs(name, enemy, chase, {u for w in waves for u in w["units"]} | set(scale_extra or {}),
                         (tx, ty), ctx.secs(chase.get("interval_sec", 5))))
    elif keepalive_sec:
        ctx.trigger(f"{name} Keepalive", [{"type": "timer", "timer": keepalive_sec}],
                    [{"type": "attack_move", "source_player": enemy, "location": [tx, ty],
                      "object_type": "MILITARY"}], looping=True)
    return {"triggers": names, "count": len(waves)}


def near_tiles(ctx: Ctx, at, count: int, min_dist: float = 0,
               exclude: set | None = None) -> list[tuple[int, int]]:
    """`count` distinct tiles nearest to `at` (point or area), at least `min_dist` from its centre,
    skipping tiles in `exclude` (which is updated with the tiles returned)."""
    exclude = exclude if exclude is not None else set()
    cx, cy = ctx.point(at)
    size = ctx.scenario.map_manager.map_size
    tiles, r = [], 0
    while len(tiles) < count and r < 60:
        r += 1
        tiles = sorted(((x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)
                        if 0 <= x < size and 0 <= y < size and (x, y) not in exclude
                        and ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 >= min_dist),
                       key=lambda t: ((t[0] - cx) ** 2 + (t[1] - cy) ** 2, t))
    tiles = tiles[:count]
    exclude.update(tiles)
    return tiles


def spawn(ctx: Ctx, *, unit: str | int, count: int, player: int = 1, at, min_dist: float = 0) -> list[dict]:
    """Effect dicts that create `count` units on distinct tiles near `at` (point or area name/rect),
    nearest first, at least `min_dist` tiles from its centre (e.g. 4 to clear a Town Center).
    Verified in game: several create_object effects on the same tile place only one unit.
    Usable as a whole `effects:` value or spliced into a longer effects list."""
    return [{"type": "create_object", "object_list_unit_id": unit, "source_player": player,
             "location": [x, y]} for x, y in near_tiles(ctx, at, count, min_dist)]


def _chase_xs(name: str, enemy: int, chase: dict, hunter_types: set, fallback: tuple[int, int],
              interval: int) -> str:
    from ..datasets import object_id
    key = "".join(ch for ch in name if ch.isalnum())
    prey = object_id(chase["unit"])
    task = "".join(
        f"    aoe2edHunt{key} = xsGetPlayerUnitIds({enemy}, {object_id(u)}, aoe2edHunt{key});\n"
        f"    if (xsArrayGetSize(aoe2edHunt{key}) > 0) {{ xsTaskUnits(aoe2edHunt{key}, cActionTypeAttackMove, pos); }}\n"
        for u in sorted(hunter_types, key=str))
    return f"""// ---- aoe2ed waves chase: {name} ----
int aoe2edPrey{key} = -1;  // arrays are reused: xsGetPlayerUnitIds(..., -1) allocates a new one
int aoe2edHunt{key} = -1;
rule aoe2edChase{key}
    active
    minInterval {interval}
{{
    aoe2edPrey{key} = xsGetPlayerUnitIds({chase.get("player", 1)}, {prey}, aoe2edPrey{key});
    vector pos = vector({fallback[0]}, {fallback[1]}, 0);
    if (xsArrayGetSize(aoe2edPrey{key}) > 0) {{
        pos = xsGetUnitPosition(xsArrayGetInt(aoe2edPrey{key}, 0));
    }}
{task}}}
"""
