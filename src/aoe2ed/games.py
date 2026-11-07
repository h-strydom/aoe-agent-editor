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


# The data sets (DLC packs) a file depends on, by game: the scenario header's list after the variant, and a
# campaign's dependency list. The parser's own values; the RoR editor saves [11] (a scenario made there, 2026-11-08).
# Setting the variant field first made the parser skip its own update, so converted RoR scenarios kept the blank
# template's AoE2 list (every pack but 11), and saves from a campaign of them wouldn't load ("can't determine data
# set"); verified fixed in game (RoR-RI, Ascent of Egypt 3, 2026-11-08).
DATA_SETS = {"aoe2": [2, 3, 4, 5, 6, 7, 8, 9, 10, 12], "ror": [11]}
# The DataHeader's 9 unnamed bytes: the parser's default starts with 1, the RoR editor saves all zeros. With the 1,
# a RoR scenario ended in victory the moment the last enemy was defeated, whatever the Custom victory settings;
# zeroing that byte alone stopped it (RoR-RI probes against the user's own scenario, 2026-11-08).
ROR_DATA_HEADER_UNKNOWN = b"\x00" * 9


def set_scenario_game(scenario: Any, game: str) -> None:
    """Mark a scenario as AoE2 or RoR: the header's variant (the game lists the file by it), data sets and, for
    RoR, the data header bytes the RoR editor writes."""
    game = normalize(game)
    variant = ScenarioVariant.ROR if game == "ror" else ScenarioVariant.AOE2
    header = scenario.sections["FileHeader"]
    header.unknown_value_2 = variant.value
    header.unknown_numbers = list(DATA_SETS[game])
    header.amount_of_unknown_numbers = len(DATA_SETS[game])
    if game == "ror":
        scenario.sections["DataHeader"].unknown = ROR_DATA_HEADER_UNKNOWN
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
