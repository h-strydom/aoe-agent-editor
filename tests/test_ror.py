"""Return of Rome: separate names, civs, variant flag and profile folders."""
from __future__ import annotations

import pytest

from aoe2ed import datasets as D
from aoe2ed import games
from aoe2ed import triggers as T
from aoe2ed.compiler import CompileError, compile_campaign
from aoe2ed.config import Paths
from aoe2ed.session import SESSIONS
from aoe2ed.tools import load_all

TOOLS = load_all()


def test_names_switch_by_game():
    assert D.object_id("MILITIA") == 74
    with games.use("ror"):
        assert D.object_id("CLUBMAN") == 281 and D.object_id("HOPLITE") == 93
        assert D.object_id("BARRACKS") == 12 and D.object_id("GOLD_MINE") == 66  # shared object
        assert D.describe_value("UnitInfo", 74) == "SHORT_SWORDSMAN"
        with pytest.raises(KeyError, match="AoE2 name.*SHORT_SWORDSMAN"):
            D.object_id("MILITIA")
        assert D.tech_id("ACADEMY") == 72
    assert games.current() == "aoe2"


def test_ror_scenario_roundtrip(tmp_path):
    h = TOOLS["scenario_new"](map_size=60, game="ror")["handle"]
    TOOLS["player_set"](handle=h, player=1, fields={"civilization": "EGYPTIANS"})
    TOOLS["units_add"](handle=h, units=[{"player": 1, "type": "CLUBMAN", "x": 10, "y": 10}])
    T.add_triggers(SESSIONS.get(h).scenario, [{"name": "Spawn", "effects": [
        {"type": "create_object", "object_list_unit_id": "HOPLITE", "source_player": 1, "location": [12, 12]}]}])
    path = tmp_path / "ror.aoe2scenario"
    SESSIONS.save(h, path)
    assert games.file_game(path.read_bytes()) == "ror"
    o = SESSIONS.open(path)
    assert o.info()["game"] == "ror"
    p1 = TOOLS["players_get"](handle=o.handle)[1]
    assert p1["civilization"] == "EGYPTIAN-CIV"
    units = TOOLS["units_list"](handle=o.handle, player=1)["units"]
    assert units[0]["name"] == "CLUBMAN"
    eff = TOOLS["trigger_get"](handle=o.handle, trigger="Spawn")["effects"][0]
    assert eff["object_list_unit_id"] == 93 and eff["_names"]["object_list_unit_id"] == "HOPLITE"


def test_ror_civ_errors():
    h = TOOLS["scenario_new"](game="ror")["handle"]
    with pytest.raises(ValueError, match="Unknown Return of Rome civilization 'BRITONS'"):
        TOOLS["player_set"](handle=h, player=1, fields={"civilization": "BRITONS"})


def test_ror_profile_folders(tmp_path):
    p = Paths(game=None, profile=tmp_path)
    assert p.user_dir("scenario", "ror") == tmp_path / "modes" / "Pompeii" / "resources" / "_common" / "scenario"
    assert p.user_dir("campaign") == tmp_path / "resources" / "_common" / "campaign"


def test_compile_ror_campaign(tmp_path):
    spec = {"name": "ror_t", "game": "ror", "missions": [{
        "id": "m", "map": {"size": "tiny", "seed": 2, "players": 1, "extra_players": 1},
        "players": {1: {"civilization": "GREEKS"}, 2: {"civilization": "PERSIANS"}},
        "blocks": [{"use": "anchor", "player": 2, "at": [1, 1]},
                   {"use": "waves", "spawns": [[100, 100, 110, 110]], "target": "player1_base", "keepalive_sec": 0,
                    "waves": [{"at": 30, "units": {"CLUBMAN": 3, "BOWMAN": 2}}]},
                   {"use": "survive", "minutes": 5},
                   {"use": "lose_if_destroyed", "unit_type": "TOWN_CENTER"}]}]}
    rep = compile_campaign(spec, out_dir=tmp_path, test_mode=True, render=False)
    assert rep["ok"] and rep["game"] == "ror"
    s = SESSIONS.open(rep["missions"][0]["scenario"]).scenario
    assert games.scenario_game(s) == "ror"
    wave = T.trigger_to_dict(T.find_trigger(s, "Wave 1"))
    assert {e["object_list_unit_id"] for e in wave["effects"] if e["type"] == "create_object"} == {281, 4}
    with pytest.raises(CompileError, match="AoE2 name"):
        bad = {**spec, "missions": [{**spec["missions"][0], "blocks": [
            {"use": "waves", "spawns": [[1, 1, 5, 5]], "target": [50, 50], "waves": [{"at": 5, "units": {"MILITIA": 1}}]}]}]}
        compile_campaign(bad, out_dir=tmp_path / "bad", render=False)
    with pytest.raises(CompileError, match="Unknown game"):
        compile_campaign({**spec, "game": "aoe3"}, out_dir=tmp_path / "x", render=False)


def test_ror_crucible_example_compiles(tmp_path):
    from pathlib import Path
    spec = Path(__file__).parents[1] / "examples" / "crucible_ror" / "campaign.yaml"
    rep = compile_campaign(spec, out_dir=tmp_path, test_mode=True, render=False)
    assert rep["ok"] and rep["game"] == "ror" and rep["warnings"] == []
    from aoe2ed.campaign import Campaign
    camp = Campaign.read(rep["campaign"])
    assert all(games.file_game(sc.data) == "ror" for sc in camp.scenarios)


def test_buildings_are_their_buildable_base():
    # RoR lists each building per age; the name is the Age1 base villagers build, not a later look
    # ("Academy Age3" 18 has a lower id than "Academy Age1" 103). AIs build by these ids.
    objects = games.ror_data()["objects"]
    assert (objects["ACADEMY"], objects["TEMPLE"], objects["TOWN_CENTER"]) == (103, 104, 109)
