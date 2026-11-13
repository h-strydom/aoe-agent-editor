"""AI toolbox skills: blocks of rules an AI spec turns on by key (docs/ai-toolbox.md).

Each skill is modelled on a mechanism RoR's own scripts use (modes/Pompeii/resources/_common/ai), named in its
docstring, and stays unverified in game until a probe or playtest confirms it. The spec compiler (spec.py) calls
these from `_body`, one difficulty level at a time:

- `composition`: the army mix, by unit line, growing with the `grow` stages, plus the buildings that make it
- `defense`: a home guard and an answer to attacks on the town (recalls a wave)
- `retreat`: pulls a wave home when it has lost a share of the army
- `farms`: keeps farming (another farm when every farm is worked)
- `water`: caps on fishing boats and warships
- `goal`: plays for a stockpile (stops spending that resource on units once past a threshold)

Goals 35-38 and timer 7 are this module's (spec.py's other goals and timers leave them free).
"""
from __future__ import annotations

import math

# RoR unit lines (default/alternateConstants.per 234-269; airef for fishing boats): training a line trains its
# current upgrade, so Clubmen become Axemen after the upgrade without a new rule. `(train catapult-trireme-line)`
# in default/units.per proves line training in RoR; the fishing line (-287) is from airef, unverified.
# Not the Bowman: RoR's bowman-line (-299) doesn't train ("replace with bowman-line when added", default/units.per
# 727; Farming playtest 2026-11-13: no Bowmen at all), and the Bowman upgrades into nothing (the Improved Bowman is
# its own unit), so it trains by unit id as RoR's scripts do (`bowman 4`).
LINES = {"ror": {
    "CLUBMAN": -266, "AXEMAN": -266,
    "IMPROVED_BOWMAN": -298, "COMPOSITE_BOWMAN": -298,
    "SHORT_SWORDSMAN": -294, "BROAD_SWORDSMAN": -294, "LONG_SWORDSMAN": -294, "LEGION": -294,
    "CAVALRY": -295, "HEAVY_CAVALRY": -295, "CATAPHRACT": -295,
    "CHARIOT": -291, "SCYTHE_CHARIOT": -291,
    "HORSE_ARCHER": -293, "HEAVY_HORSE_ARCHER": -293,
    "WAR_ELEPHANT": -292, "ARMORED_ELEPHANT": -292,
    "HOPLITE": -290, "PHALANX": -290, "CENTURION": -290,
    "BALLISTA": -289, "HELEPOLIS": -289,
    "STONE_THROWER": -288, "CATAPULT": -288, "HEAVY_CATAPULT": -288,
    "SCOUT_SHIP": -285, "WAR_GALLEY": -285, "TRIREME": -285,
    "CATAPULT_TRIREME": -284, "JUGGERNAUT": -284,
    "FISHING_BOAT": -287, "FISHING_SHIP": -287,
}}
ROLES = ("core", "support", "raiders")
DEFAULT_MIX = {"core": 55, "support": 35, "raiders": 10}       # % of the army per role
MAX_MAKERS = 3                                                  # production buildings of a kind, at most
UNITS_PER_MAKER = 6                                             # one production building per this many of its units
ECONOMY_FIRST = 80   # % of a grow stage's villagers before that stage's army trains (Farming playtest 2026-11-13)
WAVE_POP, WAVE_FLOOR, WAVE_OUT, POP_NOW = 35, 36, 37, 38        # goals: army at launch, retreat floor, out, now
RECALL_TIMER, RECALL_EVERY = 7, 60
DEFENSE_KEYS = {"home", "radius"}
COMPOSITION_KEYS = {"units", "size", "start", "mix"}
WATER_KEYS = {"fishing", "warships", "trade"}
TRADE_BOAT_LINE = -283           # RoR's trade-boat-line: `(train trade-boat-line)` in default/trade.per 24
NAVAL_UNITS = {"SCOUT_SHIP", "WAR_GALLEY", "TRIREME", "CATAPULT_TRIREME", "JUGGERNAUT", "FIRE_GALLEY"}


class SkillError(ValueError):
    pass


def _rule(facts: list[str], actions: list[str], comment: str = "") -> str:
    head = f"(defrule{f' ; {comment}' if comment else ''}\n"
    return head + "".join(f"\t{f}\n" for f in facts) + "=>\n" + "".join(f"\t{a}\n" for a in actions) + ")\n"


def line_or_unit(name: str, game: str, names) -> str:
    """The constant a train rule uses: the unit's line where it has one (a defconst named my-<line>), else the
    unit itself (names.const)."""
    line = LINES.get(game, {}).get(name)
    if line is None:
        return names.const(name, "object")
    const = f"my-line{abs(line)}"
    names.ids[f"line{line}"] = (const, line)
    return const


def base_setup() -> list[str]:
    """Setup every toolbox AI starts with. First: the engine stops scaling this script's strategic numbers by
    difficulty (airef: scenario AIs get attack groups and enemy response scaled to 0.2-0.8 below Hardest unless this
    is set first); the toolbox's levels do the scaling instead. Then no villager explores: an explorer walks into
    enemies (Trade's Canaanites lost villagers that way, playtest 2026-11-13)."""
    return ["(set-strategic-number sn-do-not-scale-for-difficulty-level 1)",
            "(set-strategic-number sn-percent-civilian-explorers 0)",
            "(set-strategic-number sn-cap-civilian-explorers 0)",
            "(set-strategic-number sn-minimum-civilian-explorers 0)"]


def rush_gates(spec: dict, names) -> tuple[list[str], list[str]]:
    """(villager facts, army facts) for `rush: TOOL_AGE`: until that age is researched the army waits, and villagers
    wait once food reaches 400, so the food piles up for the age (Trade's Canaanites never reached the Tool Age:
    villagers and soldiers spent its food first, playtest 2026-11-13)."""
    age = spec.get("rush")
    if not age:
        return [], []
    const = names.const(age, "tech")
    done = f"(research-completed {const})"
    return [f"(or {done} (food-amount < 400))"], [done]


def spend_gate(spec: dict) -> list[str]:
    """Facts that hold back spending for `goal: {stockpile: {food: 2000, hold_from: 1200}}`: once the stockpile
    passes hold_from, units that cost it wait, so the pile climbs to the goal (escrow-free; AiBuilder gates
    spending by amounts the same way)."""
    stock = (spec.get("goal") or {}).get("stockpile") or {}
    out = []
    for res, amount in stock.items():
        if res == "hold_from":
            continue
        hold = int(stock.get("hold_from", int(amount) * 0.6))
        out.append(f"({res}-amount < {hold})")
    return out


def composition(spec: dict, game: str, names, grow_stages: int | None, grow_goal: int) -> list[str]:
    """Rules for `composition: {units: {core: [AXEMAN], support: [BOWMAN], raiders: [SCOUT]}, size: 30, start: 6,
    mix: {core: 55, support: 35, raiders: 10}}`: the army grows from `start` to `size` soldiers over the grow stages
    (or is `size` from the start without grow), split by role and evenly within a role, trained by line. The
    buildings that make them follow: one per UNITS_PER_MAKER of the units they make, up to MAX_MAKERS (a few
    Scouts need one Stable; Farming's Lower Egypt built three, playtest 2026-11-13). With grow, a stage's army waits
    until ECONOMY_FIRST % of that stage's villagers are there, so the economy grows a little before each bigger army
    (soldiers came first in the rule order and starved its food, same playtest)."""
    from .. import tables
    comp = spec["composition"]
    if not isinstance(comp, dict) or set(comp) - COMPOSITION_KEYS or "units" not in comp:
        raise SkillError(f"composition is {{units: {{core: [...], support: [...], raiders: [...]}}, size, start, "
                         f"mix}}, got {comp!r}")
    units = comp["units"]
    if set(units) - set(ROLES):
        raise SkillError(f"composition.units roles are {ROLES}, got {sorted(units)}")
    mix = {**DEFAULT_MIX, **(comp.get("mix") or {})}
    used = {r: list(units.get(r) or []) for r in ROLES}
    share = {r: mix[r] for r in ROLES if used[r]}
    total = sum(share.values()) or 1
    size, start = int(comp.get("size", 20)), int(comp.get("start", min(6, int(comp.get("size", 20)))))
    gate = spend_gate(spec) + rush_gates(spec, names)[1]
    stages = grow_stages or 0
    grow = spec.get("grow") or {}
    v0 = int(spec.get("villagers") or 0)
    vn = max(v0, int(grow.get("villagers") or round(int(grow.get("to", 200)) * 0.4))) if grow else v0

    def counts(army: float) -> dict[str, int]:
        out = {}
        for role, names_ in used.items():
            if not names_:
                continue
            each = army * share[role] / total / len(names_)
            for n in names_:
                out[n] = max(1, round(each))
        return out

    rules = []
    makers: dict[str, str] = {}
    for n in [n for r in ROLES for n in used[r]]:
        made = [b for b in (tables.info(n, game) or {}).get("made_at") or [] if b != "BUILDER"]
        if made:
            makers[n] = made[0]
    for k in range(0, stages + 1) if stages else [None]:
        army = size if k is None else start + (size - start) * k / stages
        stage = [] if k is None else [f"(goal {grow_goal} {k})"]
        label = "army" if k is None else f"army stage {k}/{stages}"
        economy = []
        if k:                                       # stage 0 is the starting army: no wait
            villagers = math.floor((v0 + (vn - v0) * k / stages) * ECONOMY_FIRST / 100)
            economy = [f"(civilian-population >= {villagers})"] if villagers > 0 else []
        made = counts(army)
        for n, c in made.items():
            const = line_or_unit(n, game, names)
            rules.append(_rule([*stage, *gate, *economy, f"(unit-type-count-total {const} < {c})",
                                f"(can-train {const})"], [f"(train {const})"], f"{label}: {n} x{c}"))
        for b in sorted(set(makers.values())):
            const = names.const(b, "object")
            units_here = sum(c for n, c in made.items() if makers.get(n) == b)
            want = min(MAX_MAKERS, max(1, math.ceil(units_here / UNITS_PER_MAKER)))
            rules.append(_rule([*stage, f"(building-type-count-total {const} < {want})", f"(can-build {const})"],
                               [f"(build {const})"], f"{label}: {b} x{want}"))
    return rules


def defense(spec: dict) -> tuple[list[str], list[str]]:
    """(setup, rules) for `defense: {home: 30, radius: 14}`: idle soldiers gather at the town center and soldiers
    answer enemies seen within `radius` tiles (default/init.per 137 and 1768, AiBuilder setup 1082-1092); an attack
    on the town while a wave is out recalls it (up-retreat-now, default/tsa.per's retreat), at most once a minute.
    `home` is the share of soldiers attacks leave behind (the attack's sn-percent-attack-soldiers, set in spec.py)."""
    d = spec["defense"]
    if not isinstance(d, dict) or set(d) - DEFENSE_KEYS:
        raise SkillError(f"defense is {{home: 30, radius: 14}}, got {d!r}")
    radius = int(d.get("radius", 14))
    # Not sn-allow-civilian-defense: RoR's default AI sets 3 within its own micro, but on its own it sent Trade's
    # Canaanite villagers to fight (playtest 2026-11-13).
    setup = ["(set-strategic-number sn-gather-idle-soldiers-at-center 1)",
             f"(set-strategic-number sn-enemy-sighted-response-distance {radius})",
             f"(set-goal {WAVE_OUT} 0)", f"(enable-timer {RECALL_TIMER} {RECALL_EVERY})"]
    rules = [_rule(["(town-under-attack)", f"(goal {WAVE_OUT} 1)", f"(timer-triggered {RECALL_TIMER})"],
                   ["(up-retreat-now)", f"(set-goal {WAVE_OUT} 0)", f"(disable-timer {RECALL_TIMER})",
                    f"(enable-timer {RECALL_TIMER} {RECALL_EVERY})"], "defense: the town is attacked, recall the wave"),
             _rule([f"(timer-triggered {RECALL_TIMER})"],
                   [f"(disable-timer {RECALL_TIMER})", f"(enable-timer {RECALL_TIMER} {RECALL_EVERY})"],
                   "defense: recall check every minute")]
    return setup, rules


def home_percent(spec: dict) -> int | None:
    """The share of soldiers an attack sends, from defense.home (None: the attack's own `percent`)."""
    d = spec.get("defense")
    return None if not d else 100 - int(d.get("home", 30))


def wave_actions(spec: dict) -> list[str]:
    """Actions added to each land attack: note the army at launch and the floor a retreat triggers at, and mark
    the wave out (for retreat and defense)."""
    if not (spec.get("retreat") or spec.get("defense")):
        return []
    out = [f"(set-goal {WAVE_OUT} 1)"]
    if spec.get("retreat"):
        keep = 100 - int(spec["retreat"].get("lost", 50))
        out = [f"(up-get-fact military-population 0 {WAVE_POP})", f"(up-modify-goal {WAVE_FLOOR} g:= {WAVE_POP})",
               f"(up-modify-goal {WAVE_FLOOR} c:* {keep})", f"(up-modify-goal {WAVE_FLOOR} c:/ 100)", *out]
    return out


def retreat(spec: dict) -> list[str]:
    """Rules for `retreat: {lost: 50}`: once the army is down to (100 - lost)% of its size at launch, the wave
    comes home (up-retreat-now; default/tsa.per 382-403 retreats when it's losing)."""
    r = spec["retreat"]
    if not isinstance(r, dict) or set(r) - {"lost"}:
        raise SkillError(f"retreat is {{lost: 50}}, got {r!r}")
    return [_rule([f"(goal {WAVE_OUT} 1)"], [f"(up-get-fact military-population 0 {POP_NOW})"],
                  "retreat: count the army"),
            _rule([f"(goal {WAVE_OUT} 1)", f"(up-compare-goal {POP_NOW} g:< {WAVE_FLOOR})"],
                  ["(up-retreat-now)", f"(set-goal {WAVE_OUT} 0)"],
                  f"retreat: the wave lost {int(r.get('lost', 50))}% of the army, come home")]


def farms(spec: dict, names) -> list[str]:
    """`farms: 40` (or auto: 40 when the plan farms): another farm whenever every farm is worked (idle-farm-count,
    as default/buildings.per 850-920 farms), once the player has one."""
    cap = spec.get("farms")
    if cap in (None, 0, False):
        return []
    cap = 40 if cap in ("auto", True) else int(cap)
    f = names.const("FARM", "object")
    return [_rule([f"(building-type-count-total {f} < {cap})", "(idle-farm-count < 1)", f"(can-build {f})"],
                  [f"(build {f})"], f"farms: another when every farm is worked, up to {cap}")]


def water(spec: dict, game: str, names) -> list[str]:
    """`water: {fishing: 3, warships: 2, trade: 4}`: train up to those many fishing boats, warships and Trade Boats
    (by line), and no more from these rules (AiBuilder's fishing-cap, default/units.per's per-line caps). Trade Boats
    trade by themselves once trained, with allied and neutral Docks: RoR's own AI only trains them
    (default/trade.per)."""
    w = spec["water"]
    if not isinstance(w, dict) or set(w) - WATER_KEYS:
        raise SkillError(f"water is {{fishing: 3, warships: 2}}, got {w!r}")
    rules = []
    for key, unit in (("fishing", "FISHING_BOAT"), ("warships", "SCOUT_SHIP")):
        n = int(w.get(key, 0))
        if n:
            const = line_or_unit(unit, game, names)
            rules.append(_rule([f"(unit-type-count-total {const} < {n})", f"(can-train {const})"],
                               [f"(train {const})"], f"water: {key} up to {n}"))
    n = int(w.get("trade", 0))
    if n:
        const = "my-trade-boat-line"
        names.ids["trade-boat-line"] = (const, TRADE_BOAT_LINE)
        rules.append(_rule([f"(unit-type-count-total {const} < {n})", f"(can-train {const})"],
                           [f"(train {const})"], f"water: trade boats up to {n}"))
    return rules


# upgrades: research lines by kind, in age order (RoR's tech names, data/tables/ror.json). Unit-line upgrades come
# from the army's composition.
ECONOMY_TECHS = ("DOMESTICATION", "WOODWORKING", "GOLD_MINING", "STONE_MINING", "WHEEL", "PLOW", "ARTISANSHIP",
                 "IRRIGATION", "CRAFTMANSHIP", "COINAGE")
MILITARY_TECHS = ("TOOLWORKING", "LEATHER_ARMOR_FOR_INFANTRY", "LEATHER_ARMOR_ARCHERS", "LEATHER_ARMOR_FOR_CAVALRY",
                  "METALWORKING", "BRONZE_SHIELD", "SCALE_ARMOR_FOR_INFANTRY", "SCALE_ARMOR_ARCHERS",
                  "SCALE_ARMOR_CAVALRY", "METALLURGY", "IRON_SHIELD", "CHAIN_MAIL_FOR_INFANTRY",
                  "CHAIN_MAIL_ARCHERS", "CHAIN_MAIL_CAVALRY")
LINE_UPGRADES = {-266: ("AXE",), -298: ("COMPOSITE_BOW",),
                 -294: ("BROAD_SWORD", "LONG_SWORD", "LEGION"), -295: ("HEAVY_CAVALRY", "CATAPHRACT"),
                 -291: ("HEAVY_CHARIOTS",), -293: ("ADVANCED_HORSE_ARCHER",), -292: ("ARMORED_ELEPHANT",),
                 -290: ("PHALANGITE", "CENTURION"), -289: ("HELEPOLIS",), -288: ("CATAPULT", "HEAVY_CATAPULT"),
                 -285: ("MEDIUM_WAR_SHIP", "TRIREME"), -284: ("JUGGERNAUGHT",)}
UPGRADE_KEYS = {"first", "army_at", "villagers_at"}


def upgrades(spec: dict, game: str, names) -> list[str]:
    """Rules for `upgrades: {first: economy, army_at: 10, villagers_at: 20}` (or just `economy`, `military`,
    `balanced`): research economy and military lines, the favoured kind first. Economy first: military research
    waits until the army has `army_at` soldiers. Military first: economy research waits for `villagers_at`
    villagers. Balanced: both as soon as they can be afforded. Unit upgrades follow the composition's lines and
    never wait: an economy-first AI still gets its Battle Axe (Farming playtest 2026-11-13: no Axemen by 25:00).
    AiBuilder's technologies.per gates its upgrade groups by villager counts the same way."""
    u = spec["upgrades"]
    u = {"first": u} if isinstance(u, str) else dict(u)
    if set(u) - UPGRADE_KEYS or u.get("first", "balanced") not in ("economy", "military", "balanced"):
        raise SkillError(f"upgrades is economy, military, balanced or {{first, army_at, villagers_at}}, got {u!r}")
    first = u.get("first", "balanced")
    eco_gate = [f"(civilian-population >= {int(u.get('villagers_at', 20))})"] if first == "military" else []
    mil_gate = [f"(soldier-count >= {int(u.get('army_at', 10))})"] if first == "economy" else []
    lines = {LINES.get(game, {}).get(n) for r in ROLES
             for n in ((spec.get("composition") or {}).get("units") or {}).get(r) or []}
    unit_techs = [t for line in sorted(x for x in lines if x is not None) for t in LINE_UPGRADES.get(line, ())]
    rules = []
    for techs, gate, kind in ((tuple(unit_techs), [], "unit"), (ECONOMY_TECHS, eco_gate, "economy"),
                              (MILITARY_TECHS, mil_gate, "military")):
        for t in techs:
            const = names.const(t, "tech")
            rules.append(_rule([*gate, f"(can-research {const})"], [f"(research {const})"], f"upgrades ({kind}): {t}"))
    return rules
