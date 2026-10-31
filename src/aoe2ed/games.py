"""Which game a scenario is for: AoE2 DE or Return of Rome (RoR).

Both use the same .aoe2scenario format and version (1.59); a header field ("variant") says which
game it belongs to. RoR has its own game data, so object, tech and civ names resolve differently:
id 74 is Militia in AoE2 but Short Swordsman in RoR. The current game is kept in a context variable
that SESSIONS sets whenever a tool touches a scenario, and the compiler sets per mission, so every
name lookup underneath uses the right table.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
from functools import cache
from importlib.resources import files
from typing import Any

from AoE2ScenarioParser.datasets.scenario_variant import ScenarioVariant

GAMES = ("aoe2", "ror")
_current: contextvars.ContextVar[str] = contextvars.ContextVar("aoe2ed_game", default="aoe2")


def normalize(game: str | None) -> str:
    g = (game or "aoe2").strip().lower().replace(" ", "_")
    g = {"aoe2de": "aoe2", "return_of_rome": "ror", "rome": "ror", "pompeii": "ror"}.get(g, g)
    if g not in GAMES:
        raise ValueError(f"Unknown game '{game}'. Use 'aoe2' or 'ror' (Return of Rome).")
    return g


def current() -> str:
    return _current.get()


def set_current(game: str) -> None:
    _current.set(normalize(game))


@contextlib.contextmanager
def use(game: str):
    token = _current.set(normalize(game))
    try:
        yield
    finally:
        _current.reset(token)


def scenario_game(scenario: Any) -> str:
    return "ror" if scenario.variant == ScenarioVariant.ROR else "aoe2"


def set_scenario_game(scenario: Any, game: str) -> None:
    """Mark a scenario as AoE2 or RoR (the header field the game reads to list it)."""
    variant = ScenarioVariant.ROR if normalize(game) == "ror" else ScenarioVariant.AOE2
    scenario.sections["FileHeader"].unknown_value_2 = variant.value
    scenario.variant = variant


def file_game(data: bytes) -> str:
    """Game of a .aoe2scenario from its bytes (same detection the parser uses)."""
    i = data.find(b"\xe8\x03\x00\x00")
    if i >= 0 and int.from_bytes(data[i + 4:i + 8], "little") == ScenarioVariant.ROR.value:
        return "ror"
    return "aoe2"


@cache
def ror_data() -> dict:
    """RoR name tables generated from the game's data by scripts/gen_ror_dataset.py."""
    return json.loads((files("aoe2ed") / "data" / "ror.json").read_text(encoding="utf-8"))
