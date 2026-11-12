"""AI specs: a readable description of a computer player, compiled to an AoE2 DE / Return of Rome .per script.

Spec (YAML/JSON; every key optional):

  name: Troy                         # shown in the editor's player AI box
  gatherers: auto                    # villager split: auto (default) follows what the build order and keep list
                                     #   cost, blended with AIBuilder's 45/30/15/10; or {food, wood, gold, stone} %
  villagers: 25                      # keep training villagers up to this many (default: off)
  houses: true                       # build a house whenever housing is nearly full (default true)
  build_order:                       # worked through in order; a step is done when its count is reached
    - {build: BARRACKS}              #   count = how many in total (built or being built), default 1
    - {train: CLUBMAN, count: 5}     #   count = how many alive in total
    - {research: TOOL_AGE}           #   techs and ages
  window: 3                          # how many steps it works on at once, from the current one (default 3; 1 = one
                                     #   at a time, which leaves training one unit at a time behind everything else)
  step_timeout: 180                  # seconds before a step that can't happen is checked: skipped if it's affordable
                                     #   (so it's disabled or impossible); waited for up to 4 times while it isn't
  keep: [{train: BOWMAN, count: 10}, {build: BARRACKS}]   # keep these topped up / rebuilt
                                     #   lifetime: true = count is all it ever makes (never replaced)
                                     #   when: {soldiers: 8} = only while that many soldiers stand at home
                                     #   (defend-soldier-count): upgrades once a defence stands
                                     #   when: {units: {WAR_GALLEY: 8}} = only once it has that many of each
                                     #   (a trade fleet once it rules the water)
  keep_from: start                   # start (default): the keep list works from the beginning; end: only once the
                                     #   build order is done
  rebalance: true                    # every minute, move 5% of villagers to a resource the plan spends that's
                                     #   running out (under 200), from the biggest pile over 400 (default true)
  transports: 2                      # water maps: keep this many transport ships from the start, so attacks can
  transport_unit: LIGHT_TRANSPORT    #   cross water (the engine ferries attack groups); default per game
  scout: auto                        # a ship that explores, so attacks across water find a target: auto (default:
                                     #   with naval attacks or transports), false, or a unit name
  levels: auto                       # play by the game's difficulty: auto scales this spec (as normal) for easy
                                     #   and hard; or {easy: {...}, normal: {...}, hard: {...}} overriding keys
  army: {civ: GREEK, share: 50}      # shift the keep list's soldiers toward the civ's bonus units (aoe2ed.civs):
                                     #   share % of them, its best `units` (2) reachable by max_age (else the
                                     #   build order's highest age, or `age`); exclude: units or buildings
  start: {trigger: 1}                # do nothing until the scenario's AI Script Goal effect sends 1; timers
                                     #   (attack first, step timeout) count from then
  grow: {to: 200, minutes: 60}       # macro toward a population of `to` over `minutes`, in `stages` (default 8)
                                     #   even steps: the villager target rises to `villagers` (default 40% of to),
                                     #   the keep list's soldiers (in proportion) to the rest less 10 spare, the
                                     #   buildings that make them along with the army (up to 4 each), town centers
                                     #   to `town_centers` (default 3: expansion) and dropsites to 3. Houses follow
                                     #   by themselves. levels: auto grows 3x slower on easy, 2x faster on hard
  attack:                            # omit or null = never attacks
    first: 600                       #   seconds into the game
    every: 240                       #   seconds between attacks
    min_group: 4                     #   idle soldiers needed before it attacks
    max_group: 12
    percent: 80                      #   share of idle soldiers that go (default 80)
    naval: false                     #   warships also attack on the same timing (default false)
    target: 1                        #   attack (and raid) this player, not the closest enemy (default)
    warm_up: {attacks: 3, min_group: 5, max_group: 8, every: 180}   # the first `attacks` land attacks are
                                     #   these smaller warnings (from `first`), then the main sizes and `every`
  raids:                             # small parties sent at the closest enemy's units, apart from attacks
    - units: [BOWMAN, SLINGER]       #   what a party is made of (up to `count`, taken in this order)
      count: 5                       #   party size (1-40); min: fewest worth sending (default count)
      first: 300                     #   seconds into the game; every: seconds between parties (default: once)
      start: {trigger: 2}            #   instead of first: when the scenario's AI Script Goal effect sends 2
      near: {x: 47, y: 20, radius: 6}   # take only units this close to the point (a landing party)
      target: villagers              #   villagers, buildings or any (default): the closest one it knows of;
                                     #   with nothing of that kind known, anything
      resend: 10                     #   the party's orders are renewed every this many seconds while one lives,
                                     #   so the AI's own tasking can't call it home (default 10)
      fallback: {x: 32, y: 58}       #   with nothing of the enemy's known, go there (aggressive) instead
  trade: {buy: {stone: 200}, sell: {food: 600, wood: 600}, every: 5}   # the Market: buy what's under its
                                     #   target while gold lasts; sell what's over its floor when gold runs low
                                     #   (under 150), one deal every `every` seconds (default 5)
  strategic_numbers: {sn-number-explore-groups: 1}     # raw engine settings (names checked)
  rules: "(defrule ...)"             # extra raw .per appended as is
  debug: false                       # announce each build step and attack in chat (for playtests)

Unit, building and tech names are the game's (RoR names for game: ror; see lookup). Scripted AIs never
resign: the engine only resigns when a script says (resign).

Attacks follow DE's AIBuilder (shipped with RoR, the designers' scenario AI): target the closest enemy, set
the share of soldiers that go, attack-now; warships separately. The setup enables DE's building system and full
response to sighted enemies, as AIBuilder does.

Raids remember their party's object ids when sent and re-target them every `resend` seconds: a party that is
only sent once is taken back by the engine's own tasking (RoR-RI Egypt 5 playtest, 2026-11-08: a landing party
ordered by triggers "moved left a bit and gave up"). The searches follow RoR's own scripts (default/dawn.per:
up-find-local, up-clean-search by distance, up-set-target-object, up-target-objects 1). Unverified in game.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

TOP_KEYS = {"name", "gatherers", "villagers", "houses", "build_order", "step_timeout", "keep", "attack",
            "strategic_numbers", "rules", "transports", "transport_unit", "debug", "report", "window", "keep_from",
            "rebalance", "scout", "levels", "start", "army", "grow", "raids", "trade", "provoked"}
# Difficulty levels: the script holds one copy of the rules per level, gated on goal LEVEL_GOAL, which the first
# rules set from the game's difficulty: (difficulty == x) as the game's own scripts test it. DE's Easiest and
# Standard are easiest/easy, Moderate is moderate; Hard, Hardest and Extreme play hard.
LEVELS = ("easy", "normal", "hard")
LEVEL_GOAL, ACTIVE_GOAL = 5, 6
LEVEL_FACTS = {1: ["(difficulty == easiest)", "(difficulty == easy)"], 2: ["(difficulty == moderate)"]}
# Easy barely attacks; hard keeps up the pressure. Nothing is free at any level: the AI gathers and pays for
# everything, sees only what it explores, and gets no extra resources or spawned units.
AUTO_LEVELS = {"easy": {"villagers": 0.7, "first": 2.5, "every": 4.0, "group": 0.5, "keep": 0.6, "grow": 3.0},
               "hard": {"villagers": 1.3, "first": 0.6, "every": 0.4, "group": 1.5, "keep": 1.5, "grow": 0.5}}
MIN_ATTACK_EVERY = 20                # seconds; hard's scaling never goes below this
# army: shift the keep list's soldiers toward the units the civ's bonuses favour (aoe2ed.civs).
ARMY_KEYS = {"civ", "share", "age", "max_age", "naval", "exclude", "units"}
AGE_TECHS = {"ror": {"TOOL_AGE": 2, "BRONZE_AGE": 3, "IRON_AGE": 4}}
NOT_SOLDIERS = {2, 4, 18, 20, 21}    # unit classes: trade boat, villager, priest, transport, fishing boat
NAVAL_CLASS = 22
TRANSPORT_UNITS = {"ror": "LIGHT_TRANSPORT", "aoe2": "TRANSPORT_SHIP"}
SCOUT_SHIPS = {"ror": "SCOUT_SHIP", "aoe2": "GALLEY"}
# The attack rule needs a known enemy building ((players-building-count any-enemy >= 1)); across water nothing
# finds one until a ship explores (Trojan War probe, 2026-11-05: first attack right after the first scout ship).
SCOUT_SNS = {"sn-number-boat-explore-groups": 1, "sn-minimum-boat-explore-group-size": 1,
             "sn-maximum-boat-explore-group-size": 1}
REBALANCE_TIMER, REBALANCE_EVERY, REBALANCE_STEP = 4, 60, 5
# Rebalancing reacts to a shortage (under POOR) of something the plan spends, taking from the biggest pile above
# RICH_TIERS[-1]. A fixed 800 pile never fired in the third Trojan War probe (2026-11-05): with the step window
# wood was spent as it came in, and food sat under 200 for 11 minutes. MIN_SHARE is the floor a share drops to.
RICH_TIERS, POOR, MIN_SHARE = (1600, 800, 400), 200, 5
ATTACK_KEYS = {"first", "every", "min_group", "max_group", "percent", "naval", "warm_up", "target"}
WARM_UP_KEYS = {"attacks", "min_group", "max_group", "every"}
LAND_ATTACKS_GOAL = 8                # land attacks launched so far (attack.warm_up)
STEP_KINDS = ("build", "train", "research")
STEP_GOAL, STEP_TIMER, ATTACK_TIMER, TARGET_GOAL, NAVAL_TIMER = 1, 1, 2, 2, 3
# AIBuilder's constants for (up-find-player enemy find-closest goal): the engine's stance and search ids.
ENEMY_STANCE, FIND_CLOSEST = 3, 2
# Always set, as AIBuilder's setup does: DE's building placement, answer every sighted enemy.
BASE_SNS = {"sn-enable-new-building-system": 1, "sn-percent-enemy-sighted-response": 100}
DEFAULT_GATHERERS = {"food": 45, "wood": 30, "gold": 15, "stone": 10}   # DE's AIBuilder
RESOURCES = ("food", "wood", "gold", "stone")
WAIT_GOAL, MAX_WAITS = 3, 4
ATTACKS_GOAL = 4                     # attacks launched so far (land and naval)
# report: true publishes the AI's state on AI signals, which scenario XS reads with xsGetAiSignal (scenario XS
# can't read an AI's goals: xsGetGoal is AI-only). Signal ids per player p (1-8): step 192+p, waits 200+p,
# attacks 208+p, villager split 216+4p .. 219+4p (food, wood, gold, stone). Goals 10-16 hold those ids.
STEP_SIGNAL, WAIT_SIGNAL, ATTACK_SIGNAL, SPLIT_SIGNAL = 192, 200, 208, 216
REPORT_GOALS = range(10, 17)
HOUSE_HEADROOM = 4
# grow: macro toward a population over time. The stage (goal GROW_GOAL, 0..stages) rises every minutes/stages on
# timer GROW_TIMER; each stage's rules raise the targets. Dropsite and town center placement is the engine's
# (the new building system puts dropsites by resources): unverified in game.
GROW_KEYS = {"to", "minutes", "stages", "villagers", "town_centers"}
GROW_GOAL, GROW_TIMER = 7, 5
GROW_DEFAULTS = {"to": 200, "minutes": 60, "stages": 8, "town_centers": 3}
GROW_VILLAGER_SHARE, GROW_SPARE, GROW_MAX_PRODUCTION, GROW_DROPSITES = 0.4, 10, 4, 3
DROPSITES = {"ror": ("STORAGE_PIT", "GRANARY"), "aoe2": ("LUMBER_CAMP", "MINING_CAMP", "MILL")}
# raids: launch timer RAID_TIMER+k, resend timer RESEND_TIMER+k; goals: launching RAID_READY+k, party out
# RAID_OUT+k, search state SEARCH_STATE..+3 (local index, local total, remote index, remote total), a point at
# POINT_GOAL/+1, party ids RAID_IDS + RAID_MAX_COUNT*k + i. keep's lifetime counters: LIFETIME_GOAL + entry index.
RAID_KEYS = {"units", "count", "min", "first", "every", "start", "near", "target", "resend", "fallback"}
# What a raid looks for, by RoR's class constants (default/defaultConstants.per): villager 904, building 903,
# infantry 906, archery 900, archery-cannon (Slingers) 944, cavalry 912, cavalry-archer 936, scout 947, siege 913,
# warship 922, fishing ship 921, transport 920. Not all-units-class (-1): RoR's scripts only search with it
# behind a filter, and a raid searching with it alone found nothing (the party stood idle, Egypt 5 playtest).
RAID_UNITS = (906, 900, 944, 912, 936, 947, 913, 922, 921, 920)
RAID_TARGETS = {"any": (904, *RAID_UNITS, 903), "villagers": (904,), "buildings": (903,)}
RAID_TIMER, RESEND_TIMER, RAID_READY, RAID_OUT = 10, 20, 20, 30
SEARCH_STATE, POINT_GOAL, LIFETIME_GOAL, RAID_IDS = 41, 45, 50, 100
RAID_MAX, RAID_MAX_COUNT, RAID_CHUNK = 5, 40, 20
# Constants RoR's scripts define themselves (default/defaultConstants.per): the engine has no names for them.
UP_CONSTS = {"my-search-local": 1, "my-search-remote": 2, "my-object-data-id": 0, "my-object-data-distance": 44,
             "my-position-object": 12, "my-search-order-asc": 1, "my-action-default": 0, "my-stance-aggressive": 0}
KEEP_EXTRA = {"lifetime", "when"}
# trade: one Market deal every `every` seconds on timer TRADE_TIMER, as RoR's AIBuilder market.per trades
# (buy-commodity / sell-commodity, gold for food, wood and stone). Sells only when gold is under TRADE_GOLD_LOW.
TRADE_TIMER, TRADE_GOLD_LOW = 6, 150
COMMODITIES = ("food", "wood", "stone")
SETUP_CHUNK = 15                     # setup actions per rule (+ disable-self): well inside the engine's limit


class SpecError(ValueError):
    pass


@dataclass
class Names:
    """Game names used in a script -> their defconst name and id."""
    game: str
    ids: dict[str, tuple[str, int]] = field(default_factory=dict)

    def const(self, name: str, kind: str) -> str:
        key = f"{kind}:{name}"
        if key not in self.ids:
            self.ids[key] = (f"my-{kind[0]}-{name.lower().replace('_', '-')}", resolve(name, kind, self.game))
        return self.ids[key][0]


def resolve(name: str, kind: str, game: str) -> int:
    """A unit/building ("object") or tech id by name, for the game."""
    from .. import games
    if isinstance(name, int):
        return name
    key = str(name).upper().replace(" ", "_").replace("-", "_")
    if game == "ror":
        table = games.ror_data()["techs" if kind == "tech" else "objects"]
        if key in table:
            return table[key]
    else:
        from ..datasets import resolve_dataset_value
        for ds in (("TechInfo",) if kind == "tech" else ("UnitInfo", "BuildingInfo")):
            try:
                return int(resolve_dataset_value(ds, key))
            except (KeyError, ValueError):
                continue
    raise SpecError(f"unknown {kind} '{name}' for {game} (find names with lookup)")


@cache
def _costs() -> dict:
    data = resources.files("aoe2ed").joinpath("data/costs.json").read_text(encoding="utf-8")
    return json.loads(data)


def cost(kind: str, oid: int, game: str) -> dict[str, int]:
    """What an object (kind "object") or tech costs in the game: {food: .., gold: ..}; {} if free or unknown."""
    return _costs().get(game, {}).get("techs" if kind == "tech" else "objects", {}).get(str(oid), {})


def auto_gatherers(items: list[tuple[str, int, int]], game: str) -> dict[str, int]:
    """A villager split from what (kind, id, count) items cost, blended half and half with AIBuilder's split."""
    need = dict.fromkeys(RESOURCES, 0.0)
    for kind, oid, count in items:
        for res, amount in cost(kind, oid, game).items():
            need[res] += amount * max(count, 1)
    total = sum(need.values())
    share = {r: (need[r] / total if total else DEFAULT_GATHERERS[r] / 100) for r in RESOURCES}
    raw = {r: 50 * share[r] + DEFAULT_GATHERERS[r] / 2 for r in RESOURCES}
    out = {r: int(raw[r]) for r in RESOURCES}
    for r in sorted(RESOURCES, key=lambda r: raw[r] - out[r], reverse=True)[:100 - sum(out.values())]:
        out[r] += 1
    return out


def _step(step: dict) -> tuple[str, str, int]:
    kinds = [k for k in STEP_KINDS if k in step]
    if len(kinds) != 1 or set(step) - {*STEP_KINDS, "count", *KEEP_EXTRA}:
        raise SpecError(f"a build_order step is one of {STEP_KINDS} with an optional count, got {step}")
    return kinds[0], step[kinds[0]], int(step.get("count", 1))


def _rule(facts: list[str], actions: list[str], comment: str = "") -> str:
    head = f"(defrule{f' ; {comment}' if comment else ''}\n"
    return head + "".join(f"\t{f}\n" for f in facts) + "=>\n" + "".join(f"\t{a}\n" for a in actions) + ")\n"


def _do(kind: str, const: str, count: int) -> tuple[list[str], list[str], str]:
    """(facts that it still needs doing, actions doing it, fact that it's done)."""
    if kind == "build":
        return ([f"(building-type-count-total {const} < {count})", f"(can-build {const})"],
                [f"(build {const})"], f"(building-type-count-total {const} >= {count})")
    if kind == "train":
        return ([f"(unit-type-count-total {const} < {count})", f"(can-train {const})"],
                [f"(train {const})"], f"(unit-type-count-total {const} >= {count})")
    return [f"(can-research {const})"], [f"(research {const})"], f"(research-completed {const})"


def _merge(base: dict, over: dict) -> dict:
    out = {**base, **over}
    if isinstance(base.get("attack"), dict) and isinstance(over.get("attack"), dict):
        out["attack"] = {**base["attack"], **over["attack"]}
    return out


def _scaled(spec: dict, f: dict, game: str = "ror") -> dict:
    """The spec made easier or harder by AUTO_LEVELS factors (soldiers only in the keep list)."""
    out = dict(spec)
    if spec.get("villagers"):
        out["villagers"] = max(1, round(int(spec["villagers"]) * f["villagers"]))
    if spec.get("attack"):
        a = dict(spec["attack"])
        a["first"] = round(int(a.get("first", 600)) * f["first"])
        a["every"] = max(MIN_ATTACK_EVERY, round(int(a.get("every", 240)) * f["every"]))
        a["min_group"] = max(1, round(int(a.get("min_group", 4)) * f["group"]))
        a["max_group"] = max(a["min_group"], round(int(a.get("max_group", 12)) * f["group"]))
        out["attack"] = a
    if spec.get("keep"):
        out["keep"] = [{**k, "count": max(1, round(int(k.get("count", 1)) * f["keep"]))}
                       if "train" in k and _soldier(k["train"], game) else k for k in spec["keep"]]
    if spec.get("grow"):
        g = dict(spec["grow"])
        g["minutes"] = max(1, round(float(g.get("minutes", GROW_DEFAULTS["minutes"])) * f.get("grow", 1)))
        out["grow"] = g
    return out


def _grow(spec: dict, game: str, names: Names) -> tuple[list[str], list[str]]:
    """(setup actions, rules) for `grow`: the stage timer and each stage's raised targets."""
    from .. import tables
    grow = spec["grow"]
    if not isinstance(grow, dict) or set(grow) - GROW_KEYS:
        raise SpecError(f"grow is {{to, minutes, stages, villagers, town_centers}}, got {grow!r}")
    g = {**GROW_DEFAULTS, **grow}
    to, stages = int(g["to"]), max(1, int(g["stages"]))
    every = max(1, round(float(g["minutes"]) * 60 / stages))
    v0 = int(spec.get("villagers") or 0)
    vn = max(v0, int(g.get("villagers") or round(to * GROW_VILLAGER_SHARE)))
    keep = [_step(k) for k in spec.get("keep") or []]
    soldiers = [(n, c) for kind, n, c in keep if kind == "train" and _soldier(n, game)]
    a0 = sum(c for _, c in soldiers)
    an = max(a0, to - vn - GROW_SPARE - int(spec.get("transports") or 0))
    kept = {n: c for kind, n, c in keep if kind == "build"}
    makers: dict[str, int] = {}                  # building -> soldiers it makes, at the start
    for n, c in soldiers:
        made_at = [b for b in (tables.info(n, game) or {}).get("made_at") or [] if b != "BUILDER"]
        if made_at:
            makers[made_at[0]] = makers.get(made_at[0], 0) + c
    setup = [f"(set-goal {GROW_GOAL} 0)", f"(enable-timer {GROW_TIMER} {every})"]
    rules = [_rule([f"(timer-triggered {GROW_TIMER})", f"(up-compare-goal {GROW_GOAL} < {stages})"],
                   [f"(up-modify-goal {GROW_GOAL} c:+ 1)", f"(disable-timer {GROW_TIMER})",
                    f"(enable-timer {GROW_TIMER} {every})"], f"grow: next stage every {every} s")]
    v, tc = names.const("VILLAGER", "object"), names.const("TOWN_CENTER", "object")
    for k in range(1, stages + 1):
        frac, stage = k / stages, [f"(goal {GROW_GOAL} {k})"]
        label = f"grow stage {k}/{stages}"
        rules.append(_rule([*stage, f"(civilian-population < {round(v0 + (vn - v0) * frac)})", f"(can-train {v})"],
                           [f"(train {v})"], f"{label}: villagers"))
        army = a0 + (an - a0) * frac
        for n, c in soldiers:
            const = names.const(n, "object")
            todo, actions, _ = _do("train", const, max(c, round(c * army / a0)))
            rules.append(_rule([*stage, *todo], actions, f"{label}: {n}"))
        for b in makers:
            base = kept.get(b, 1)
            const = names.const(b, "object")
            count = min(max(base, GROW_MAX_PRODUCTION), max(base, round(base * army / a0)))
            todo, actions, _ = _do("build", const, count)
            rules.append(_rule([*stage, *todo], actions, f"{label}: {b}"))
        tcs = 1 + round((int(g["town_centers"]) - 1) * frac)
        if tcs > 1:
            todo, actions, _ = _do("build", tc, tcs)
            rules.append(_rule([*stage, *todo], actions, f"{label}: town centers (expand)"))
        for d in DROPSITES.get(game, ()):
            const = names.const(d, "object")
            todo, actions, _ = _do("build", const, 1 + round((GROW_DROPSITES - 1) * frac))
            rules.append(_rule([*stage, *todo], actions, f"{label}: {d}"))
    return setup, rules


def _find_target(player, goal: int) -> list[str]:
    """Actions putting the player to attack in `goal`: `player` (attack.target), else the closest enemy. A fixed
    target keeps an AI on the player even when another enemy is closer (RoR-RI Egypt 7: the Minoans and Canaanites
    are enemies only so they don't trade with each other)."""
    if player is None:
        return [f"(up-find-player my-enemy my-find-closest {goal})"]
    if not 1 <= int(player) <= 8:
        raise SpecError(f"attack.target is a player number 1-8, got {player!r}")
    return [f"(set-goal {goal} {int(player)})"]


def _raids(spec: dict, names: Names) -> tuple[list[str], list[str]]:
    """(setup actions, rules) for `raids`. Per raid: a launch (timer or scenario event) searches the party, stores
    its ids if there are enough, and sends it; while any of it lives, its orders are renewed every `resend` s."""
    raids = spec.get("raids") or []
    if not isinstance(raids, list) or len(raids) > RAID_MAX:
        raise SpecError(f"raids is a list of up to {RAID_MAX} raids, got {raids!r}")
    setup, rules = [], []
    for k, r in enumerate(raids):
        if not isinstance(r, dict) or set(r) - RAID_KEYS or not r.get("units"):
            raise SpecError(f"a raid is {{units: [...], count, min, first, every, start, near, target, resend}}, "
                            f"got {r!r}")
        count = int(r.get("count", 5))
        least = int(r.get("min", count))
        if not 1 <= count <= RAID_MAX_COUNT or not 1 <= least <= count:
            raise SpecError(f"raid count is 1-{RAID_MAX_COUNT} and min 1-count, got {count} and {least}")
        target = r.get("target", "any")
        if target not in RAID_TARGETS:
            raise SpecError(f"raid target is one of {sorted(RAID_TARGETS)}, got {target!r}")
        timer, resend_timer = RAID_TIMER + k, RESEND_TIMER + k
        ready, out = RAID_READY + k, RAID_OUT + k
        ids = [RAID_IDS + RAID_MAX_COUNT * k + i for i in range(count)]
        every, resend = r.get("every"), max(1, int(r.get("resend", 10)))
        units = [names.const(u, "object") for u in r["units"]]
        label = f"raid {k + 1} ({'/'.join(r['units'])} x{count})"
        who = str(spec.get("name", "AI")).replace('"', "'")

        def say(text: str) -> list[str]:
            return [f'(chat-to-all "{who}: raid {k + 1} {text}")'] if spec.get("debug") else []
        fallback = r.get("fallback")
        if fallback is not None and (not isinstance(fallback, dict) or set(fallback) != {"x", "y"}):
            raise SpecError(f"raid fallback is {{x, y}}, got {fallback!r}")
        setup += [f"(set-goal {ready} 0)", f"(set-goal {out} 0)"]
        again = [f"(enable-timer {timer} {int(every)})"] if every else []
        start = r.get("start")
        if start is not None:
            if not isinstance(start, dict) or set(start) != {"trigger"} or not 0 <= int(start["trigger"]) <= 255:
                raise SpecError(f"raid start is {{trigger: N}} (0-255), got {start!r}")
            n = int(start["trigger"])
            rules.append(_rule([f"(event-detected trigger {n})"],
                               [f"(acknowledge-event trigger {n})", f"(set-goal {ready} 1)", *again],
                               f"{label}: the scenario sends AI Script Goal {n}"))
            if every:
                rules.append(_rule([f"(timer-triggered {timer})"],
                                   [f"(disable-timer {timer})", *again, f"(set-goal {ready} 1)"], f"{label}: again"))
        else:
            setup.append(f"(enable-timer {timer} {int(r.get('first', 600))})")
            rules.append(_rule([f"(timer-triggered {timer})"],
                               [f"(disable-timer {timer})", *again, f"(set-goal {ready} 1)"], f"{label}: time"))
        find = ["(up-full-reset-search)"]
        near = r.get("near")
        if near is not None:
            if not isinstance(near, dict) or set(near) - {"x", "y", "radius"} or not {"x", "y"} <= set(near):
                raise SpecError(f"raid near is {{x, y, radius}}, got {near!r}")
            find += [f"(set-goal {POINT_GOAL} {int(near['x'])})", f"(set-goal {POINT_GOAL + 1} {int(near['y'])})",
                     f"(up-set-target-point {POINT_GOAL})",
                     f"(up-filter-distance c: -1 c: {int(near.get('radius', 6))})"]
        find += [f"(up-find-local c: {u} c: {count})" for u in units] + [f"(up-get-search-state {SEARCH_STATE})"]
        rules.append(_rule([f"(goal {ready} 1)"], find, f"{label}: find the party"))
        enough = [f"(goal {ready} 1)", f"(up-compare-goal {SEARCH_STATE + 1} >= {least})"]
        for c in range(0, count, RAID_CHUNK):
            rules.append(_rule(enough, [f"(set-goal {g} -1)" for g in ids[c:c + RAID_CHUNK]], f"{label}: forget"))
        for i, g in enumerate(ids):
            rules.append(_rule([*enough, f"(up-compare-goal {SEARCH_STATE + 1} > {i})"],
                               [f"(up-set-target-object my-search-local c: {i})",
                                f"(up-get-object-data my-object-data-id {g})"], f"{label}: remember unit {i + 1}"))
        rules.append(_rule(enough, [f"(set-goal {out} 1)", f"(disable-timer {resend_timer})",
                                    f"(enable-timer {resend_timer} 1)", *say("sent")], f"{label}: send it"))
        if spec.get("debug"):
            rules.append(_rule([f"(goal {ready} 1)", f"(up-compare-goal {SEARCH_STATE + 1} < {least})"],
                               say("not enough units"), f"{label}: not enough units"))
        rules.append(_rule([f"(goal {ready} 1)"], [f"(set-goal {ready} 0)"], f"{label}: launched or not"))
        # The party, while any of it lives: orders renewed, at the closest enemy object of the target kind.
        live = [f"(timer-triggered {resend_timer})", f"(goal {out} 1)"]
        for c in range(0, count, RAID_CHUNK):
            first = [*_find_target((spec.get("attack") or {}).get("target"), 2),
                     "(up-modify-sn sn-focus-player-number g:= 2)", "(up-full-reset-search)"] if c == 0 else []
            rules.append(_rule(live, [*first, *(f"(up-add-object-by-id my-search-local g: {g})"
                                                for g in ids[c:c + RAID_CHUNK])], f"{label}: the party"))
        rules.append(_rule(live, [f"(up-get-search-state {SEARCH_STATE})"], f"{label}: how many are left"))
        rules.append(_rule([*live, f"(up-compare-goal {SEARCH_STATE + 1} < 1)"],
                           [f"(set-goal {out} 0)", f"(disable-timer {resend_timer})", *say("is gone")],
                           f"{label}: the party is gone"))
        rules.append(_rule(live, ["(up-set-target-object my-search-local c: 0)",
                                  f"(up-get-point my-position-object {POINT_GOAL})",
                                  f"(up-set-target-point {POINT_GOAL})",
                                  *(f"(up-find-remote c: {c} c: 40)" for c in RAID_TARGETS[target]),
                                  f"(up-get-search-state {SEARCH_STATE})"], f"{label}: look for a {target} target"))
        if target != "any":
            rules.append(_rule([*live, f"(up-compare-goal {SEARCH_STATE + 3} < 1)"],
                               [*(f"(up-find-remote c: {c} c: 40)" for c in (*RAID_UNITS, 903)),
                                f"(up-get-search-state {SEARCH_STATE})"], f"{label}: none known, so anything"))
        found = [*live, f"(up-compare-goal {SEARCH_STATE + 3} >= 1)"]
        rules.append(_rule(found, ["(up-clean-search my-search-remote my-object-data-distance my-search-order-asc)",
                                   "(up-set-target-object my-search-remote c: 0)",
                                   "(up-target-objects 1 my-action-default -1 my-stance-aggressive)", *say("attacks")],
                           f"{label}: at the closest"))
        if fallback:
            # Nothing of the enemy's known: to the fallback point, aggressive, attacking what it meets on the way.
            rules.append(_rule([*live, f"(up-compare-goal {SEARCH_STATE + 3} < 1)"],
                               [f"(set-goal {POINT_GOAL} {int(fallback['x'])})",
                                f"(set-goal {POINT_GOAL + 1} {int(fallback['y'])})",
                                f"(up-target-point {POINT_GOAL} my-action-default -1 my-stance-aggressive)",
                                *say("heads for the fallback point")], f"{label}: nothing known: the fallback point"))
        elif spec.get("debug"):
            rules.append(_rule([*live, f"(up-compare-goal {SEARCH_STATE + 3} < 1)"], say("finds no target"),
                               f"{label}: no target"))
        rules.append(_rule(live, [f"(disable-timer {resend_timer})", f"(enable-timer {resend_timer} {resend})"],
                           f"{label}: again in {resend} s"))
    return setup, rules


def _soldier(name: str, game: str) -> str | None:
    """'land' or 'naval' for a fighting unit, None for anything else."""
    from .. import tables
    info = tables.info(name, game)
    if not info or info.get("kind") != "unit" or info.get("class") in NOT_SOLDIERS:
        return None
    return "naval" if info.get("class") == NAVAL_CLASS else "land"


def civ_army(spec: dict, game: str) -> tuple[dict, list[str]]:
    """The spec with its keep list's soldiers shifted toward what the civ's bonuses favour (spec key `army`), and
    what changed. `share`% of the land soldiers (default 50) become the civ's best `units` (default 2) favoured
    units it can reach: by `max_age`, else the highest age the build order researches or `age` (the starting age).
    Their buildings join the keep list. The army keeps its size, and nothing in the build order changes."""
    from .. import civs
    army = spec.get("army")
    if not army:
        return spec, []
    if not isinstance(army, dict) or set(army) - ARMY_KEYS or "civ" not in army:
        raise SpecError(f"army is {{civ: NAME, share: 50, age, max_age, naval, exclude, units}}, got {army!r}")
    ages = AGE_TECHS.get(game, {})
    reached = [ages[s["research"]] for s in spec.get("build_order") or [] if s.get("research") in ages]
    max_age = int(army.get("max_age") or max([int(army.get("age", 1)), *reached]))
    try:
        picks = civs.favoured(army["civ"], game, max_age=max_age, exclude=set(army.get("exclude") or ()))
    except KeyError as e:
        raise SpecError(str(e)) from None
    picks = picks[:int(army.get("units", 2))]
    if not picks:
        return spec, []
    keep = [dict(k) for k in spec.get("keep") or []]
    land = [k for k in keep if "train" in k and _soldier(k["train"], game) == "land"]
    total = sum(int(k.get("count", 1)) for k in land) or (10 if spec.get("attack") else 0)
    if not total:
        return spec, []
    names = [p["unit"] for p in picks]
    want = max(len(picks), round(total * int(army.get("share", 50)) / 100))
    have = {k["train"]: int(k.get("count", 1)) for k in land if k["train"] in names}
    others = [k for k in land if k["train"] not in names]
    add = max(0, want - sum(have.values()))
    notes = []
    for i, p in enumerate(picks):                                   # spread what's added over the picks
        extra = add // len(picks) + (1 if i < add % len(picks) else 0)
        if not extra:
            continue
        entry = next((k for k in keep if k.get("train") == p["unit"]), None)
        if entry is None:
            entry = {"train": p["unit"], "count": 0}
            keep.append(entry)
        entry["count"] = int(entry.get("count", 1) if entry.get("count") is not None else 1) + extra
        own = [b for b in p["bonuses"] if "(" not in b] or p["bonuses"]
        notes.append(f"keep {p['unit']} x{entry['count']} ({', '.join(own[:3])})")
    rest = sum(int(k.get("count", 1)) for k in others)
    if rest and add:                                                # the others give up as many as were added
        cut = min(add, rest - len(others))
        for k in others:
            share = round(cut * int(k.get("count", 1)) / rest)
            k["count"] = max(1, int(k.get("count", 1)) - share)
    built = {s.get("build") for s in [*(spec.get("build_order") or []), *keep]}
    for p in picks:
        if p["made_at"] not in built:
            keep.append({"build": p["made_at"]})
            built.add(p["made_at"])
            notes.append(f"keep {p['made_at']} (makes {p['unit']})")
    return {**spec, "keep": keep}, notes


def level_specs(spec: dict, game: str = "ror") -> dict[str, dict]:
    """The spec for each difficulty level: `levels: auto` scales the spec (it is normal), a dict overrides keys per
    level ({easy: {villagers: 15, attack: {first: 900}}}); a level left out plays as normal."""
    levels = spec.get("levels")
    base = {k: v for k, v in spec.items() if k not in ("levels", "start")}
    if levels == "auto":
        return {"easy": _scaled(base, AUTO_LEVELS["easy"], game), "normal": base,
                "hard": _scaled(base, AUTO_LEVELS["hard"], game)}
    if not isinstance(levels, dict) or set(levels) - set(LEVELS):
        raise SpecError(f"levels is auto or a dict with keys from {LEVELS}, got {levels!r}")
    out = {}
    for lvl in LEVELS:
        over = levels.get(lvl) or {}
        if set(over) & {"levels", "start", "name"}:
            raise SpecError(f"levels.{lvl} can't set levels, start or name")
        out[lvl] = _merge(base, over)
    return out


def _gated(rule: str, facts: list[str]) -> str:
    if not facts:
        return rule
    head, rest = rule.split("\n", 1)
    return head + "\n" + "".join(f"\t{f}\n" for f in facts) + rest


def build_script(spec: dict, game: str = "ror") -> str:
    """The .per script for an AI spec."""
    unknown = set(spec) - TOP_KEYS
    if unknown:
        raise SpecError(f"unknown AI spec keys {sorted(unknown)}; allowed {sorted(TOP_KEYS)}")
    spec, _ = civ_army(spec, game)
    names = Names(game)
    pre, active = [], []
    start = spec.get("start")
    if start is not None:
        if not isinstance(start, dict) or set(start) != {"trigger"} or not 0 <= int(start["trigger"]) <= 255:
            raise SpecError(f"start is {{trigger: N}} (0-255, sent with the AI Script Goal effect), got {start!r}")
        n = int(start["trigger"])
        pre.append(_rule(["(true)"], [f"(set-goal {ACTIVE_GOAL} 0)", "(disable-self)"], "not started yet"))
        pre.append(_rule([f"(event-detected trigger {n})"],
                         [f"(acknowledge-event trigger {n})", f"(set-goal {ACTIVE_GOAL} 1)", "(disable-self)"],
                         f"start: the scenario sends AI Script Goal {n}"))
        active = [f"(goal {ACTIVE_GOAL} 1)"]
    if spec.get("levels"):
        pre.append(_rule(["(true)"], [f"(set-goal {LEVEL_GOAL} 3)", "(disable-self)"],
                         "difficulty: hard, hardest and extreme play hard"))
        for lvl, facts in LEVEL_FACTS.items():
            fact = facts[0] if len(facts) == 1 else "(or " + " ".join(facts) + ")"
            pre.append(_rule([fact], [f"(set-goal {LEVEL_GOAL} {lvl})", "(disable-self)"],
                             f"difficulty: {LEVELS[lvl - 1]}"))
        body = []
        for i, (lvl, s) in enumerate(level_specs(spec, game).items(), start=1):
            body += [_gated(r, [f"(goal {LEVEL_GOAL} {i})", *active]) for r in _body(s, game, names)]
    else:
        body = [_gated(r, active) for r in _body(spec, game, names)]
    head = [f"; {spec.get('name', 'AI')}: generated by aoe-agent-editor from an AI spec ({game})",
            f"(defconst my-step {STEP_GOAL})", f"(defconst my-enemy {ENEMY_STANCE})",
            f"(defconst my-find-closest {FIND_CLOSEST})"]
    head += [f"(defconst {c} {i})" for c, i in names.ids.values()]
    if any(s.get("raids") for s in (level_specs(spec, game).values() if spec.get("levels") else [spec])):
        head += [f"(defconst {c} {v})" for c, v in UP_CONSTS.items()]
    extra = spec.get("rules") or ""
    return "\n".join(head) + "\n\n" + "\n".join(pre + body) + (f"\n{extra.strip()}\n" if extra else "")


def _body(spec: dict, game: str, names: Names) -> list[str]:
    """The rules for one spec (one difficulty level)."""
    steps = [_step(s) for s in spec.get("build_order") or []]
    if any(set(s) & KEEP_EXTRA for s in spec.get("build_order") or []):
        raise SpecError(f"{sorted(KEEP_EXTRA)} are for keep entries, not build_order steps")
    timeout = int(spec.get("step_timeout", 180))
    keep = [_step(s) for s in spec.get("keep") or []]

    def item(kind: str, name: str, count: int) -> tuple[str, int, int]:
        k = "tech" if kind == "research" else "object"
        return k, resolve(name, k, game), count

    demand = [item(*s) for s in steps + keep]
    if spec.get("villagers"):
        demand.append(item("train", "VILLAGER", int(spec["villagers"])))
    spends = [r for r in RESOURCES if any(r in cost(k, oid, game) for k, oid, _ in demand)]
    if spec.get("gatherers", "auto") == "auto":
        gatherers = auto_gatherers(demand, game)
    else:
        gatherers = {**DEFAULT_GATHERERS, **spec["gatherers"]}
    if set(gatherers) != set(DEFAULT_GATHERERS) or sum(gatherers.values()) != 100:
        raise SpecError(f"gatherers needs food, wood, gold and stone summing to 100, got {gatherers}")
    attack = spec.get("attack")
    if attack is not None and set(attack) - ATTACK_KEYS:
        raise SpecError(f"unknown attack keys {sorted(set(attack) - ATTACK_KEYS)}")
    window = max(1, int(spec.get("window", 3)))
    keep_from = spec.get("keep_from", "start")
    if keep_from not in ("start", "end"):
        raise SpecError(f"keep_from is start or end, got {keep_from!r}")
    scout = spec.get("scout", "auto")
    if scout == "auto":
        scout = SCOUT_SHIPS.get(game) if (attack or {}).get("naval") or spec.get("transports") else None
    elif scout is True:
        scout = SCOUT_SHIPS.get(game)

    body = []
    init = [f"(set-strategic-number sn-{k}-gatherer-percentage {v})" for k, v in gatherers.items()]
    sns = {**BASE_SNS, **(SCOUT_SNS if scout else {}), **(spec.get("strategic_numbers") or {})}
    init += [f"(set-strategic-number {k} {int(v)})" for k, v in sns.items()]
    if attack:
        init += [f"(set-strategic-number sn-minimum-attack-group-size {int(attack.get('min_group', 4))})",
                 f"(set-strategic-number sn-maximum-attack-group-size {int(attack.get('max_group', 12))})",
                 f"(enable-timer {ATTACK_TIMER} {int(attack.get('first', 600))})"]
        if attack.get("naval"):
            init.append(f"(enable-timer {NAVAL_TIMER} {int(attack.get('first', 600))})")
    init += ["(set-goal my-step 1)", f"(set-goal {ATTACKS_GOAL} 0)", f"(set-goal {LAND_ATTACKS_GOAL} 0)"]
    grow_setup, grow_rules = _grow(spec, game, names) if spec.get("grow") else ([], [])
    init += grow_setup
    raid_setup, raid_rules = _raids(spec, names)
    init += raid_setup
    trade = spec.get("trade")
    if trade:
        if not isinstance(trade, dict) or set(trade) - {"buy", "sell", "every"} or any(
                set(trade.get(k) or {}) - set(COMMODITIES) for k in ("buy", "sell")):
            raise SpecError(f"trade is {{buy: {{stone: 200}}, sell: {{food: 600}}, every: 5}} (food, wood, stone), "
                            f"got {trade!r}")
        init.append(f"(enable-timer {TRADE_TIMER} {int(trade.get('every', 5))})")
    if steps and timeout:
        init.append(f"(enable-timer {STEP_TIMER} {timeout})")
    rebalance = spec.get("rebalance", True)
    if rebalance:
        init.append(f"(enable-timer {REBALANCE_TIMER} {REBALANCE_EVERY})")
    report = bool(spec.get("report"))
    if report:                                   # this player's signal ids, from my-player-number
        g = list(REPORT_GOALS)
        for goal, base in zip(g[:3], (STEP_SIGNAL, WAIT_SIGNAL, ATTACK_SIGNAL), strict=True):
            init += [f"(up-modify-goal {goal} c:= my-player-number)", f"(up-modify-goal {goal} c:+ {base})"]
        init += [f"(up-modify-goal {g[3]} c:= my-player-number)", f"(up-modify-goal {g[3]} c:* 4)",
                 f"(up-modify-goal {g[3]} c:+ {SPLIT_SIGNAL})"]
        for k in range(1, 4):
            init += [f"(up-modify-goal {g[3] + k} g:= {g[3]})", f"(up-modify-goal {g[3] + k} c:+ {k})"]
    for n, start in enumerate(range(0, len(init), SETUP_CHUNK), start=1):   # the engine limits rule length
        body.append(_rule(["(true)"], [*init[start:start + SETUP_CHUNK], "(disable-self)"], f"setup {n}"))
    if report:
        g = list(REPORT_GOALS)
        body.append(_rule(["(true)"], [
            f"(fe-set-signal g: {g[0]} g: my-step)", f"(fe-set-signal g: {g[1]} g: {WAIT_GOAL})",
            f"(fe-set-signal g: {g[2]} g: {ATTACKS_GOAL})",
            *(f"(fe-set-signal g: {g[3] + k} s: sn-{r}-gatherer-percentage)" for k, r in enumerate(RESOURCES))],
            "report state on AI signals (read by probes)"))

    debug = bool(spec.get("debug"))
    who = str(spec.get("name", "AI")).replace('"', "'")

    def say(text: str) -> list[str]:
        return [f'(chat-to-all "{who}: {text}")'] if debug else []

    restart = [f"(disable-timer {STEP_TIMER})", f"(enable-timer {STEP_TIMER} {timeout})"] if timeout else []
    advance = [*restart, f"(set-goal {WAIT_GOAL} 0)"]
    for i, (kind, name, count) in enumerate(steps, start=1):
        const = names.const(name, "tech" if kind == "research" else "object")
        todo, actions, done = _do(kind, const, count)
        label = f"step {i}: {kind} {name}" + (f" x{count}" if kind != "research" else "")
        # Worked on while it's among the next `window` steps; only the current step advances my-step.
        active = [f"(goal my-step {i})"] if window == 1 else \
            [f"(up-compare-goal my-step <= {i})", f"(up-compare-goal my-step > {i - window})"]
        body.append(_rule([*active, *todo], actions, label))
        body.append(_rule([f"(goal my-step {i})", done],
                          [f"(set-goal my-step {i + 1})", *advance, *say(f"{label} done")]))
        if timeout and kind == "train":
            # A train step counts living units, so losses in attacks can hold it back forever (Trojan War probe,
            # 2026-11-05: "5 cavalry" stalled the plan for 10 minutes). The units keep training while it's in the
            # window and the keep list tops the army up, so the plan moves on after one timeout.
            body.append(_rule([f"(goal my-step {i})", f"(timer-triggered {STEP_TIMER})"],
                              [f"(set-goal my-step {i + 1})", *advance, *say(f"{label}: moving on")],
                              f"step {i}: training doesn't block the plan: move on"))
        elif timeout:
            k, oid, _ = item(kind, name, count)
            afford = [f"({r}-amount >= {a})" for r, a in cost(k, oid, game).items()]
            body.append(_rule([f"(goal my-step {i})", f"(timer-triggered {STEP_TIMER})", *afford],
                              [f"(set-goal my-step {i + 1})", *advance, *say(f"{label} skipped (can't be made)")],
                              f"step {i}: affordable but still not made, so it can't be: skip it"))
    if steps and timeout:                                 # not affordable yet: wait, up to MAX_WAITS timeouts
        body.append(_rule([f"(timer-triggered {STEP_TIMER})", f"(up-compare-goal {WAIT_GOAL} < {MAX_WAITS})"],
                          [f"(up-modify-goal {WAIT_GOAL} c:+ 1)", *restart, *say("waiting for resources")],
                          "step waiting for resources"))
        body.append(_rule([f"(timer-triggered {STEP_TIMER})", f"(up-compare-goal {WAIT_GOAL} >= {MAX_WAITS})"],
                          ["(up-modify-goal my-step c:+ 1)", *advance, *say("gave up on a step")],
                          "step waited too long: skip it"))

    if spec.get("villagers"):
        v = names.const("VILLAGER", "object")
        body.append(_rule([f"(civilian-population < {int(spec['villagers'])})", f"(can-train {v})"],
                          [f"(train {v})"], "villagers"))
    if spec.get("transports"):
        tr = names.const(spec.get("transport_unit") or TRANSPORT_UNITS.get(game, "TRANSPORT_SHIP"), "object")
        body.append(_rule([f"(unit-type-count-total {tr} < {int(spec['transports'])})", f"(can-train {tr})"],
                          [f"(train {tr})"], f"transports x{int(spec['transports'])}"))
    pv = spec.get("provoked")
    if pv:
        if not isinstance(pv, dict) or set(pv) - {"players", "signal"} or not pv.get("players"):
            raise SpecError(f"provoked is {{players: [1], signal: 40}}, got {pv!r}")
        from .standard import provoked
        body.append(provoked(pv["players"], pv.get("signal")))
    if spec.get("houses", True):
        h = names.const("HOUSE", "object")
        body.append(_rule([f"(housing-headroom < {HOUSE_HEADROOM})", "(population-headroom > 0)", f"(can-build {h})"],
                          [f"(build {h})"], "houses"))
    if scout:
        sc = names.const(scout, "object")
        body.append(_rule([f"(unit-type-count-total {sc} < 1)", f"(can-train {sc})"], [f"(train {sc})"],
                          "scout ship: explores, so attacks across water find a target"))
    for i, (entry, (kind, name, count)) in enumerate(zip(spec.get("keep") or [], keep, strict=True)):
        const = names.const(name, "tech" if kind == "research" else "object")
        todo, actions, _ = _do(kind, const, count)
        when = [f"(goal my-step {len(steps) + 1})"] if keep_from == "end" else []
        cond = entry.get("when") or {}
        if set(cond) - {"soldiers", "units"}:
            raise SpecError(f"keep when is {{soldiers: N, units: {{NAME: N}}}}, got {cond!r}")
        if "soldiers" in cond:
            when.append(f"(defend-soldier-count >= {int(cond['soldiers'])})")
        for unit, n in (cond.get("units") or {}).items():
            when.append(f"(unit-type-count {names.const(unit, 'object')} >= {int(n)})")
        label = f"keep {name} x{count}"
        if entry.get("lifetime"):
            if kind == "research":
                raise SpecError(f"keep {name}: lifetime is for units and buildings")
            goal = LIFETIME_GOAL + i
            if goal >= RAID_IDS:
                raise SpecError("too many keep entries for lifetime counters")
            when.append(f"(up-compare-goal {goal} < {count})")
            actions = [*actions, f"(up-modify-goal {goal} c:+ 1)"]
            label += ", never replaced"
        body.append(_rule([*when, *todo], actions, label))
    body += raid_rules
    if trade:
        tick = [f"(timer-triggered {TRADE_TIMER})"]
        for res, target in (trade.get("buy") or {}).items():
            body.append(_rule([*tick, f"({res}-amount < {int(target)})", f"(can-buy-commodity {res})"],
                              [f"(buy-commodity {res})", *say(f"buys {res}")], f"trade: buy {res} up to {target}"))
        for res, floor in (trade.get("sell") or {}).items():
            body.append(_rule([*tick, f"(gold-amount < {TRADE_GOLD_LOW})", f"({res}-amount > {int(floor)})",
                               f"(can-sell-commodity {res})"],
                              [f"(sell-commodity {res})", *say(f"sells {res}")], f"trade: sell {res} over {floor}"))
        body.append(_rule(tick, [f"(disable-timer {TRADE_TIMER})",
                                 f"(enable-timer {TRADE_TIMER} {int(trade.get('every', 5))})"], "trade: next deal"))
    body += grow_rules
    if rebalance:
        # One 5% move a minute, to a resource the plan spends that's running out, from whichever other resource has
        # the most: the first rule that matches resets the timer, so the tiers go from the biggest pile down.
        for tier in RICH_TIERS:
            for poor in spends:
                for rich in RESOURCES:
                    if rich == poor:
                        continue
                    body.append(_rule(
                        [f"(timer-triggered {REBALANCE_TIMER})", f"({poor}-amount < {POOR})",
                         f"({rich}-amount > {tier})", f"(strategic-number sn-{rich}-gatherer-percentage >= {MIN_SHARE + REBALANCE_STEP})"],
                        [f"(up-modify-sn sn-{rich}-gatherer-percentage c:- {REBALANCE_STEP})",
                         f"(up-modify-sn sn-{poor}-gatherer-percentage c:+ {REBALANCE_STEP})",
                         f"(disable-timer {REBALANCE_TIMER})", f"(enable-timer {REBALANCE_TIMER} {REBALANCE_EVERY})",
                         *say(f"villagers: {rich} to {poor}")], f"rebalance: {poor} runs out, {rich} over {tier}"))
        body.append(_rule([f"(timer-triggered {REBALANCE_TIMER})"],
                          [f"(disable-timer {REBALANCE_TIMER})", f"(enable-timer {REBALANCE_TIMER} {REBALANCE_EVERY})"],
                          "rebalance: nothing to move"))
    if attack:
        every, percent = int(attack.get("every", 240)), int(attack.get("percent", 80))
        target = [*_find_target(attack.get("target"), TARGET_GOAL),
                  f"(up-modify-sn sn-target-player-number g:= {TARGET_GOAL})"]
        warm = attack.get("warm_up")
        if warm is not None and (not isinstance(warm, dict) or set(warm) - WARM_UP_KEYS or "attacks" not in warm):
            raise SpecError(f"attack.warm_up is {{attacks, min_group, max_group, every}}, got {warm!r}")
        # (label, gate, smallest group, largest, seconds to the next attack)
        waves = [("attack", [], int(attack.get("min_group", 4)), int(attack.get("max_group", 12)), every)]
        if warm:
            n = int(warm["attacks"])
            wmin = int(warm.get("min_group", 4))
            waves = [("warning attack", [f"(up-compare-goal {LAND_ATTACKS_GOAL} < {n})"], wmin,
                      int(warm.get("max_group", max(wmin, 8))), int(warm.get("every", every))),
                     ("attack", [f"(up-compare-goal {LAND_ATTACKS_GOAL} >= {n})"], *waves[0][2:])]
        for label, gate, least, most, wait in waves:
            sizes = [f"(set-strategic-number sn-minimum-attack-group-size {least})",
                     f"(set-strategic-number sn-maximum-attack-group-size {most})"] if warm else []
            body.append(_rule([f"(timer-triggered {ATTACK_TIMER})", *gate, "(players-building-count any-enemy >= 1)",
                               f"(defend-soldier-count >= {least})"],
                              [*target, *sizes, f"(set-strategic-number sn-percent-attack-soldiers {percent})",
                               "(set-strategic-number sn-percent-attack-boats 0)", "(attack-now)",
                               f"(up-modify-goal {ATTACKS_GOAL} c:+ 1)", f"(up-modify-goal {LAND_ATTACKS_GOAL} c:+ 1)",
                               f"(disable-timer {ATTACK_TIMER})", f"(enable-timer {ATTACK_TIMER} {wait})",
                               *say("attacking" if label == "attack" else label)], label))
        if attack.get("naval"):
            body.append(_rule([f"(timer-triggered {NAVAL_TIMER})", "(players-building-count any-enemy >= 1)",
                               "(warboat-count > 0)"],
                              [*target, f"(set-strategic-number sn-percent-attack-boats {percent})",
                               "(set-strategic-number sn-percent-attack-soldiers 0)", "(attack-now)", f"(up-modify-goal {ATTACKS_GOAL} c:+ 1)",
                               f"(disable-timer {NAVAL_TIMER})", f"(enable-timer {NAVAL_TIMER} {every})",
                               *say("naval attack")], "naval attack"))
    return body
