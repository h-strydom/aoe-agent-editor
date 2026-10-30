"""Blocks compose into a working Crucible-style run and hub; checked after save + reload."""
from __future__ import annotations

from aoe2ed import blocks as B
from aoe2ed import telemetry
from aoe2ed import triggers as T
from aoe2ed.session import SESSIONS
from aoe2ed.xs import check


def _reload(o, tmp_path, name):
    p = tmp_path / name
    SESSIONS.save(o.handle, p, overwrite=True)
    return SESSIONS.open(p).scenario


def _names(s):
    return [t.name for t in s.trigger_manager.triggers]


def _all_xs(s) -> str:
    return "\n".join(e.message for t in s.trigger_manager.triggers for e in t.effects if e.effect_type == 55)


def test_run_mission(tmp_path):
    o = SESSIONS.new(120)
    ctx = B.Ctx(o.scenario, areas={"north": (55, 0, 65, 5), "south": (55, 114, 65, 119)},
                points={"core": (60, 60)}, time_scale=0.1)
    o.scenario.unit_manager.add_unit(1, 276, 60.5, 60.5)  # WONDER
    B.bank_load(ctx, {"meta_points": {"var": "meta_points"}, "perk_eco": 0, "heat": 0})
    B.perk_effects(ctx, var="perk_eco", levels={1: [{"type": "modify_resource", "tribute_list": "FOOD_STORAGE",
                                                     "quantity": 100, "operation": "ADD", "source_player": 1}]})
    sv = B.survive(ctx, 45, on_complete=[])
    wl = B.escalating(45, pools=[{"from_min": 0, "units": ["MILITIA"]}, {"from_min": 20, "units": ["KNIGHT"]}])
    B.waves(ctx, spawns=["north", "south"], target="core", waves=wl, scale_var="heat",
            scale_extra={"MAN_AT_ARMS": 2}, scale_max=2, on_wave=[B.earn("earned", 5)])
    B.boon_offers(ctx, boons={"a": {"label": "A", "effects": []}, "b": {"label": "B", "effects": []},
                              "c": {"label": "C", "effects": []}},
                  offers=[{"at": 600, "pairs": [["a", "b"], ["b", "c"]]}])
    B.run_end(ctx, success_trigger=sv["complete_trigger"], success_bonus=50,
              fail_conditions=[{"type": "own_fewer_objects", "source_player": 1, "object_list": "WONDER",
                                "quantity": 0}])
    B.telemetry_harness(ctx, track_vars=["meta_points", "earned"], events={"Run End": 1})
    ctx.flush_xs()

    s = _reload(o, tmp_path, "run.aoe2scenario")
    names = _names(s)
    assert {"Bank Load", "Survive Objective", "Wave 1", "Wave 1 +2", "Run End", "Boon 1 roll"} <= set(names)
    obj = T.trigger_to_dict(T.find_trigger(s, "Survive Objective"))
    assert obj["conditions"][0]["timer"] == 270  # 45 min * 60 * 0.1
    complete = T.trigger_to_dict(T.find_trigger(s, "Survive Complete"))
    assert complete["effects"][-1]["trigger_id"] == T.find_trigger(s, "Run Success").trigger_id
    assert len([n for n in names if n.startswith("Wave ") and "+" not in n and "Keepalive" not in n]) == len(wl)
    xs = _all_xs(s)
    assert "aoe2edTelemetrySample" in xs and "aoe2edPickBoon1" in xs
    r = check(code=xs)
    assert r["ok"], r["diagnostics"]


def test_hub_shop(tmp_path):
    o = SESSIONS.new(60)
    ctx = B.Ctx(o.scenario, areas={"pad_eco": (20, 20, 22, 22), "pad_war": (30, 20, 32, 22)},
                points={"plaza": (26, 30)})
    B.bank_load(ctx, {"meta_points": 0, "perk_eco": 0, "perk_war": 0})
    ctx.trigger("Gold from meta", [], [B.var_to_resource("meta_points")])
    B.pad_shop(ctx, exit_point="plaza", perks=[
        {"key": "perk_eco", "label": "Eager Hands", "pad": "pad_eco", "costs": [100, 250]},
        {"key": "perk_war", "label": "Drilled", "pad": "pad_war", "costs": [150]}])
    B.bank_store(ctx, {"meta_points": "meta_points"}, conditions=[{"type": "timer", "timer": 5}], enabled=True)
    s = _reload(o, tmp_path, "hub.aoe2scenario")
    lvl2 = T.trigger_to_dict(T.find_trigger(s, "Shop perk_eco L2"), verbose=True)
    assert lvl2["looping"] is True
    conds = {c["type"]: c for c in lvl2["conditions"]}
    assert conds["accumulate_attribute"]["quantity"] == 250
    assert conds["variable_value"]["quantity"] == 1
    assert [e["type"] for e in lvl2["effects"]][:3] == ["modify_resource", "change_variable", "store_key_value"]
    captions = [u.caption_string for u in s.unit_manager.get_player_units(0)]
    assert "Eager Hands (100/250)" in captions


def test_telemetry_decode():
    import struct
    vals = [telemetry.MAGIC, 1, 1, 1, 1, 7, 1, 10, 200, 100, 300, 50, 5, 2, 3, 42, 2, 12, 9]
    d = telemetry.decode(struct.pack(f"<{len(vals)}i", *vals), var_names={7: "meta"}, event_names={9: "end"})
    assert d["last"]["players"][1]["gold"] == 300 and d["last"]["vars"]["meta"] == 42
    assert d["events"] == [{"t": 12, "event": "end"}]


def test_anchor(tmp_path):
    o = SESSIONS.new(40)
    ctx = B.Ctx(o.scenario)
    r = B.anchor(ctx, player=2, at=(1, 1))
    s = _reload(o, tmp_path, "anchor.aoe2scenario")
    assert [u.reference_id for u in s.unit_manager.get_player_units(2)] == [r["unit_ref"]]
    effects = T.trigger_to_dict(T.find_trigger(s, "Anchor P2"))["effects"]
    assert {e["type"] for e in effects} == {"disable_unit_attackable", "disable_unit_targeting",
                                            "disable_object_selection"}
    assert all(e["selected_object_ids"] == [r["unit_ref"]] for e in effects)


def test_spawn_distinct_tiles():
    o = SESSIONS.new(60)
    ctx = B.Ctx(o.scenario, points={"tc": (30, 30)})
    effs = B.spawn(ctx, unit="MAN_AT_ARMS", count=8, at="tc", min_dist=4)
    locs = [tuple(e["location"]) for e in effs]
    assert len(locs) == 8 and len(set(locs)) == 8
    assert all(((x - 30) ** 2 + (y - 30) ** 2) ** 0.5 >= 4 for x, y in locs)
