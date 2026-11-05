"""Civilization bonuses, from the game's own data (data/civ_bonuses.json, scripts/gen_civ_bonuses.py).

Return of Rome only so far: each civ's favoured military units (what its bonuses improve: hit points, speed,
armour, attack, range, fire rate, cost, training time), where they're made and the age they're available, and
the units its tech tree takes away.
"""
from __future__ import annotations

import json
from functools import cache
from importlib import resources


ALIASES = {"CARTHAGINIAN": "CARTHAGE", "PALMYRAN": "PALMYRA"}    # player_set's civ names -> the data's


@cache
def _data() -> dict:
    return json.loads(resources.files("aoe2ed").joinpath("data/civ_bonuses.json").read_text(encoding="utf-8"))


def civ(name: str, game: str = "ror") -> dict:
    """{"favoured": [{unit, made_at, age, naval, bonuses}], "unavailable": [...]}, favoured best first."""
    if game != "ror":
        raise KeyError(f"civ bonuses are only tabled for Return of Rome so far, not {game}")
    civs = _data()["civs"]
    key = str(name).upper().replace("_", " ")
    key = ALIASES.get(key, key)
    if key not in civs:
        raise KeyError(f"unknown RoR civ '{name}'; known: {sorted(civs)}")
    return civs[key]


def favoured(name: str, game: str = "ror", *, max_age: int = 4, naval: bool = False,
             exclude: set[str] | frozenset[str] = frozenset()) -> list[dict]:
    """The civ's favoured units it can reach by `max_age`, land units only unless `naval`, leaving out units or
    buildings named in `exclude`."""
    out = []
    for f in civ(name, game)["favoured"]:
        if f["age"] > max_age or (f["naval"] and not naval) or f["unit"] in exclude or f["made_at"] in exclude:
            continue
        out.append(f)
    return out
