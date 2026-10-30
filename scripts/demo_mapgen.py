"""Generate three example maps and save each as .aoe2scenario plus .png previews.

    PYTHONPATH=src python scripts/demo_mapgen.py [out_dir]   (default: out/mapgen)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aoe2ed._parser import AoE2DEScenario  # noqa: E402  (configures the parser quietly)
from aoe2ed.mapgen import (ElevationSpec, ForestSpec, MapSpec, PlayerStart, ResourceSpec,  # noqa: E402
                           RoadSpec, UnitPlacement, WaterSpec, ZoneSpec, generate)

SPAWNS = {"north": "n", "east": "e", "south": "s", "west": "w"}


def survival() -> MapSpec:
    """45-minute survival: player base in the center, enemies arrive from 4 corner spawns
    along roads that pass through forest choke points."""
    zones = [ZoneSpec(f"spawn_{name}", kind="edge", side=d, depth=12) for name, d in SPAWNS.items()]
    zones += [ZoneSpec(f"choke_{name}", kind="choke", between=[f"spawn_{name}", "center"], at=0.45,
                       gap=7, wall_length=20) for name in SPAWNS]
    zones.append(ZoneSpec("inner_ring", kind="circle", center="center", radius=22, clear=False, flat=True))
    return MapSpec(
        size=144, seed=45, biome="pine",
        players=[PlayerStart(base_radius=13, villagers=6)], player_layout="center", extra_players=1,
        forests=ForestSpec(coverage=0.26, clumps=22, border=4, player_woodlines=3, stragglers=4),
        resources=ResourceSpec(gold=[8, 6, 5], stone=[6, 5], berries=8, sheep=6, deer=4,
                               neutral_gold=[6, 6, 5], neutral_stone=[5, 5]),
        water=[WaterSpec(kind="lake", name="lake_west", radius=7, fish=5),
               WaterSpec(kind="lake", name="lake_east", radius=6, fish=4)],
        elevation=ElevationSpec(hills=6, height=(2, 4), radius=(6, 11)),
        roads=[RoadSpec([f"spawn_{name}", "player1"], width=3, wobble=1.0) for name in SPAWNS],
        zones=zones,
    )


def hub_town() -> MapSpec:
    """Small hub town: a plaza with shops around it, exits on the four edges, forest ring."""
    exits = {"exit_northeast": "ne", "exit_southeast": "se", "exit_southwest": "sw", "exit_northwest": "nw"}
    buildings = [("MARKET", (0, 11)), ("BLACKSMITH", (11, 0)), ("MONASTERY", (-11, 0)),
                 ("UNIVERSITY", (0, -11)), ("HOUSE", (8, 8)), ("HOUSE", (-8, 8)),
                 ("HOUSE", (8, -8)), ("HOUSE", (-8, -8)), ("BARRACKS", (14, 14)), ("STABLE", (-14, -14))]
    return MapSpec(
        size=72, seed=3, biome="autumn",
        players=[PlayerStart(position="center", base_radius=16, town_center=False, villagers=1, scout=False)],
        forests=ForestSpec(coverage=0.22, clumps=6, border=6, player_woodlines=0, stragglers=0),
        resources=ResourceSpec(gold=[], stone=[], berries=0, sheep=0, deer=0),
        water=[WaterSpec(kind="lake", name="town_pond", center=[52, 20], radius=4, fish=2)],
        elevation=ElevationSpec(hills=2, height=(1, 2), radius=(4, 6)),
        zones=[ZoneSpec("hub_plaza", kind="circle", center="center", radius=6, terrain="ROAD", flat=True)]
        + [ZoneSpec(name, kind="edge", side=d, width=8, depth=5) for name, d in exits.items()],
        roads=[RoadSpec(["hub_plaza", name], width=3, wobble=0.6) for name in exits],
        units=[UnitPlacement(b, "hub_plaza", player=1, offset=off) for b, off in buildings],
    )


def land_2p() -> MapSpec:
    """Open two-player land map with hills, a pond and contested gold in the middle."""
    return MapSpec(
        size=120, seed=1337, biome="temperate", players=2,
        forests=ForestSpec(coverage=0.17, clumps=14),
        resources=ResourceSpec(neutral_gold=[5, 5], neutral_stone=[4]),
        water=[WaterSpec(kind="lake", name="pond", radius=5, fish=3)],
        elevation=ElevationSpec(hills=5),
    )


def main(out_dir: str = "out/mapgen") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, spec in (("survival_45min", survival()), ("hub_town", hub_town()), ("land_2p", land_2p())):
        m = generate(spec)
        path = m.save(out / f"{name}.aoe2scenario")
        m.render(out / f"{name}.png", title=f"{name}  seed={spec.seed}  size={spec.size}")
        m.render(out / f"{name}_diamond.png", orientation="diamond", show_areas=None)
        back = AoE2DEScenario.from_file(path)  # round-trip check
        assert back.map_manager.map_size == spec.size
        print(f"{name}: {path}  units={len(back.unit_manager.get_all_units())}  areas={sorted(m.areas)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
