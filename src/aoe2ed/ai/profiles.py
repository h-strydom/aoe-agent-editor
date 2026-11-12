"""AI toolbox profiles: a computer player described in a few words, expanded into an AI spec (docs/ai-toolbox.md).

    expand({"kind": "town", "pop": "default", "army": {"core": ["AXEMAN"], "support": ["BOWMAN"]},
            "upgrades": "economy", "water": "light", "defense": "home", "offense": "light"})

gives a spec with explicit levels (Standard plays easy, Moderate normal, Hard hard) that build_script compiles.
Kinds built so far: `town` (villagers and a Town Center: grows, farms, fights) and `army` (soldiers without an
economy: defends its post and attacks in waves with what it has). Every other key overrides one skill; `spec`
merges raw AI spec keys last (build_order, ages, start, ...).

Population targets (the user, 2026-11-12): Standard about 50, Moderate about 100, Hard 150 or more. The army grows
toward its share of the target over the game.
"""
from __future__ import annotations

KINDS = ("town", "army")
PROFILE_KEYS = {"kind", "name", "pop", "army", "upgrades", "water", "defense", "offense", "retreat", "goal",
                "farms", "grow_minutes", "ages", "spec"}
LEVELS = ("easy", "normal", "hard")
POP = {"easy": 50, "normal": 100, "hard": 150}
GROW_MINUTES = {"easy": 90, "normal": 60, "hard": 40}
ARMY_SHARE = 40                       # % of the population that's army at full size
START_ARMY = 6
OFFENSE = {"none": None,
           "light": {"first": 900, "every": 360, "min_group": 4},
           "normal": {"first": 600, "every": 240, "min_group": 6},
           "heavy": {"first": 420, "every": 180, "min_group": 8}}
# Standard waits longer and attacks less often, Hard sooner and more often (on top of its bigger army).
OFFENSE_LEVEL = {"easy": {"first": 1.4, "every": 1.4}, "normal": {"first": 1, "every": 1},
                 "hard": {"first": 0.7, "every": 0.7}}
DEFENSE = {"none": None, "home": {"home": 30, "radius": 14}, "heavy": {"home": 50, "radius": 18}}
RETREAT = {"none": None, "outnumbered": {"lost": 50}}
WATER = {"none": None, "light": {"fishing": 3, "warships": 1}, "normal": {"fishing": 6, "warships": 4},
         "heavy": {"fishing": 10, "warships": 12}}


class ProfileError(ValueError):
    pass


def _pick(table: dict, value, key: str):
    if isinstance(value, dict) or value is None:
        return value
    if value not in table:
        raise ProfileError(f"{key} is one of {sorted(table)} or a dict, got {value!r}")
    return table[value]


def _per_level(value, default: dict) -> dict:
    """A number for every level from `default` (a dict per level), one number (Moderate's, scaled), or a dict."""
    if value in (None, "default"):
        return dict(default)
    if isinstance(value, dict):
        return {lvl: int(value.get(lvl, default[lvl])) for lvl in LEVELS}
    n = int(value)
    return {lvl: round(n * default[lvl] / default["normal"]) for lvl in LEVELS}


def expand(profile: dict) -> dict:
    """The AI spec for a profile."""
    unknown = set(profile) - PROFILE_KEYS
    if unknown:
        raise ProfileError(f"unknown profile keys {sorted(unknown)}; allowed {sorted(PROFILE_KEYS)}")
    kind = profile.get("kind", "town")
    if kind not in KINDS:
        raise ProfileError(f"kind is one of {KINDS}, got {kind!r}")
    army = dict(profile.get("army") or {})
    units = {r: army[r] for r in ("core", "support", "raiders") if army.get(r)}
    share = int(army.get("share", ARMY_SHARE))
    pop = _per_level(profile.get("pop"), POP)
    minutes = _per_level(profile.get("grow_minutes"), GROW_MINUTES)
    offense = _pick(OFFENSE, profile.get("offense", "light"), "offense")
    defense = _pick(DEFENSE, profile.get("defense", "home"), "defense")
    retreat = _pick(RETREAT, profile.get("retreat", "outnumbered"), "retreat")
    water = _pick(WATER, profile.get("water", "none"), "water")

    def level(lvl: str) -> dict:
        s: dict = {}
        if kind == "town":
            soldiers = round(pop[lvl] * share / 100)
            s["villagers"] = 3
            s["grow"] = {"to": pop[lvl], "minutes": minutes[lvl], "villagers": pop[lvl] - soldiers}
            if units:
                s["composition"] = {"units": units, "size": soldiers, "start": min(START_ARMY, soldiers)}
            s["farms"] = profile.get("farms", "auto")
            s["keep"] = [{"build": "MARKET"}] if s["farms"] else []
            s["keep"] += [{"research": a} for a in profile.get("ages") or []]
        else:                                     # army: what it has, kept up where it can train
            size = int(army.get("size", 12))
            if units:
                s["composition"] = {"units": units, "size": size, "start": size}
            s["houses"] = False
            s["rebalance"] = False
        if offense:
            f = OFFENSE_LEVEL[lvl]
            s["attack"] = {"first": round(offense["first"] * f["first"]),
                           "every": round(offense["every"] * f["every"]),
                           "min_group": offense["min_group"], "naval": bool(water and water.get("warships", 0) > 1)}
        if defense:
            s["defense"] = dict(defense)
        if retreat:
            s["retreat"] = dict(retreat)
        if water:
            s["water"] = dict(water)
        if profile.get("upgrades"):
            s["upgrades"] = profile["upgrades"]
        if profile.get("goal"):
            s["goal"] = profile["goal"]
        return s

    normal = level("normal")
    spec = {"name": profile.get("name", f"{kind} (toolbox)"), **normal,
            "levels": {lvl: level(lvl) for lvl in ("easy", "hard")}}
    for k, v in (profile.get("spec") or {}).items():
        spec[k] = v
    return spec
