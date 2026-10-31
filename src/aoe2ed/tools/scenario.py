"""Scenario lifecycle: open, create, save, inspect."""
from __future__ import annotations

from pathlib import Path

from ..config import paths
from ..session import SESSIONS
from . import tool


@tool
def paths_info() -> dict:
    """Where the game and the user's profile folders are (scenario/campaign/xs dirs, logs)."""
    return paths().as_dict()


@tool
def scenario_files(kind: str = "scenario", pattern: str = "*", game: str = "aoe2") -> list[dict]:
    """List files in the profile's user folder. kind: scenario | campaign | xs | ai.
    game: aoe2 | ror (Return of Rome keeps its own folders)."""
    from .. import games
    d = paths().user_dir(kind, games.normalize(game))
    return [{"name": p.name, "path": str(p), "bytes": p.stat().st_size}
            for p in sorted(d.glob(pattern)) if p.is_file()]


@tool
def scenario_new(map_size: int = 120, game: str = "aoe2") -> dict:
    """Create a blank scenario at the parser's latest version. Returns a handle like 's1'.
    game: aoe2 | ror. A Return of Rome scenario uses RoR's units, techs and civs (see lookup)."""
    from .. import games
    return SESSIONS.new(map_size, games.normalize(game)).info()


@tool
def scenario_open(path: str) -> dict:
    """Open a .aoe2scenario file. A bare name is looked up in the profile's scenario folders
    (AoE2, then Return of Rome)."""
    p = Path(path)
    tried = [p.resolve()]
    if not p.is_absolute() and not p.exists():
        for game in ("aoe2", "ror"):
            cand = paths().user_dir("scenario", game) / p
            cand = cand if cand.suffix else cand.with_suffix(".aoe2scenario")
            tried.append(cand)
            if cand.exists():
                break
        p = tried[-1]
    if not p.exists():
        raise FileNotFoundError(f"No scenario at {' or '.join(str(t) for t in tried)}")
    return SESSIONS.open(p).info()


@tool
def scenario_save(handle: str, path: str | None = None, overwrite: bool = False, install: bool = False) -> dict:
    """Save a scenario. With install=True and a bare file name, saves into the profile's scenario
    folder (AoE2 or Return of Rome, by the scenario's game) so the game sees it. Overwriting keeps a
    timestamped .bak copy."""
    if install:
        if not path:
            raise ValueError("install=True needs a file name")
        from .. import games
        game = games.scenario_game(SESSIONS.get(handle).scenario)
        path = str(paths().user_dir("scenario", game) / Path(path).name)
    return SESSIONS.save(handle, path, overwrite=overwrite)


@tool
def scenario_close(handle: str) -> dict:
    """Forget an open scenario (unsaved changes are lost)."""
    SESSIONS.close(handle)
    return {"closed": handle}


@tool
def scenario_list_open() -> list[dict]:
    """Scenarios currently open in this server."""
    return SESSIONS.list()


@tool
def scenario_summary(handle: str) -> dict:
    """Overview: map, players, unit counts, variables, trigger names, messages, XS presence."""
    s = SESSIONS.get(handle).scenario
    pm, um, tm, mm = s.player_manager, s.unit_manager, s.trigger_manager, s.message_manager
    players = []
    for p in pm.players:
        if p.player_id == 0 or p.active:
            players.append({"id": p.player_id, "active": bool(p.active), "human": bool(p.human),
                            "civ": getattr(p.civilization, "name", p.civilization),
                            "units": len(um.units[p.player_id]) if p.player_id < len(um.units) else 0})
    return {
        **SESSIONS.get(handle).info(),
        "players": players,
        "variables": [{"id": v.variable_id, "name": v.name} for v in tm.variables],
        "trigger_list": [{"index": t.trigger_id, "name": t.name, "enabled": bool(t.enabled)} for t in tm.triggers],
        "messages": {k: getattr(mm, k) for k in ("instructions", "hints", "victory", "loss", "history", "scouts")},
        "xs_script_name": s.xs_manager.script_name,
    }
