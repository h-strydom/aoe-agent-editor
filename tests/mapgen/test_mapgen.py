import pytest

from aoe2ed._parser import AoE2DEScenario
from aoe2ed.mapgen import (
    ElevationSpec,
    ForestSpec,
    MapSpec,
    PlayerStart,
    ResourceSpec,
    RoadSpec,
    UnitPlacement,
    WaterSpec,
    ZoneSpec,
    build_canvas,
    compass,
    generate,
)
from aoe2ed.mapgen.canvas import WATER
from aoe2ed.mapgen.names import unit_id
from aoe2ed.mapgen.steps import DEFAULT_PIPELINE

SPAWNS = {"north": "n", "east": "e", "south": "s", "west": "w"}


def survival_spec(seed=45, size=96) -> MapSpec:
    zones = [ZoneSpec(f"spawn_{n}", kind="edge", side=d, depth=8) for n, d in SPAWNS.items()]
    zones += [ZoneSpec(f"choke_{n}", kind="choke", between=[f"spawn_{n}", "center"], gap=5, wall_length=12)
              for n in SPAWNS]
    return MapSpec(
        size=size, seed=seed, biome="pine",
        players=[PlayerStart(base_radius=10)], player_layout="center", extra_players=1,
        forests=ForestSpec(coverage=0.22, clumps=10, border=3),
        resources=ResourceSpec(gold=[7, 4], stone=[5], neutral_gold=[5]),
        water=[WaterSpec(kind="lake", name="lake", radius=5, fish=3),
               WaterSpec(kind="river", start="nw", end="sw", width=3, fords=2)],
        elevation=ElevationSpec(hills=3),
        roads=[RoadSpec([f"spawn_{n}", "player1"], width=2) for n in SPAWNS],
        zones=zones,
    )


def snapshot(ctx):
    c = ctx.canvas
    return (list(c.terrain), list(c.elevation), [(u.player, u.unit_const, u.x, u.y) for u in c.units],
            dict(ctx.areas))


def test_same_seed_same_map():
    assert snapshot(build_canvas(survival_spec())) == snapshot(build_canvas(survival_spec()))


def test_different_seed_different_map():
    assert snapshot(build_canvas(survival_spec(seed=1))) != snapshot(build_canvas(survival_spec(seed=2)))


def test_steps_have_independent_rngs():
    # Dropping a step that has nothing to do must not change what the other steps produce.
    spec = survival_spec()
    full = snapshot(build_canvas(spec))
    without_cliffs = snapshot(build_canvas(spec, [s for s in DEFAULT_PIPELINE if s != "cliffs"]))
    assert full == without_cliffs


def test_units_and_areas_inside_map():
    ctx = build_canvas(survival_spec())
    n = ctx.size
    for u in ctx.canvas.units:
        assert 0 <= u.x < n and 0 <= u.y < n
    for name, (x1, y1, x2, y2) in ctx.areas.items():
        assert 0 <= x1 <= x2 < n and 0 <= y1 <= y2 < n, name


def test_named_areas():
    ctx = build_canvas(survival_spec())
    a = ctx.areas
    for name in ["player1_base", "lake", "river_2", "river_2_ford_1", "hill_1"] + \
            [f"spawn_{n}" for n in SPAWNS] + [f"choke_{n}" for n in SPAWNS]:
        assert name in a, name
    n = ctx.size
    # Each spawn touches the map corner its compass direction names.
    for name, d in SPAWNS.items():
        cx, cy = compass.edge_point(d, n)
        x1, y1, x2, y2 = a[f"spawn_{name}"]
        assert x1 <= cx <= x2 and y1 <= cy <= y2, name
    # The base area is centered on the town center.
    tc = [u for u in ctx.canvas.units if u.unit_const == unit_id("TOWN_CENTER")]
    assert len(tc) == 1
    x1, y1, x2, y2 = a["player1_base"]
    assert x1 < tc[0].x < x2 and y1 < tc[0].y < y2


def test_compass_convention():
    n = 100
    assert compass.edge_point("w", n, 0) == (0, 0)
    assert compass.edge_point("n", n, 0) == (99, 0)
    assert compass.edge_point("e", n, 0) == (99, 99)
    assert compass.edge_point("s", n, 0) == (0, 99)
    assert compass.edge_point("north", n, 4) == (95, 4)


def test_elevation_is_smooth_and_water_is_flat():
    ctx = build_canvas(survival_spec())
    c, n = ctx.canvas, ctx.size
    assert max(c.elevation) > 0
    for y in range(n):
        for x in range(n):
            e = c.elevation[c.i(x, y)]
            if c.has(x, y, WATER):
                assert e == 0
            for nx, ny in c.neighbors(x, y, diagonal=True):
                assert abs(e - c.elevation[c.i(nx, ny)]) <= 1


def test_resources_per_player():
    spec = MapSpec(size=80, seed=5, players=2, resources=ResourceSpec(gold=[7, 4], stone=[5], berries=6,
                                                                       sheep=4, deer=0))
    ctx = build_canvas(spec)
    count = lambda name: sum(1 for u in ctx.canvas.units if u.unit_const == unit_id(name))  # noqa: E731
    assert count("GOLD_MINE") == 2 * 11
    assert count("STONE_MINE") == 2 * 5
    assert count("FORAGE_BUSH") == 2 * 6
    assert count("TOWN_CENTER") == 2
    assert {u.player for u in ctx.canvas.units if u.unit_const == unit_id("SHEEP")} == {1, 2}


def test_no_two_objects_on_one_tile():
    ctx = build_canvas(survival_spec())
    tiles = [(int(u.x), int(u.y)) for u in ctx.canvas.units
             if u.unit_const not in (unit_id("TOWN_CENTER"), unit_id("FISH_PERCH"))]
    assert len(tiles) == len(set(tiles))


def test_explicit_units_and_plaza():
    spec = MapSpec(size=60, seed=3, players=[PlayerStart(position="center", town_center=False, villagers=0,
                                                         scout=False)],
                   zones=[ZoneSpec("hub_plaza", kind="circle", center="center", radius=5, terrain="ROAD")],
                   units=[UnitPlacement("MARKET", "hub_plaza", player=1, offset=(0, 9))],
                   forests=ForestSpec(border=4), resources=ResourceSpec(gold=[], stone=[], berries=0, sheep=0,
                                                                         deer=0))
    ctx = build_canvas(spec)
    markets = [u for u in ctx.canvas.units if u.unit_const == unit_id("MARKET")]
    assert len(markets) == 1 and markets[0].player == 1
    cx, cy = ctx.point("hub_plaza")
    assert ctx.canvas.terrain[ctx.canvas.i(cx, cy)] == 24  # ROAD


def test_from_dict_and_unknown_keys():
    spec = MapSpec.from_dict({"size": 72, "seed": 9, "players": 1,
                              "forests": {"coverage": 0.1},
                              "zones": [{"name": "spawn_north", "kind": "edge", "side": "north"}],
                              "water": [{"kind": "lake", "radius": 4}]})
    assert isinstance(spec.forests, ForestSpec) and spec.forests.coverage == 0.1
    assert spec.zones[0].side == "north" and isinstance(spec.water[0], WaterSpec)
    with pytest.raises(ValueError, match="unknown keys"):
        MapSpec.from_dict({"size": 72, "forest": {}})
    with pytest.raises(ValueError, match="unknown keys"):
        MapSpec.from_dict({"forests": {"density": 1}})


def test_bad_point_reference():
    spec = MapSpec(size=60, players=1, roads=[RoadSpec(["nowhere", "center"])])
    with pytest.raises(ValueError, match="Unknown point"):
        build_canvas(spec)


def test_generate_writes_scenario_that_reloads(tmp_path):
    spec = survival_spec(size=72)
    m = generate(spec)
    path = m.save(tmp_path / "survival.aoe2scenario")
    back = AoE2DEScenario.from_file(path)
    assert back.map_manager.map_size == 72
    assert len(back.unit_manager.get_all_units()) == len(m.canvas.units)
    assert back.player_manager.active_players == 2
    terrain = [t.terrain_id for t in back.map_manager.terrain]
    assert terrain == m.canvas.terrain
    png = m.render(tmp_path / "survival.png")
    assert (tmp_path / "survival.png").exists() and png.size[0] > 72
