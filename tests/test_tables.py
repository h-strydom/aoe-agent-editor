"""The unit/tech tables generated from the game's data, and the check that they match the installed build."""
from __future__ import annotations

import pytest

from aoe2ed import datasets, games, tables
from aoe2ed.config import find_game_dir
from aoe2ed.tools.meta import unit_info


@pytest.mark.parametrize("game", tables.GAMES)
def test_tables_are_pinned_and_consistent(game):
    t = tables.load(game)
    assert t["build"].count(".") == 3 and len(next(iter(t["data"].values()))) == 64
    for kind, index in (("objects", "names"), ("techs", "tech_names")):
        names = [e["name"] for e in t[kind].values()]
        assert len(names) == len(set(names))                         # one name per id
        assert all(t[index][e["name"]] == int(i) for i, e in t[kind].items())


def test_ror_buildings_point_to_their_buildable_base():
    academy = tables.info("ACADEMY_AGE3", "ror")
    assert academy["age"] == 3 and academy["variant_of"] == {"id": 103, "name": "ACADEMY"}
    base = tables.info(103, "ror")
    assert base["age"] == 1 and {look["id"] for look in base["age_looks"]} >= {18}
    assert tables.info("HOPLITE", "ror")["made_at"] == ["ACADEMY"]


def test_table_names_agree_with_the_resolvers():
    for game in tables.GAMES:
        with games.use(game):
            for name in ("TOWN_CENTER", "VILLAGER", "ARCHER" if game == "aoe2" else "BOWMAN", "HOUSE"):
                assert tables.object_id(name, game) == datasets.object_id(name)


def test_aoe2_resolver_falls_back_to_the_table():
    t = tables.load("aoe2")
    only_in_table = next(name for name, i in t["names"].items() if name not in datasets._object_index())
    with games.use("aoe2"):
        assert datasets.object_id(only_in_table) == t["names"][only_in_table]


def test_unit_info_tool():
    out = unit_info("hoplite", game="ror", kinds=["unit"])
    hop = out["results"][0]
    assert hop["name"] == "HOPLITE" and hop["cost"] == {"food": 60, "gold": 40} and out["build"]
    assert unit_info("Loom", game="aoe2", kinds=["tech"])["results"][0]["researched_at"] == ["TOWN_CENTER"]


@pytest.mark.skipif(find_game_dir() is None, reason="AoE2 DE not installed")
def test_tables_match_the_installed_game():
    check = tables.build_check()
    assert check["ok"], f"game patched since the tables were made; rerun scripts/gen_unit_tables.py: {check}"
