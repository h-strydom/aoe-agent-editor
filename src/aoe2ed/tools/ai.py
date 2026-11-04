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
def ai_lookup(query: str, kind: str = "all", limit: int = 40, describe: bool = False) -> dict:
    """Search the AI script language: what the game's own scripts use plus the AI Scripting Encyclopedia
    (airef.github.io). kind = facts | actions | strategic_numbers | symbols | all.
    Commands come with their signature ("(up-compare-goal GoalId compareOp Value)"), the version that added
    them (AoC, UP, DE: all work in DE and RoR), whether the game's own scripts use them, and an airef link;
    strategic numbers with their id, default, valid range and whether DE uses them.
    An exact name with describe=True adds airef's description (downloaded into your cache on first use).
    Example: ai_lookup("attack", "strategic_numbers"), ai_lookup("up-find-player", describe=True)."""
    v = per.vocab()
    kinds = ["facts", "actions", "strategic_numbers", "symbols"] if kind == "all" else [kind]
    q = query.lower()
    out: dict = {}
    for k in kinds:
        if k in ("facts", "actions"):
            want = k[:-1]
            names = {x for x in v[k] if q in x} | {n for n, c in v["ref_commands"].items()
                                                   if q in n and want in c["kind"]}
            out[k] = [_command(n, v) for n in sorted(names, key=lambda n: (n != q, len(n), n))[:limit]]
        elif k == "strategic_numbers":
            names = {x for x in v[k] if q in x} | {n for n in v["ref_sns"] if q in n}
            out[k] = [{"name": n, "used_by_game": n in v[k], **v["ref_sns"].get(n, {})}
                      for n in sorted(names, key=lambda n: (n != q, len(n), n))[:limit]]
        else:
            out[k] = sorted(x for x in v[k] | v["ref_symbols"] if q in x)[:limit]
    if describe:
        from ..ai.reference import describe as airef_describe
        try:
            out["description"] = airef_describe(query)
        except OSError as e:
            out["description"] = {"error": f"couldn't fetch airef's descriptions: {e}"}
    return out


def _command(name: str, v: dict) -> dict:
    ref = v["ref_commands"].get(name)
    entry = {"name": name, "used_by_game": name in v["facts"] or name in v["actions"]}
    if ref:
        entry.update(signature=per._signature(name, ref), version=ref["version"], link=ref["link"],
                     parameters=ref["parameters"])
    if name in v["arity"]:
        entry["argument_counts_in_game_scripts"] = sorted(v["arity"][name])
    return entry
