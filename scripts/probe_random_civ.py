"""Probe: what does the game do with a Random civilization in a scenario?

    uv run python scripts/probe_random_civ.py --install

Builds `aoe2ed_probe_civ`: player 1 = RANDOM, player 2 = FULL_RANDOM. On start, XS prints each
player's civilization (id and name) in chat and writes them to aoe2ed_probe_civ.xsdat as
[p1_civ, p2_civ]. A trigger also spawns a civ-specific unit (LONGBOWMAN) for player 1, to see
whether unique units can be created for whatever civ was rolled. The map is revealed.
Play it twice and compare: does the civ change between plays? Do architecture, the unit and the
tech tree match the rolled civ?
"""
from __future__ import annotations

import argparse
from pathlib import Path

from aoe2ed import blocks as B
from aoe2ed.session import SESSIONS
from aoe2ed.tools import load_all

OUT = Path(__file__).resolve().parent.parent / "out" / "aoe2ed_probe_civ.aoe2scenario"


def build() -> str:
    tools = load_all()
    o = SESSIONS.new(60)
    h, s = o.handle, o.scenario
    tools["player_set"](handle=h, player=1, fields={"civilization": "RANDOM", "food": 500, "wood": 500,
                                                       "gold": 500, "stone": 500})
    tools["player_set"](handle=h, player=2, fields={"civilization": "FULL_RANDOM", "ai": "none"})
    tools["diplomacy_set"](handle=h, player=1, others=[2], state="ENEMY")
    tools["units_add"](handle=h, units=[
        {"player": 1, "type": "TOWN_CENTER", "x": 20, "y": 20},
        *[{"player": 1, "type": "VILLAGER_MALE", "x": 16 + i, "y": 25} for i in range(3)],
        {"player": 2, "type": "TOWN_CENTER", "x": 45, "y": 45},
    ])
    tools["options_set"](handle=h, fields={"victory_condition": "CUSTOM"})
    ctx = B.Ctx(s, points={"p1": (24, 24)})
    ctx.xs("""rule aoe2edProbeCiv
    active
    highFrequency
{
    int c1 = xsGetPlayerCivilization(1);
    int c2 = xsGetPlayerCivilization(2);
    xsChatData("P1 civ id: %d", c1);
    xsChatData("P1 civ: " + xsGetPlayerCivName(1, true));
    xsChatData("P2 civ id: %d", c2);
    xsChatData("P2 civ: " + xsGetPlayerCivName(2, true));
    xsCreateFile(false);
    xsWriteInt(c1);
    xsWriteInt(c2);
    xsCloseFile();
    xsDisableSelf();
}""")
    ctx.trigger("Probe Unique Unit", [{"type": "timer", "timer": 3}], [
        {"type": "create_object", "object_list_unit_id": "LONGBOWMAN", "source_player": 1, "location": [24, 24]},
        {"type": "display_instructions", "source_player": 1, "display_time": 15, "instruction_panel_position": 0,
         "message": "Probe: a Longbowman should appear next to your Town Center whatever civ you rolled."}])
    ctx.trigger("Reveal Map (test)", [], [{"type": "modify_resource", "tribute_list": "REVEAL_MAP",
                                           "source_player": 1, "quantity": 2, "operation": "SET"}])
    ctx.flush_xs()
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    h = build()
    print(SESSIONS.save(h, OUT, overwrite=True))
    if a.install:
        from aoe2ed.game import install
        print(install(OUT))


if __name__ == "__main__":
    main()
