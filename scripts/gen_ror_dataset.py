"""Regenerate the Return of Rome name tables (src/aoe2ed/data/ror.json) from the game's own data.

    uv run --with genieutils-py python scripts/gen_ror_dataset.py [AOE2DE_PATH]

RoR has its own game data (modes/Pompeii/resources/_common/dat/empires2_x2_p1.dat): many object
ids mean something else than in AoE2 (74 is Militia in AoE2, Short Swordsman in RoR). This reads
both games' data with genieutils-py and writes:
  objects: NAME -> id for every named RoR object (display name from RoR's English strings, else the
           internal name), plus the AoE2 names of objects both games share (same id and same
           internal name: trees, gold, stone, berries...), which stay valid in RoR.
  techs:   NAME -> id
  civs:    NAME -> data name stored in scenarios ("EGYPTIANS" -> "EGYPTIAN-CIV")
  not_shared: AoE2 object names whose id means a different RoR object, for helpful errors.
Only ids and names are written, never game assets.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from genieutils.datfile import DatFile

from aoe2ed.config import find_game_dir
from aoe2ed.datasets import OBJECT_DATASETS

OUT = Path(__file__).resolve().parents[1] / "src" / "aoe2ed" / "data" / "ror.json"


def strings(path: Path) -> dict[int, str]:
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r'^(\d+)\s+"(.*)"\s*$', line)
        if m:
            out[int(m.group(1))] = m.group(2).replace("\\n", " ")
    return out


def key(name: str) -> str:
    k = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper()
    return k if k and not k[0].isdigit() else ""


def objects_by_id(dat) -> dict[int, object]:
    """First non-empty definition of every object id across civs (Gaia first)."""
    out = {}
    for civ in dat.civs:
        for i, u in enumerate(civ.units):
            if u is not None and i not in out:
                out[i] = u
    return out


def main(game: Path) -> None:
    ror_dat = DatFile.parse(str(game / "modes/Pompeii/resources/_common/dat/empires2_x2_p1.dat"))
    aoe2_dat = DatFile.parse(str(game / "resources/_common/dat/empires2_x2_p1.dat"))
    names = strings(game / "modes/Pompeii/resources/en/strings/key-value/key-value-pompeii-strings-utf8.txt")
    ror, aoe2 = objects_by_id(ror_dat), objects_by_id(aoe2_dat)

    # Units the tech trees offer come first, so a display name shared by several ids maps to the
    # playable one.
    playable: list[int] = []
    for f in sorted((game / "modes/Pompeii/resources/_common/dat/CivTechTrees").glob("*.json")):
        tree = json.loads(f.read_text(encoding="utf-8"))
        # A unit node's "Node ID" is the unit; a building node's "Node ID" is its tech, so use "Building ID".
        nodes = [(n.get("Node ID"), n) for n in tree.get("civ_techs_units", [])]
        nodes += [(n.get("Building ID"), n) for n in tree.get("civ_techs_buildings", [])]
        for nid, _node in nodes:
            if isinstance(nid, int) and nid in ror and nid not in playable:
                playable.append(nid)

    objects: dict[str, int] = {}
    display: dict[int, str] = {}  # id -> name from RoR's display strings
    for i in sorted(playable) + sorted(ror):  # lowest id first: a building's Age1 base, not its later look
        u = ror[i]
        k = key(names.get(u.language_dll_name, ""))
        if k and k not in objects:
            objects[k] = i
            display.setdefault(i, k)
    for i in sorted(ror):  # internal names (VMBAS, GOLDM...) as extra aliases
        k = key(ror[i].name)
        if k and k not in objects:
            objects[k] = i

    shared = {i for i in ror if i in aoe2 and ror[i].name == aoe2[i].name}
    not_shared: dict[str, str] = {}
    for ds in OBJECT_DATASETS.values():
        for m in ds:
            if m.ID in shared:
                objects.setdefault(m.name, m.ID)
            elif m.name not in objects and m.ID in ror:
                ror_name = names.get(ror[m.ID].language_dll_name) or ror[m.ID].name
                not_shared[m.name] = key(ror_name) or ror_name

    # AoE2 names the tools use by default whose RoR counterpart has the same role but another name.
    for alias, ror_name in {"VILLAGER": "VILLAGER_MALE", "SCOUT_CAVALRY": "SCOUT"}.items():
        if ror_name in objects:
            objects.setdefault(alias, objects[ror_name])
            not_shared.pop(alias, None)

    techs: dict[str, int] = {}
    for i, t in enumerate(ror_dat.techs):
        for candidate in (names.get(t.language_dll_name, ""), t.name):
            k = key(candidate)
            if k and k not in techs:
                techs[k] = i

    # One name per id for reverse lookups: RoR display name, else the shared AoE2 name, else internal.
    object_names: dict[int, str] = dict(display)
    for ds in OBJECT_DATASETS.values():
        for m in ds:
            if m.ID in shared and objects.get(m.name) == m.ID:
                object_names.setdefault(m.ID, m.name)
    for k, i in objects.items():
        object_names.setdefault(i, k)
    tech_names: dict[int, str] = {}
    for k, i in techs.items():
        tech_names.setdefault(i, k)

    civ_list = json.loads((game / "modes/Pompeii/resources/_common/dat/civilizations.json").read_text(encoding="utf-8"))
    civs = {}
    for c in civ_list["civilization_list"]:
        if c["data_name"] != "GAIA":
            civs[key(c.get("tech_tree_name") or c["internal_name"])] = c["data_name"]
            civs.setdefault(key(c["internal_name"]), c["data_name"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": "Generated by scripts/gen_ror_dataset.py from the game's RoR data",
                               "objects": dict(sorted(objects.items())), "techs": dict(sorted(techs.items())),
                               "civs": dict(sorted(civs.items())), "not_shared": dict(sorted(not_shared.items())),
                               "object_names": {str(i): n for i, n in sorted(object_names.items())},
                               "tech_names": {str(i): n for i, n in sorted(tech_names.items())}},
                              indent=1), encoding="utf-8")
    print(f"wrote {OUT}: {len(objects)} objects, {len(techs)} techs, {len(civs)} civ names, "
          f"{len(not_shared)} AoE2 names that differ in RoR")


if __name__ == "__main__":
    game = Path(sys.argv[1]) if len(sys.argv) > 1 else find_game_dir()
    if game is None:
        sys.exit("AoE2 DE install not found; pass its path")
    main(game)
