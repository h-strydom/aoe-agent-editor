"""Build a short scenario that exercises every block once, for in-game verification.

    uv run python scripts/smoke_scenario.py [--install]

Play it (Single Player > Scenario > aoe2ed_smoke). Expected within ~2.5 minutes:
  t=0   chat "aoe2ed smoke: XS running", countdown timer, objective line
  t=20  wave 1 (militia) from the north attack-moves to the Town Center
  t=30  decision popup: two boons
  t=50  wave 2 from the south
  t=120 "You survived!", chat with earnings, victory ~8 s later
Afterwards: `aoe2ed call xsdat_list '{}'` should show aoe2ed_smoke.xsdat (telemetry).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from aoe2ed import blocks as B
from aoe2ed.session import SESSIONS
from aoe2ed.tools import load_all

OUT = Path(__file__).resolve().parent.parent / "out" / "aoe2ed_smoke.aoe2scenario"


def build() -> str:
    tools = load_all()
    o = SESSIONS.new(60)
    h, s = o.handle, o.scenario
    tools["player_set"](handle=h, player=1, fields={"civilization": "BRITONS", "food": 500, "wood": 500,
                                                       "gold": 200, "stone": 0})
    tools["player_set"](handle=h, player=2, fields={"civilization": "GOTHS"})
    tools["diplomacy_set"](handle=h, player=1, others=[2], state="ENEMY")
    tools["units_add"](handle=h, units=[
        {"player": 1, "type": "TOWN_CENTER", "x": 30, "y": 30},
        *[{"player": 1, "type": "VILLAGER_MALE", "x": 26 + i, "y": 34} for i in range(4)],
        *[{"player": 1, "type": "ARCHER", "x": 27 + i, "y": 26} for i in range(5)],
        {"player": 1, "type": "MAN_AT_ARMS", "x": 33, "y": 26},
    ])
    tools["messages_set"](handle=h, fields={"instructions": "aoe2ed smoke test: survive 2 minutes."})
    tools["options_set"](handle=h, fields={"victory_condition": "CUSTOM"})

    ctx = B.Ctx(s, areas={"north": (26, 1, 34, 3), "south": (26, 56, 34, 58)}, points={"core": (30, 30)})
    ctx.xs('rule aoe2edSmokeHello active highFrequency { xsChatData("aoe2ed smoke: XS running"); xsDisableSelf(); }')
    B.anchor(ctx, player=2, at=(1, 1))  # player 2 has no army until wave 1
    B.bank_load(ctx, {"meta_points": 0, "heat": 0})
    sv = B.survive(ctx, 2, on_complete=[])
    B.waves(ctx, spawns=["north", "south"], target="core", on_wave=[B.earn("earned", 5)],
            waves=[{"at": 20, "units": {"MILITIA": 3}}, {"at": 50, "units": {"MILITIA": 2, "SPEARMAN": 2}}])
    B.boon_offers(ctx, offers=[{"at": 30, "pairs": [["gold", "hp"]]}], boons={
        "gold": {"label": "Plunder: +300 gold", "effects": [
            {"type": "modify_resource", "tribute_list": "GOLD_STORAGE", "quantity": 300, "operation": "ADD",
             "source_player": 1}]},
        "hp": {"label": "Fortify: +50% archer HP", "effects": [
            {"type": "modify_attribute", "object_list_unit_id": "ARCHER", "source_player": 1,
             "object_attributes": "HIT_POINTS", "operation": "MULTIPLY", "quantity": 1.5}]}})
    B.run_end(ctx, success_trigger=sv["complete_trigger"], success_bonus=10,
              fail_conditions=[{"type": "own_fewer_objects", "source_player": 1, "object_list": "TOWN_CENTER",
                                "quantity": 0}])
    B.telemetry_harness(ctx, players=[1, 2], track_vars=["meta_points", "earned", "boon_pick_1"],
                        interval_sec=5, events={"Wave 1": 1, "Wave 2": 2, "Run End": 3})
    ctx.flush_xs()
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true", help="also copy into the game's scenario folder")
    a = ap.parse_args()
    h = build()
    print(SESSIONS.save(h, OUT, overwrite=True))
    if a.install:
        from aoe2ed.game import install
        print(install(OUT))


if __name__ == "__main__":
    main()
