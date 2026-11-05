"""Build the civ bonus table for Return of Rome from the game's own data.

For each civilization: the military units its bonuses favour (better hit points, speed, armour, attack, range or
fire rate, or cheaper), what each bonus is, where the unit is made and the age it becomes available; and the
units its tech tree takes away. Writes src/aoe2ed/data/civ_bonuses.json, pinned like the unit tables.

Where bonuses live (RoR, 2026-11-05): each civ's tech tree effect (civ.tech_tree_id) disables techs and carries
most unit bonuses; techs with tech.civ == civ add the rest (some per age). Bonuses name a unit or a unit class;
a unit line counts once, under its first unit (Hoplite for Phalangite and Centurion).

  uv run --with genieutils-py python scripts/gen_civ_bonuses.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from genieutils.datfile import DatFile

from aoe2ed import tables
from aoe2ed.config import find_game_dir
from aoe2ed.tables import EXE, exe_version

OUT = Path(__file__).resolve().parents[1] / "src" / "aoe2ed" / "data" / "civ_bonuses.json"
DAT = "modes/Pompeii/resources/_common/dat/empires2_x2_p1.dat"
AGE_TECHS = {101: 2, 102: 3, 103: 4}                 # Tool, Bronze, Iron Age (Stone is 1)
NOT_ARMY = {2, 4, 18, 20, 21}                        # trade boat, villager, priest, transport, fishing boat
NAVAL = {22}
ATTRS = {0: "hp", 5: "speed", 8: "armour", 9: "attack", 10: "fire rate", 12: "range", 100: "cost", 101: "train time"}
LOWER_IS_BETTER = {10, 100, 101}


def enabling_age(d: DatFile) -> dict[int, int]:
    """The age each unit first becomes available: the age of the tech that enables it (Stone if none does)."""
    tech_age: dict[int, int] = {}

    def age(t: int, seen=()) -> int:
        if t in AGE_TECHS:
            return AGE_TECHS[t]
        if t in tech_age:
            return tech_age[t]
        if t in seen or not 0 <= t < len(d.techs):
            return 1
        req = [r for r in d.techs[t].required_techs if r >= 0]
        tech_age[t] = max([age(r, (*seen, t)) for r in req], default=1)
        return tech_age[t]

    out: dict[int, int] = {}
    for t, tech in enumerate(d.techs):
        if tech.effect_id < 0 or tech.civ > 0:
            continue
        for c in d.effects[tech.effect_id].effect_commands:
            if c.type == 2 and c.b == 1:
                out[c.a] = min(out.get(c.a, 9), age(t))
    return out


def lines(d: DatFile) -> dict[int, int]:
    """Each upgraded unit -> the first unit of its line."""
    up = {}
    for e in d.effects:
        for c in e.effect_commands:
            if c.type == 3 and c.a >= 0 and c.b >= 0 and c.a != c.b:
                up.setdefault(c.b, c.a)
    out = {}
    for u in up:
        root, seen = u, set()
        while root in up and root not in seen:
            seen.add(root)
            root = up[root]
        out[u] = root
    return out


def army_units(d: DatFile) -> dict[int, object]:
    return {i: u for i, u in enumerate(d.civs[0].units)
            if u and u.type == 70 and u.creatable and u.creatable.train_locations and u.class_ not in NOT_ARMY}


def better(c, unit) -> str | None:
    """'hp x1.33' if the command improves the attribute for this unit, else None."""
    attr, value = c.c, c.d
    if attr not in ATTRS:
        return None
    name = ATTRS[attr]
    if attr in (8, 9):                                 # armour/attack: class << 8 | amount
        amount = int(value) & 0xFF
        return f"{name} +{amount}" if c.type == 4 and amount > 0 else None
    if c.type == 5:
        good = value < 1 if attr in LOWER_IS_BETTER else value > 1
        return f"{name} x{value:.3g}" if good and value != 1 else None
    if c.type == 4:
        good = value < 0 if attr in LOWER_IS_BETTER else value > 0
        return f"{name} {value:+g}" if good else None
    if c.type == 0 and attr == 0 and value > unit.hit_points:
        return f"hp {unit.hit_points} -> {value:g}"
    if c.type == 0 and attr == 10 and unit.type_50 and 0 < value < unit.type_50.reload_time:
        return f"fire rate {unit.type_50.reload_time:g}s -> {value:g}s"
    return None


def civ_table(d: DatFile, ci: int, names: dict[int, str], army: dict[int, object], line: dict[int, int],
              ages: dict[int, int]) -> dict:
    civ = d.civs[ci]
    effects = [civ.tech_tree_id] + [t.effect_id for t in d.techs if t.civ == ci and t.effect_id >= 0]
    disabled_techs = {int(c.d) for c in d.effects[civ.tech_tree_id].effect_commands if c.type == 102}
    gone = set()
    for t in disabled_techs:
        if 0 <= t < len(d.techs) and d.techs[t].effect_id >= 0:
            for c in d.effects[d.techs[t].effect_id].effect_commands:
                if c.type == 2 and c.b == 1:
                    gone.add(c.a)
                if c.type == 3:
                    gone.add(c.b)
    favoured: dict[int, list[str]] = {}
    for e in effects:
        for c in d.effects[e].effect_commands:
            if c.type not in (0, 4, 5):
                continue
            hit = [c.a] if c.a >= 0 else [i for i, u in army.items() if u.class_ == c.b]
            for i in hit:
                if i not in army or i in gone:
                    continue
                text = better(c, army[i])
                if text:
                    base = line.get(i, i)
                    favoured.setdefault(base, [])
                    label = text if base == i else f"{text} ({names.get(i, army[i].name)})"
                    if label not in favoured[base]:
                        favoured[base].append(label)
    out = []
    for i, bonuses in favoured.items():
        if i not in names or i in gone or i not in army or army[i].creatable.hero_mode:
            continue
        if not (civ.units[i] and civ.units[i].enabled) and i not in ages:
            continue                                   # in the data but nothing makes it available (AoE2 leftovers)
        info = tables.info(i, "ror") or {}
        made_at = (info.get("made_at") or [None])[0]
        if made_at is None:
            continue
        b_age = ages.get(tables.object_id(made_at, "ror") or -1, 1) if made_at else 1
        out.append({"unit": names[i], "made_at": made_at, "age": max(ages.get(i, 1), b_age),
                    "naval": army[i].class_ in NAVAL, "bonuses": bonuses})
    out.sort(key=lambda f: (-len(f["bonuses"]), f["unit"]))
    return {"favoured": out, "unavailable": sorted(names[i] for i in gone if i in names and i in army)}


def main() -> int:
    game = find_game_dir()
    if game is None:
        print("AoE2 DE not found", file=sys.stderr)
        return 1
    dat = game / DAT
    d = DatFile.parse(str(dat))
    t = tables.load("ror")
    names = {int(i): o["name"] for i, o in t["objects"].items()}
    army, line, ages = army_units(d), lines(d), enabling_age(d)
    civs = {c.name.upper(): civ_table(d, i, names, army, line, ages) for i, c in enumerate(d.civs) if i > 0}
    out = {"game": "ror", "exe": exe_version(game / EXE),
           "data": {DAT: hashlib.sha256(dat.read_bytes()).hexdigest()}, "civs": civs}
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(civs)} civs, {sum(len(c['favoured']) for c in civs.values())} favoured units")
    return 0


if __name__ == "__main__":
    sys.exit(main())
