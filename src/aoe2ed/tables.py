"""Full unit, building and tech tables for Return of Rome and AoE2, pinned to the game build they came from.

data/tables/{ror,aoe2}.json are generated from the game's own data (scripts/gen_unit_tables.py): every object id
with its name, display name, kind, class, hit points, cost, where it's made, and for buildings that exist once per
age look, its age and the Age1 base it belongs to; every tech with its cost and where it's researched.

Each table records the game build (AoE2DE_s.exe's FileVersion) and the SHA-256 of the data file it was read from.
build_check() compares them with the installed game, so a patch or DLC that adds or changes units is noticed
rather than silently giving stale answers; rerun the generator then.
"""
from __future__ import annotations

import hashlib
import json
from functools import cache
from importlib.resources import files
from pathlib import Path

from . import games

GAMES = ("ror", "aoe2")
EXE = "AoE2DE_s.exe"


@cache
def load(game: str) -> dict:
    game = games.normalize(game)
    return json.loads((files("aoe2ed") / "data" / "tables" / f"{game}.json").read_text(encoding="utf-8"))


def _norm(s: str) -> str:
    return s.strip().upper().replace(" ", "_").replace("-", "_")


def object_id(name: str, game: str) -> int | None:
    """An object's id from its name in the table (any name: canonical, display or internal), or None."""
    return load(game)["names"].get(_norm(name))


def tech_id(name: str, game: str) -> int | None:
    return load(game)["tech_names"].get(_norm(name))


def _named(ids, t: dict) -> list[str]:
    return [t["objects"].get(str(i), {}).get("name", str(i)) for i in ids]


def info(value: int | str, game: str, kind: str = "object") -> dict | None:
    """Everything the table knows about an object (kind "object") or tech (kind "tech"), by id or name, with the
    buildings it's made in named; None if unknown."""
    t = load(game)
    entries, index = (t["techs"], t["tech_names"]) if kind == "tech" else (t["objects"], t["names"])
    oid = int(value) if str(value).lstrip("-").isdigit() else index.get(_norm(str(value)))
    if oid is None or str(oid) not in entries:
        return None
    e = {"id": oid, **entries[str(oid)]}
    if "made_at" in e:
        e["made_at"] = _named(e["made_at"], t)
    if "researched_at" in e:
        e["researched_at"] = _named(e["researched_at"], t)
    if "variant_of" in e:
        base = e["variant_of"]
        e["variant_of"] = {"id": base, "name": t["objects"][str(base)]["name"]}
    else:
        looks = [int(i) for i, o in t["objects"].items() if o.get("variant_of") == oid]
        if looks:
            e["age_looks"] = [{"id": i, "name": t["objects"][str(i)]["name"], "age": t["objects"][str(i)]["age"]}
                              for i in looks]
    return e


def search(query: str, game: str, kinds: list[str] | None = None, limit: int = 25) -> list[dict]:
    """Objects and techs whose name, display or internal name contains the query; exact matches first.
    kinds: unit, building, other, tech (default: all)."""
    t = load(game)
    q = _norm(query)
    kinds = kinds or ["unit", "building", "other", "tech"]
    hits = []
    for entries in (t["objects"], t["techs"]):
        for i, e in entries.items():
            kind = e.get("kind", "tech")
            if kind not in kinds:
                continue
            names = [e["name"], _norm(e["display"]), _norm(e["internal"])]
            if any(q in n for n in names if n):
                exact = q in names
                hits.append(((not exact, "variant_of" in e, len(e["name"]), int(i)),
                             {"kind": kind, "id": int(i), "name": e["name"], "display": e["display"],
                              **{k: e[k] for k in ("cost", "age") if k in e}}))
    return [h for _, h in sorted(hits, key=lambda h: h[0])[:limit]]


def build_check(game_dir: Path | None = None) -> dict:
    """Whether the tables match the installed game: {"build", "installed_build", "games": {game: problem or
    None}, "ok"}. A mismatch means the game was patched since the tables were made; rerun
    scripts/gen_unit_tables.py."""
    from .config import find_game_dir

    game_dir = game_dir or find_game_dir()
    out: dict = {"build": load("aoe2")["build"], "installed_build": None, "games": {}, "ok": False}
    if game_dir is None or not (game_dir / EXE).is_file():
        out["error"] = "AoE2 DE not found (set AOE2DE_PATH)"
        return out
    out["installed_build"] = exe_version(game_dir / EXE)
    for game in GAMES:
        t = load(game)
        problems = []
        if t["build"] != out["installed_build"]:
            problems.append(f"tables are from build {t['build']}, the game is {out['installed_build']}")
        for rel, digest in t["data"].items():
            path = game_dir / rel
            if not path.is_file():
                problems.append(f"{rel} is missing")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                problems.append(f"{rel} changed since the tables were made")
        out["games"][game] = "; ".join(problems) or None
    out["ok"] = not any(out["games"].values())
    return out


def exe_version(path: Path) -> str:
    """An executable's FileVersion, read from its version resource."""
    data = path.read_bytes()
    key = "FileVersion".encode("utf-16-le") + b"\0\0"
    i = data.find(key)
    if i < 0:
        return "unknown"
    i += len(key)
    i += (4 - i % 4) % 4                                  # the value is DWORD-aligned
    end = data.find(b"\0\0", i)
    while (end - i) % 2:
        end = data.find(b"\0\0", end + 1)
    return data[i:end].decode("utf-16-le")
