"""Compiler features and blocks added after the frontier acceptance test (docs/acceptance-frontier.md)."""
from __future__ import annotations

from pathlib import Path

import pytest

from aoe2ed import blocks as B
from aoe2ed import triggers as T
from aoe2ed.compiler import CompileError, compile_campaign
from aoe2ed.session import SESSIONS

FRONTIER = Path(__file__).parents[1] / "examples" / "frontier" / "campaign.yaml"


def _spec(**mission):
    return {"name": "t", "missions": [{"id": "m", "map_size": 60, **mission}]}


def _built(rep, i=0):
    return SESSIONS.open(rep["missions"][i]["scenario"]).scenario


def _effects(s, name):
    return T.trigger_to_dict(T.find_trigger(s, name))["effects"]


def test_frontier_compiles_cleanly(tmp_path):
    rep = compile_campaign(FRONTIER, out_dir=tmp_path, test_mode=True, render=False)
    assert rep["ok"] and rep["warnings"] == []
    assert len(rep["missions"]) == 3


def test_defaults_merge_and_unknown_keys(tmp_path):
    spec = {"name": "t", "defaults": {"options": {"victory_condition": "CUSTOM"}, "map_size": 50},
            "x-notes": "ignored quietly",
            "missions": [{"id": "a", "trigers": []}, {"id": "b", "map_size": 70}]}
    rep = compile_campaign(spec, out_dir=tmp_path, render=False)
    assert any("unknown key 'trigers'" in w for w in rep["warnings"])
    assert not any("x-notes" in w for w in rep["warnings"])
    assert _built(rep, 0).map_manager.map_size == 50 and _built(rep, 1).map_manager.map_size == 70


def test_helper_splice_and_stack_warning(tmp_path):
    rep = compile_campaign(_spec(points={"p": [30, 30]}, triggers=[
        {"name": "Mix", "effects": [
            {"type": "send_chat", "source_player": 1, "message": "a"},
            {"$helper": "spawn", "unit": "KNIGHT", "count": 3, "at": "p"},
            {"type": "send_chat", "source_player": 1, "message": "b"}]},
        {"name": "Stacked", "effects": [
            {"type": "create_object", "object_list_unit_id": "KNIGHT", "source_player": 1, "location": [5, 5]},
            {"type": "create_object", "object_list_unit_id": "KNIGHT", "source_player": 1, "location": [5, 5]}]}]),
        out_dir=tmp_path, render=False)
    types = [e["type"] for e in _effects(_built(rep), "Mix")]
    assert types == ["send_chat", "create_object", "create_object", "create_object", "send_chat"]
    assert any("'Stacked'" in w and "spawn" in w for w in rep["warnings"])


def test_errors_name_mission_and_trigger(tmp_path):
    with pytest.raises(CompileError, match=r"\[m\] .*trigger 'Bad' effect 0 \(create_object\)"):
        compile_campaign(_spec(triggers=[{"name": "Bad", "effects": [
            {"type": "create_object", "object_list_unit_id": "NOT_A_UNIT", "location": [1, 1]}]}]),
            out_dir=tmp_path, render=False)


def test_failed_compile_leaves_no_partial_output(tmp_path):
    spec = {"name": "t", "missions": [{"id": "ok", "map_size": 40},
                                      {"id": "bad", "map_size": 40, "blocks": [{"use": "nope"}]}]}
    with pytest.raises(CompileError):
        compile_campaign(spec, out_dir=tmp_path, render=False)
    assert list(tmp_path.iterdir()) == []


def test_units_count_spreads_without_stacking(tmp_path):
    rep = compile_campaign(_spec(points={"yard": [30, 30]}, units=[
        {"player": 1, "type": "KNIGHT", "at": "yard", "count": 4},
        {"player": 1, "type": "ARCHER", "at": "yard", "count": 4}]), out_dir=tmp_path, render=False)
    tiles = [(int(u.x), int(u.y)) for u in _built(rep).unit_manager.get_player_units(1)]
    assert len(tiles) == 8 and len(set(tiles)) == 8


def test_when_gates_block_and_blocks_can_reference_raw_triggers(tmp_path):
    rep = compile_campaign(_spec(areas={"sp": [1, 1, 5, 5]}, points={"t": [30, 30]}, blocks=[
        {"use": "waves", "name": "Gated", "spawns": ["sp"], "target": "t", "keepalive_sec": 0,
         "when": [{"type": "variable_value", "variable": "flag", "comparison": "EQUAL", "quantity": 1}],
         "waves": [{"at": 10, "units": {"MILITIA": 2}}], "on_wave": [{"type": "activate_trigger", "trigger_id": "Later"}]}],
        triggers=[{"name": "Later", "enabled": False}]), out_dir=tmp_path, render=False)
    s = _built(rep)
    w = T.trigger_to_dict(T.find_trigger(s, "Gated 1"))
    assert [c["type"] for c in w["conditions"]] == ["timer", "variable_value"]
    assert w["effects"][-1]["trigger_id"] == T.find_trigger(s, "Later").trigger_id
    assert [t.name for t in s.trigger_manager.triggers][-1] == "Later"


def test_choice_block(tmp_path):
    o = SESSIONS.new(40)
    ctx = B.Ctx(o.scenario)
    r = B.choice(ctx, prompt="Pick", var="pick", store_key="pick", at=30, default_option=2, timeout_sec=20,
                 options=[{"label": "A", "value": 7}, {"label": "B", "value": 9,
                                                      "effects": [{"type": "send_chat", "source_player": 1, "message": "b"}]}])
    s = o.scenario
    opt2 = T.trigger_to_dict(T.find_trigger(s, "Choice 2"))
    assert opt2["conditions"][0]["decision_option"] == 2
    assert {"change_variable", "store_key_value", "send_chat"} <= {e["type"] for e in opt2["effects"]}
    timeout = T.trigger_to_dict(T.find_trigger(s, "Choice Timeout"))
    assert timeout["enabled"] is False
    assert any(e["type"] == "change_variable" and e["quantity"] == 9 for e in timeout["effects"])
    assert r["decision_id"] > 499
    with pytest.raises(ValueError, match="exactly 2"):
        B.choice(ctx, prompt="x", var="v", options=[{"label": "only"}], name="C2")


def test_escort_block(tmp_path):
    o = SESSIONS.new(60)
    ctx = B.Ctx(o.scenario, areas={"start": (1, 1, 4, 4), "home": (50, 50, 55, 55)}, points={"mid": (30, 30)})
    r = B.escort(ctx, unit="TRADE_CART_FULL", count=3, start="start", waypoints=["mid"], destination="home",
                 store_key="arrived", speed=0.6)
    assert len(set(r["unit_refs"])) == 3
    s = o.scenario
    start = _effects(s, "Escort Start")
    moves = [e for e in start if e["type"] == "task_object"]
    assert len(moves) == 2 and moves[1].get("queue_action") == 1
    arrive = T.trigger_to_dict(T.find_trigger(s, "Escort Arrive"))
    assert arrive["looping"] and arrive["effects"][0]["max_units_affected"] == 1
    assert any(e["type"] == "store_key_value" for e in _effects(s, "Escort Done"))


def test_waves_chase_xs():
    o = SESSIONS.new(60)
    ctx = B.Ctx(o.scenario, areas={"sp": (1, 1, 5, 5)}, points={"t": (30, 30)})
    B.waves(ctx, spawns=["sp"], target="t", waves=[{"at": 5, "units": {"MILITIA": 2}}],
            chase={"player": 1, "unit": "TRADE_CART_FULL"})
    assert "Wave Keepalive" not in ctx.trigger_names()
    assert any("aoe2edChaseWave" in c for c in ctx.xs_chunks)


def test_decision_option_names_resolve():
    o = SESSIONS.new(40)
    T.add_triggers(o.scenario, [{"name": "D", "conditions": [
        {"type": "decision_triggered", "decision_id": 1, "decision_option": "Option2"}]}])
    assert T.trigger_to_dict(T.find_trigger(o.scenario, "D"))["conditions"][0]["decision_option"] == 2


def test_cli_one_line_errors(capsys):
    from aoe2ed.cli import main
    assert main(["call", "enum_values", '{"name": "NoSuchEnum"}']) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ValueError: Unknown dataset 'NoSuchEnum'") and "Traceback" not in err


def test_computer_players_get_no_ai_unless_asked(tmp_path):
    rep = compile_campaign({"name": "t", "missions": [
        {"id": "a", "map_size": 40},
        {"id": "b", "map_size": 40, "players": {2: {"ai": "default"}}}]}, out_dir=tmp_path, render=False)
    p2a = _built(rep, 0).player_manager.players[2]
    p2b = _built(rep, 1).player_manager.players[2]
    assert p2a.personality == "NoneAi"
    assert p2b.personality != "NoneAi"


def test_escort_uncontrollable_by_default():
    o = SESSIONS.new(60)
    ctx = B.Ctx(o.scenario, areas={"start": (1, 1, 4, 4), "home": (50, 50, 55, 55)})
    r = B.escort(ctx, unit="TRADE_CART_FULL", count=2, start="start", destination="home")
    first = _effects(o.scenario, "Escort Start")[0]
    assert first["type"] == "disable_object_selection" and first["selected_object_ids"] == r["unit_refs"]


def test_reveal_map_in_test_builds_only(tmp_path):
    spec = {"name": "t", "missions": [{"id": "a", "map_size": 40}, {"id": "b", "map_size": 40, "reveal_map": "explored"}]}
    test = compile_campaign(spec, out_dir=tmp_path / "test", test_mode=True, render=False)
    rel = compile_campaign(spec, out_dir=tmp_path / "rel", render=False)
    eff = _effects(_built(test, 0), "Reveal Map (test)")[0]
    assert eff["tribute_list"] == 203 and eff["quantity"] == 2
    assert _effects(_built(test, 1), "Reveal Map (test)")[0]["quantity"] == 1  # mission setting wins
    assert "Reveal Map (test)" not in [t.name for t in _built(rel, 0).trigger_manager.triggers]
    assert _effects(_built(rel, 1), "Reveal Map (test)")[0]["quantity"] == 1
    off = compile_campaign({**spec, "test_mode": {"reveal_map": False}}, out_dir=tmp_path / "off",
                           test_mode=True, render=False)
    assert "Reveal Map (test)" not in [t.name for t in _built(off, 0).trigger_manager.triggers]


def test_defaults_deep_merge_players(tmp_path):
    spec = {"name": "t", "defaults": {"players": {2: {"civilization": "MAGYARS"}}},
            "missions": [{"id": "a", "map_size": 40, "players": {"2": {"starting_age": "CASTLE"}}}]}
    rep = compile_campaign(spec, out_dir=tmp_path, render=False)
    p2 = _built(rep).player_manager.players[2]
    assert p2.civilization.name == "MAGYARS" and p2.starting_age.name == "CASTLE_AGE"
    assert not any("player 2 civilization" in w for w in rep["warnings"])


def test_random_faction_block(tmp_path):
    o = SESSIONS.new(40)
    ctx = B.Ctx(o.scenario)
    r = B.random_faction(ctx, store_key="faction", factions=[
        {"name": "A", "civ_name": "Ayy", "disable_units": ["KNIGHT"], "train": [{"unit": "BERSERK", "at": "BARRACKS"}],
         "free_techs": ["LOOM"]},
        {"name": "B", "effects": [{"type": "send_chat", "source_player": 1, "message": "b"}]}])
    s = o.scenario
    assert r["triggers"] == ["Faction Load", "Faction Roll", "Faction 1", "Faction 2"]
    roll = T.trigger_to_dict(T.find_trigger(s, "Faction Roll"))
    assert "xsGetRandomNumberLH(1, 3)" in roll["effects"][0]["message"]
    assert [c["type"] for c in roll["conditions"]] == ["timer", "variable_value"]
    f1 = [e["type"] for e in _effects(s, "Faction 1")]
    assert f1[:3] == ["store_key_value", "change_civilization_name", "enable_disable_object"]
    assert {"add_train_location", "research_technology", "display_instructions"} <= set(f1)


def test_factions_example_compiles(tmp_path):
    rep = compile_campaign(Path(__file__).parents[1] / "examples" / "factions" / "campaign.yaml",
                           out_dir=tmp_path, test_mode=True, render=False)
    assert rep["ok"] and rep["warnings"] == [] and len(rep["missions"]) == 2


def test_defeat_default_size_names_and_release_telemetry(tmp_path):
    spec = {"name": "t", "missions": [{
        "id": "m", "map": {"size": "small", "seed": 1, "players": 1, "extra_players": 1},
        "blocks": [{"use": "lose_if_destroyed", "unit_type": "TOWN_CENTER"}],
        "telemetry": True}]}
    rel = compile_campaign(spec, out_dir=tmp_path / "rel", render=False)
    s = _built(rel)
    assert s.map_manager.map_size == 144
    eff = _effects(s, "Core Lost")[0]
    assert eff["type"] == "declare_victory" and eff["source_player"] == 2
    assert rel["missions"][0]["telemetry"] is None  # release build: no telemetry
    test = compile_campaign(spec, out_dir=tmp_path / "test", test_mode=True, render=False)
    assert test["missions"][0]["telemetry"] is not None
    keep = {**spec, "missions": [{**spec["missions"][0], "telemetry": {"release": True}}]}
    assert compile_campaign(keep, out_dir=tmp_path / "keep", render=False)["missions"][0]["telemetry"]
    with pytest.raises(CompileError, match="Unknown map size 'huge'"):
        compile_campaign({**spec, "missions": [{**spec["missions"][0], "map": {"size": "huge"}}]},
                         out_dir=tmp_path / "bad", render=False)
