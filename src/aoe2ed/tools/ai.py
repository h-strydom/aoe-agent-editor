"""AI scripts for computer players: write them from a spec, check them, embed them in a scenario."""
from __future__ import annotations

from pathlib import Path

from .. import games
from ..ai import per
from ..ai.spec import build_script
from ..session import SESSIONS
from . import tool


def _script(source: str | dict, game: str) -> str:
    """An AI script from a spec dict, a .per path, or script text."""
    if isinstance(source, dict):
        with games.use(game):
            return build_script(source, game)
    p = Path(source)
    if len(source) < 260 and p.suffix == ".per" and p.is_file():
        return p.read_text(encoding="utf-8")
    return source


@tool
def ai_build(spec: dict, game: str = "ror", out: str | None = None) -> dict:
    """Write an AI script (.per) from an AI spec: build order, villagers, houses, gatherer split, attacks,
    strategic numbers (guide("ai-spec") for every key). Returns the script and its check; out= saves it."""
    script = _script(spec, games.normalize(game))
    if out:
        Path(out).write_text(script, encoding="utf-8")
    problems = [d.as_dict() for d in per.check(script)]
    return {"script": script, "rules": script.count("(defrule"), "problems": problems, "saved": out}


@tool
def ai_check(script: str) -> dict:
    """Check an AI script (text or .per path): bracket and rule structure are errors; facts, actions,
    strategic numbers and names that the game's own scripts never use are warnings."""
    text = _script(script, "ror")
    problems = [d.as_dict() for d in per.check(text)]
    return {"ok": not any(p["severity"] == "error" for p in problems), "rules": text.count("(defrule"),
            "problems": problems}


@tool
def ai_set(handle: str, player: int, ai: str | dict, name: str | None = None) -> dict:
    """Give a scenario player an AI embedded in the scenario: an AI spec (dict), a .per path, script text,
    or 'none' (does nothing on its own), 'immobile' (units hold position), 'default' (the game's standard AI,
    which resigns when losing). Specs and scripts are checked first; errors refuse the change."""
    from .world import set_ai
    o = SESSIONS.get(handle)
    p = o.scenario.player_manager.players[player]
    if ai in ("none", "immobile", "default"):
        set_ai(p, ai)
        return {"player": player, "ai": ai}
    script = _script(ai, games.scenario_game(o.scenario))
    problems = [d.as_dict() for d in per.check(script)]
    errors = [x for x in problems if x["severity"] == "error"]
    if errors:
        raise ValueError(f"AI script has errors: {errors[:5]}")
    label = name or (ai.get("name") if isinstance(ai, dict) else None) or f"Player {player} AI"
    p.set_custom_ai(label, ai_script=script)
    return {"player": player, "ai": label, "rules": script.count("(defrule"), "warnings": problems}


@tool
def ai_lookup(query: str, kind: str = "all", limit: int = 40) -> dict:
    """Search the AI script vocabulary (what the game's own scripts use): kind = facts | actions |
    strategic_numbers | symbols | all. Example: ai_lookup("attack", "strategic_numbers")."""
    v = per.vocab()
    kinds = ["facts", "actions", "strategic_numbers", "symbols"] if kind == "all" else [kind]
    q = query.lower()
    return {k: sorted(x for x in v[k] if q in x)[:limit] for k in kinds}
