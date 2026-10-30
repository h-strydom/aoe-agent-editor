"""Round-trip tests: every edit is saved, reloaded and asserted."""
from __future__ import annotations

from pathlib import Path

import pytest

from aoe2ed.session import SESSIONS
from aoe2ed.tools import load_all

TOOLS = load_all()
FIX = Path(__file__).parent / "fixtures"


def call(_tool, **kw):
    return TOOLS[_tool](**kw)


def reload(handle, tmp_path, name="out.aoe2scenario"):
    out = tmp_path / name
    call("scenario_save", handle=handle, path=str(out), overwrite=True)
    return call("scenario_open", path=str(out))["handle"]


@pytest.fixture
def blank():
    return call("scenario_new", map_size=100)["handle"]


def test_open_fixture_summary():
    h = call("scenario_open", path=str(FIX / "siege.aoe2scenario"))["handle"]
    s = call("scenario_summary", handle=h)
    assert s["triggers"] > 50 and s["units"] > 0
    assert any(t["name"] for t in s["trigger_list"])
    # Opening an old (1.53) scenario must not break newer ones in the same process.
    assert call("scenario_new")["scenario_version"] >= "1.59"


def test_triggers_roundtrip(blank, tmp_path):
    call("triggers_add", handle=blank, triggers=[
        {"name": "Start", "effects": [
            {"type": "load_key_value", "variable": "meta", "message": "meta_points", "quantity": 0},
            {"type": "activate_trigger", "trigger_id": "Win"}]},
        {"name": "Win", "enabled": False, "conditions": [{"type": "timer", "timer": 10}],
         "effects": [{"type": "create_object", "object_list_unit_id": "ARCHER", "source_player": "ONE",
                      "location": [5, 5]},
                     {"type": "change_variable", "variable": "meta", "operation": "Add", "quantity": 3}]},
    ])
    h2 = reload(blank, tmp_path)
    win = call("trigger_get", handle=h2, trigger="Win")
    assert win["enabled"] is False
    assert win["effects"][0]["object_list_unit_id"] == 4
    assert win["effects"][1]["_names"]["operation"].upper() == "ADD"
    start = call("trigger_get", handle=h2, trigger="Start")
    assert start["effects"][1]["trigger_id"] == win["index"]
    assert call("variables_list", handle=h2) == [{"id": 0, "name": "meta"}]


def test_trigger_update_remove(blank):
    call("triggers_add", handle=blank, triggers=[{"name": "A"}, {"name": "B"}])
    call("trigger_update", handle=blank, trigger="A", changes={"looping": True, "effects": [
        {"type": "send_chat", "source_player": 1, "message": "hi"}]})
    assert call("trigger_get", handle=blank, trigger="A")["looping"] is True
    call("triggers_remove", handle=blank, triggers=["A"])
    assert [t["name"] for t in call("triggers_list", handle=blank)] == ["B"]


def test_bad_param_rejected(blank):
    with pytest.raises(ValueError, match="Unknown params"):
        call("triggers_add", handle=blank, triggers=[
            {"name": "X", "effects": [{"type": "send_chat", "bogus": 1}]}])


def test_units_players_map(blank, tmp_path):
    call("units_add", handle=blank, units=[
        {"player": 1, "type": "CASTLE", "x": 20, "y": 20},
        {"player": 0, "type": "GOLD_MINE", "x": 30.5, "y": 30.5}])
    call("player_set", handle=blank, player=1, fields={
        "civilization": "BRITONS", "starting_age": "FEUDAL", "gold": 777, "disabled_units": ["ARCHER"]})
    call("map_set_terrain", handle=blank, terrain="WATER_DEEP", area=[0, 0, 9, 9])
    call("map_set_elevation", handle=blank, elevation=3, area=[50, 50, 60, 60])
    h2 = reload(blank, tmp_path)
    units = call("units_list", handle=h2)["units"]
    assert {u["name"] for u in units} >= {"CASTLE", "GOLD_MINE"}
    p1 = call("players_get", handle=h2)[1]
    assert p1["civilization"] == "BRITONS" and p1["gold"] == 777 and p1["disabled_units"] == [4]
    assert p1["starting_age"] == "FEUDAL_AGE"
    grid = call("map_get", handle=h2, x1=0, y1=0, x2=2, y2=2)["rows"]
    assert all(v == grid[0][0] for row in grid for v in row) and grid[0][0] != 0
    assert call("map_get", handle=h2, x1=55, y1=55, x2=55, y2=55, layer="elevation")["rows"] == [[3]]


def test_options_messages(blank, tmp_path):
    call("options_set", handle=blank, fields={"victory_condition": "CUSTOM", "lock_teams": True})
    call("messages_set", handle=blank, fields={"instructions": "Survive 45 minutes."})
    h2 = reload(blank, tmp_path)
    assert call("options_get", handle=h2)["victory_condition"] == "CUSTOM"
    assert call("scenario_summary", handle=h2)["messages"]["instructions"] == "Survive 45 minutes."


def test_xs_embed_and_check(blank, tmp_path):
    good = 'void main() { xsChatData("hello"); }'
    assert call("xs_check", code=good)["ok"]
    bad = call("xs_check", code='void main() { string s = 3; }')
    assert not bad["ok"] and bad["diagnostics"][0]["code"] == "TypeError"
    call("xs_embed", handle=blank, code=good)
    h2 = reload(blank, tmp_path)
    assert "hello" in call("xs_get", handle=h2)["script_calls"][0]["code"]


def test_triggers_copy(blank):
    other = call("scenario_new")["handle"]
    call("triggers_add", handle=blank, triggers=[
        {"name": "Go", "effects": [{"type": "activate_trigger", "trigger_id": "Next"},
                                   {"type": "change_variable", "variable": "gold", "quantity": 1, "operation": "Set"}]},
        {"name": "Next"}])
    call("variable_add", handle=other, name="padding")
    call("triggers_copy", src_handle=blank, dst_handle=other)
    go = call("trigger_get", handle=other, trigger="Go")
    assert go["effects"][0]["trigger_id"] == call("trigger_get", handle=other, trigger="Next")["index"]
    assert go["effects"][1]["variable"] == 1  # 'gold' got a new id after 'padding'


def test_lookup_and_run_python(blank):
    assert call("lookup", query="castle", kinds=["building"])[0]["name"] == "CASTLE"
    r = call("run_python", handle=blank, code="result = scenario.map_manager.map_size")
    assert r["result"] == 100 and r["error"] is None


def test_schema(blank):
    sch = call("effect_schema", handle=blank, effect_type="store_key_value")
    assert [p["name"] for p in sch["params"]] == ["variable", "message"]
    assert any(e["type"] == "script_call" for e in call("effect_types", handle=blank))
