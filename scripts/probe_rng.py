"""Probe: is XS randomness different between fresh starts (campaign vs standalone scenario)?

    uv run python scripts/probe_rng.py --install

Installs the scenario `aoe2ed_probe_rng` and the campaign `aoe2ed_rng` (same scenario). At start XS
shows five xsGetRandomNumber() values and xsGetMapSeed() in chat and writes them to the .xsdat
(aoe2ed_probe_rng.xsdat standalone, aoe2ed_rng.xsdat in the campaign). Play each twice with a full
quit in between and compare.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from aoe2ed import blocks as B
from aoe2ed.campaign import Campaign
from aoe2ed.session import SESSIONS
from aoe2ed.tools import load_all

OUT = Path(__file__).resolve().parent.parent / "out" / "aoe2ed_probe_rng.aoe2scenario"


def build() -> str:
    tools = load_all()
    o = SESSIONS.new(40)
    h, s = o.handle, o.scenario
    tools["player_set"](handle=h, player=1, fields={"civilization": "FRANKS"})
    tools["player_set"](handle=h, player=2, fields={"civilization": "GOTHS", "ai": "none", "human": False})
    tools["units_add"](handle=h, units=[{"player": 1, "type": "TOWN_CENTER", "x": 10, "y": 10},
                                        {"player": 2, "type": "TOWN_CENTER", "x": 30, "y": 30}])
    tools["options_set"](handle=h, fields={"victory_condition": "CUSTOM"})
    ctx = B.Ctx(s)
    ctx.xs("""rule aoe2edProbeRng
    active
    highFrequency
{
    xsCreateFile(false);
    for (i = 0; < 5) {
        int r = xsGetRandomNumber();
        xsChatData("random: %d", r);
        xsWriteInt(r);
    }
    xsChatData("map seed: %d", xsGetMapSeed());
    xsWriteInt(xsGetMapSeed());
    xsCloseFile();
    xsDisableSelf();
}""")
    ctx.flush_xs()
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    h = build()
    print(SESSIONS.save(h, OUT, overwrite=True))
    if a.install:
        from aoe2ed.config import paths
        from aoe2ed.game import install
        print(install(OUT))
        camp = Campaign("aoe2ed_rng")
        camp.add_scenario_file(OUT)
        print(camp.write(paths().user_dir("campaign") / "aoe2ed_rng.aoe2campaign"))


if __name__ == "__main__":
    main()
