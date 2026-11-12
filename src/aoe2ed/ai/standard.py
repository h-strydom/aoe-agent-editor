"""The game's standard skirmish AI, embedded in a scenario, playing a chosen difficulty.

The standard AI is a main script that loads the game's `ai/default/*.per` files (what the scenario editor embeds
when you pick the standard AI; RoR names it "Trajan"). Its difficulty settings (population and villager caps,
when it may attack, what share of its army attacks, kiting...) are six `#load-if-defined DIFFICULTY-<LEVEL>`
blocks in `default/customConstants.per`, picked by the game's difficulty. To play another difficulty, the script
inlines that file with each block's settings swapped for the level it should play: under `plays: {moderate:
hard}` a Moderate game runs the Hard settings. The other files' few difficulty checks (boar hunting, extreme
buildings, some researches) still follow the game's difficulty.

The `resign` file is left out unless asked for: campaign enemies fight to the end (the standard AI resigns when it
judges the game lost).

Read from the player's own install at build time (nothing of the game is bundled): `config.find_game_dir()`.
"""
from __future__ import annotations

import re
from pathlib import Path

from .. import config

LEVELS = ("easiest", "easy", "moderate", "hard", "hardest", "extreme")
# The scenario editor's own standard AI main script, file by file (RoR, 2026-11-12): customConstants is inlined.
FILES = ("defaultConstants", "alternateConstants", "customConstants", "init", "threats", "escrow", "dawn",
         "gatherers", "tsa", "general", "orb", "@boarhunting", "researches", "interaction", "buildings", "units",
         "trade", "resign")
BOARHUNTING = """#load-if-not-defined DIFFICULTY-EASIEST
#load-if-not-defined DIFFICULTY-EASY
#load-if-not-defined DIFFICULTY-MODERATE
#load-if-not-defined INFINITE-RESOURCES-START
(load "default\\boarhunting")
#end-if
#end-if
#end-if
#end-if"""
AI_DIRS = {"ror": "modes/Pompeii/resources/_common/ai", "aoe2": "resources/_common/ai"}
_BLOCK = re.compile(r"#load-if-defined DIFFICULTY-([A-Z]+)\s*\n(.*?)#end-if[^\n]*\n?", re.S)


def ai_dir(game: str = "ror", root: Path | None = None) -> Path:
    root = root or config.find_game_dir()
    if root is None:
        raise FileNotFoundError("the game isn't installed where Steam keeps it: can't read its standard AI")
    return Path(root) / AI_DIRS[game]


def shifted_constants(text: str, plays: dict[str, str]) -> str:
    """customConstants.per with each difficulty block holding the settings of the level its difficulty plays."""
    blocks = {m.group(1).lower(): m.group(2) for m in _BLOCK.finditer(text)}
    if set(blocks) != set(LEVELS):
        raise ValueError(f"customConstants.per has difficulty blocks for {sorted(blocks)}, expected {LEVELS}")
    bad = {k: v for k, v in plays.items() if k not in LEVELS or v not in LEVELS}
    if bad:
        raise ValueError(f"plays maps difficulties to difficulties ({', '.join(LEVELS)}), got {bad}")
    first = _BLOCK.search(text)
    rest = _BLOCK.sub("", text)
    swapped = "".join(f"#load-if-defined DIFFICULTY-{lvl.upper()}\n{blocks[plays.get(lvl, lvl)]}#end-if\n"
                      for lvl in LEVELS)
    return rest[:first.start()] + swapped + rest[first.start():]


def standard_script(plays: dict[str, str] | None = None, *, resign: bool = False, game: str = "ror",
                    root: Path | None = None) -> str:
    """The standard AI's main script; `plays` maps a game difficulty to the difficulty it plays (default: its
    own). Without `plays` it loads every file, as the scenario editor's standard AI does."""
    folder = ai_dir(game, root) / "default"
    lines = []
    for f in FILES:
        if f == "resign" and not resign:
            continue
        if f == "@boarhunting":
            lines.append(BOARHUNTING)
        elif f == "customConstants" and plays:
            text = (folder / "customConstants.per").read_text(encoding="utf-8", errors="replace")
            lines.append(shifted_constants(text, plays))
        else:
            lines.append(f'(load "default\\{f}")')
    return "\n".join(lines) + "\n"
