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
