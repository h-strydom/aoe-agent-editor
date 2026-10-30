"""The Crucible example compiles into a working two-mission campaign."""
from __future__ import annotations

import json
from pathlib import Path

from aoe2ed.campaign import Campaign
from aoe2ed.compiler import compile_campaign
from aoe2ed.session import SESSIONS
from aoe2ed import triggers as T

SPEC = Path(__file__).parents[1] / "examples" / "crucible" / "campaign.yaml"


def test_crucible_compiles(tmp_path):
    rep = compile_campaign(SPEC, out_dir=tmp_path, test_mode=True, render=False)
    assert rep["ok"], [m["xs_errors"] for m in rep["missions"]]
    camp = Campaign.read(rep["campaign"])
    assert camp.name == "crucible" and len(camp.scenarios) == 2
    hub, run = rep["missions"]
    assert {"pad_eco", "exit_gate", "hub_plaza"} <= set(hub["areas"])
    assert {"spawn_north", "player1_base"} <= set(run["areas"])
    assert run["telemetry"]["var_names"]
    s = SESSIONS.open(run["scenario"]).scenario
    obj = T.trigger_to_dict(T.find_trigger(s, "Survive Objective"))
    assert obj["conditions"][0]["timer"] == 270          # 45 min scaled x0.1
    heat = T.trigger_to_dict(T.find_trigger(s, "Heat pay 1"))
    assert heat["conditions"][0]["timer"] == 269          # $secs scaled too
    assert json.loads((tmp_path / "build_report.json").read_text())["name"] == "crucible"


def test_unknown_block_message(tmp_path):
    import pytest
    spec = {"name": "x", "missions": [{"id": "m", "blocks": [{"use": "nope"}]}]}
    with pytest.raises(ValueError, match="unknown block 'nope'"):
        compile_campaign(spec, out_dir=tmp_path, render=False)


def test_crucible_spawns_on_distinct_tiles(tmp_path):
    rep = compile_campaign(SPEC, out_dir=tmp_path, render=False)
    s = SESSIONS.open(rep["missions"][1]["scenario"]).scenario
    for name in ("Perk perk_guard L1", "Boon 1 offer 0 pick reinforce"):
        effs = T.trigger_to_dict(T.find_trigger(s, name))["effects"]
        locs = [(e["location_x"], e["location_y"]) for e in effs if e["type"] == "create_object"]
        assert len(locs) >= 4 and len(set(locs)) == len(locs), name
