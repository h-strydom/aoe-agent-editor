"""Build the full unit, building and tech tables for Return of Rome and AoE2 from the game's own data.

Writes src/aoe2ed/data/tables/{ror,aoe2}.json, pinned to the game build they came from (the executable's version
and each data file's SHA-256), so a patch or DLC that adds units shows up as a difference (tests/test_tables.py).

Per object id: its name key (as used in specs and tools), display name, internal name, kind (unit, building,
other), class, hit points, where it's made, cost, and for buildings that exist once per age look, the Age1 base
it belongs to ("Academy Age3" 18 -> 103) and its age. Per tech: name, display name, cost, where it's researched.

  uv run --with genieutils-py python scripts/gen_unit_tables.py [AOE2DE_PATH]
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from genieutils.datfile import DatFile

from aoe2ed import datasets, games
from aoe2ed.config import find_game_dir
from aoe2ed.tables import EXE, exe_version

OUT = Path(__file__).resolve().parents[1] / "src" / "aoe2ed" / "data" / "tables"
GAMES = {
    "ror": {"dat": "modes/Pompeii/resources/_common/dat/empires2_x2_p1.dat",
            "strings": ["modes/Pompeii/resources/en/strings/key-value/key-value-pompeii-strings-utf8.txt",
                        "resources/en/strings/key-value/key-value-strings-utf8.txt"]},
    "aoe2": {"dat": "resources/_common/dat/empires2_x2_p1.dat",
             "strings": ["resources/en/strings/key-value/key-value-strings-utf8.txt",
                         "resources/en/strings/key-value/key-value-paphos-strings-utf8.txt"]},
}
KINDS = {70: "unit", 80: "building"}
RESOURCES = {0: "food", 1: "wood", 2: "stone", 3: "gold"}


def strings(paths: list[Path]) -> dict[int, str]:
    out: dict[int, str] = {}
    for path in paths:
        if path.is_file():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.match(r'^(\d+)\s+"(.*)"\s*$', line)
                if m:
                    out.setdefault(int(m.group(1)), m.group(2).replace("\\n", " "))
    return out


def key(name: str) -> str:
    k = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper()
    return k if k and not k[0].isdigit() else ""


def cost(entries) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in entries:
        if c.type in RESOURCES and c.amount > 0 and c.flag:
            out[RESOURCES[c.type]] = out.get(RESOURCES[c.type], 0) + c.amount
    return out


def age_of(internal: str) -> int | None:
    m = re.search(r"Age(\d)", internal)
    return int(m.group(1)) if m else None


ALIASES = {"VILLAGER": "VILLAGER_MALE"}                 # names agents use for a role whose object is named otherwise


def known_names(which: str) -> tuple[dict[str, int], dict[int, str], dict[str, int]]:
    """The object names the resolvers already accept, each id's canonical name, and the tech names, so the tables
    never rename anything."""
    if which == "ror":
        data = games.ror_data()
        return dict(data["objects"]), {int(i): n for i, n in data["object_names"].items()}, dict(data["techs"])
    canonical: dict[int, str] = {}
    for ds in datasets.OBJECT_DATASETS.values():
        for m in ds:
            canonical.setdefault(m.ID, m.name)
    objects = datasets._object_index()
    for alias, name in ALIASES.items():
        objects.setdefault(alias, objects[name])
    return objects, canonical, datasets._info_index("TechInfo")


def table(game: Path, which: str) -> dict:
    spec = GAMES[which]
    dat_path = game / spec["dat"]
    dat = DatFile.parse(str(dat_path))
    names = strings([game / s for s in spec["strings"]])
    objs = {}
    for civ in dat.civs:                                  # first definition of each id across civs (Gaia first)
        for i, u in enumerate(civ.units):
            if u is not None and i not in objs:
                objs[i] = u

    objects: dict[str, dict] = {}
    for i, u in sorted(objs.items()):
        display = names.get(u.language_dll_name, "")
        c = getattr(u, "creatable", None)
        entry = {"display": display, "internal": u.name, "kind": KINDS.get(u.type, "other"), "class": u.class_,
                 "hp": u.hit_points}
        made_at = sorted({t.unit_id for t in (c.train_locations if c else []) if t.unit_id >= 0})
        if made_at:
            entry["made_at"] = made_at
        if c and (price := cost(c.resource_costs)):
            entry["cost"] = price
        objects[str(i)] = entry

    # Buildings that exist once per age look share a display name: each belongs to its earliest-age base.
    groups: dict[str, list[int]] = {}
    for i, e in objects.items():
        if e["kind"] == "building" and e["display"] and age_of(e["internal"]) is not None:
            groups.setdefault(e["display"], []).append(int(i))
    for members in groups.values():
        base = min(members, key=lambda i: (age_of(objects[str(i)]["internal"]), i))
        for i in members:
            objects[str(i)]["age"] = age_of(objects[str(i)]["internal"])
            if i != base:
                objects[str(i)]["variant_of"] = base

    # Name keys: the names the resolvers already use, then display names (the base of a variant group before its
    # looks), then internal names.
    known_objects, canonical, known_techs = known_names(which)
    taken: dict[str, int] = {k: i for k, i in known_objects.items() if str(i) in objects}
    for i, k in canonical.items():
        if str(i) in objects and taken.get(k) == i:
            objects[str(i)]["name"] = k
    order = sorted(objects, key=lambda i: ("variant_of" in objects[i], objects[i]["kind"] == "other", int(i)))
    for i in order:
        for candidate in (objects[i]["display"], objects[i]["internal"]):
            k = key(candidate)
            if k and k not in taken:
                taken[k] = int(i)
                objects[i].setdefault("name", k)
    for i, e in objects.items():                        # the rest share a name with another id: number them
        if "name" not in e:
            e["name"] = f"{key(e['internal']) or 'OBJECT'}_{i}"
            taken[e["name"]] = int(i)

    techs: dict[str, dict] = {}
    tech_taken: dict[str, int] = {k: i for k, i in known_techs.items() if i < len(dat.techs)}
    tech_name = {}
    for k, i in tech_taken.items():
        tech_name.setdefault(i, k)
    for i, t in enumerate(dat.techs):
        display = names.get(t.language_dll_name, "")
        entry = {"display": display, "internal": t.name}
        if i in tech_name:
            entry["name"] = tech_name[i]
        if price := cost(t.resource_costs):
            entry["cost"] = price
        at = sorted({loc.location_id for loc in getattr(t, "research_locations", []) if loc.location_id >= 0})
        if at:
            entry["researched_at"] = at
        for candidate in (display, t.name):
            k = key(candidate)
            if k and k not in tech_taken:
                tech_taken[k] = i
                entry.setdefault("name", k)
        if "name" not in entry:
            entry["name"] = f"{key(t.name) or 'TECH'}_{i}"
            tech_taken[entry["name"]] = i
        techs[str(i)] = entry

    return {
        "game": which,
        "build": exe_version(game / EXE),
        "data": {spec["dat"]: hashlib.sha256(dat_path.read_bytes()).hexdigest()},
        "source": "scripts/gen_unit_tables.py, from the game's data file and English strings",
        "objects": objects,
        "names": dict(sorted(taken.items())),
        "techs": techs,
        "tech_names": dict(sorted(tech_taken.items())),
    }


def main() -> int:
    game = Path(sys.argv[1]) if len(sys.argv) > 1 else find_game_dir()
    if game is None:
        print("AoE2 DE not found (set AOE2DE_PATH or pass it)", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for which in GAMES:
        t = table(game, which)
        path = OUT / f"{which}.json"
        path.write_text(json.dumps(t, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        units = sum(1 for o in t["objects"].values() if o["kind"] == "unit")
        buildings = sum(1 for o in t["objects"].values() if o["kind"] == "building")
        print(f"{path.name}: build {t['build']}, {len(t['objects'])} objects ({units} units, {buildings} buildings), "
              f"{len(t['techs'])} techs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
