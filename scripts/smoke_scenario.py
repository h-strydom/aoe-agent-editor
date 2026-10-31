"""Build a short scenario that exercises every block once, for in-game verification.

    uv run python scripts/smoke_scenario.py [--install] [--game ror]

Play it (Single Player > Scenario > aoe2ed_smoke; for --game ror start Return of Rome and pick
aoe2ed_smoke_ror). Expected within ~2.5 minutes:
  t=0   chat "aoe2ed smoke: XS running", countdown timer, objective line
  t=20  wave 1 from the north attack-moves to the Town Center
  t=30  decision popup: two boons
  t=50  wave 2 from the south
  t=120 "You survived!", chat with earnings, victory ~8 s later
The map is revealed. Afterwards `aoe2ed call xsdat_list '{}'` should show the telemetry file.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from aoe2ed import blocks as B
from aoe2ed.session import SESSIONS
from aoe2ed.tools import load_all

OUT = Path(__file__).resolve().parent.parent / "out"

# Unit and civ names per game: Return of Rome has its own (many AoE2 ids mean other units there).
ROSTER = {
    "aoe2": {"civ1": "BRITONS", "civ2": "GOTHS", "ranged": "ARCHER", "melee": "MAN_AT_ARMS",
             "wave1": {"MILITIA": 3}, "wave2": {"MILITIA": 2, "SPEARMAN": 2}},
    "ror": {"civ1": "EGYPTIANS", "civ2": "GREEKS", "ranged": "BOWMAN", "melee": "SHORT_SWORDSMAN",
            "wave1": {"CLUBMAN": 3}, "wave2": {"CLUBMAN": 2, "SLINGER": 2}},
}


def build(game: str = "aoe2") -> str:
    r = ROSTER[game]
    tools = load_all()
    o = SESSIONS.new(60, game)
    h, s = o.handle, o.scenario
    tools["player_set"](handle=h, player=1, fields={"civilization": r["civ1"], "food": 500, "wood": 500,
                                                       "gold": 200, "stone": 0})
    tools["player_set"](handle=h, player=2, fields={"civilization": r["civ2"], "ai": "none", "human": False})
    tools["diplomacy_set"](handle=h, player=1, others=[2], state="ENEMY")
    tools["units_add"](handle=h, units=[
        {"player": 1, "type": "TOWN_CENTER", "x": 30, "y": 30},
        *[{"player": 1, "type": "VILLAGER_MALE", "x": 26 + i, "y": 34} for i in range(4)],
        *[{"player": 1, "type": r["ranged"], "x": 27 + i, "y": 26} for i in range(5)],
        {"player": 1, "type": r["melee"], "x": 33, "y": 26},
    ])
    tools["messages_set"](handle=h, fields={"instructions": f"aoe2ed smoke test ({game}): survive 2 minutes."})
    tools["options_set"](handle=h, fields={"victory_condition": "CUSTOM"})

    ctx = B.Ctx(s, areas={"north": (26, 1, 34, 3), "south": (26, 56, 34, 58)}, points={"core": (30, 30)})
    ctx.xs('rule aoe2edSmokeHello active highFrequency { xsChatData("aoe2ed smoke: XS running"); xsDisableSelf(); }')
    ctx.trigger("Reveal Map (test)", [], [{"type": "modify_resource", "tribute_list": "REVEAL_MAP",
                                           "source_player": 1, "quantity": 2, "operation": "SET"}])
    B.anchor(ctx, player=2, at=(1, 1))  # player 2 has no army until wave 1
    B.bank_load(ctx, {"meta_points": 0, "heat": 0})
    sv = B.survive(ctx, 2, on_complete=[])
    B.waves(ctx, spawns=["north", "south"], target="core", on_wave=[B.earn("earned", 5)],
            waves=[{"at": 20, "units": r["wave1"]}, {"at": 50, "units": r["wave2"]}])
    B.boon_offers(ctx, offers=[{"at": 30, "pairs": [["gold", "hp"]]}], boons={
        "gold": {"label": "Plunder: +300 gold", "effects": [
            {"type": "modify_resource", "tribute_list": "GOLD_STORAGE", "quantity": 300, "operation": "ADD",
             "source_player": 1}]},
        "hp": {"label": f"Fortify: +15 {r['ranged'].lower()} HP", "effects": [
            {"type": "modify_attribute", "object_list_unit_id": r["ranged"], "source_player": 1,
             "object_attributes": "HIT_POINTS", "operation": "ADD", "quantity": 15}]}})
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
    ap.add_argument("--game", choices=["aoe2", "ror"], default="aoe2")
    a = ap.parse_args()
    h = build(a.game)
    out = OUT / ("aoe2ed_smoke.aoe2scenario" if a.game == "aoe2" else "aoe2ed_smoke_ror.aoe2scenario")
    print(SESSIONS.save(h, out, overwrite=True))
    if a.install:
        from aoe2ed.game import install
        print(install(out))


if __name__ == "__main__":
    main()
