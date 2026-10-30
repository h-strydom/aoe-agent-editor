from pathlib import Path

import pytest
from AoE2ScenarioParser.datasets.terrains import TerrainId

from aoe2ed._parser import AoE2DEScenario
from aoe2ed.mapgen import MapSpec, generate
from aoe2ed.render import TERRAIN_COLORS, object_class, render_scenario, trigger_areas
from aoe2ed.render.colors import GOLD_COLOR, TREE_COLOR

SIEGE = Path(__file__).resolve().parents[1] / "fixtures" / "siege.aoe2scenario"


@pytest.fixture(scope="module")
def small_map():
    return generate(MapSpec(size=60, seed=11, players=2))


def test_every_terrain_has_a_color():
    missing = [t.name for t in TerrainId if int(t) not in TERRAIN_COLORS]
    assert not missing


def test_object_classes():
    assert object_class(66) == "gold"
    assert object_class(102) == "stone"
    assert object_class(59) == "food"
    assert object_class(411) == "tree"
    assert object_class(109) == "building"
    assert object_class(83) == "unit"
    assert object_class(65) == "food_animal"


def test_render_square_writes_png(small_map, tmp_path):
    out = tmp_path / "map.png"
    img = render_scenario(small_map.scenario, out, scale=6, show_areas=small_map.areas)
    assert out.exists()
    assert img.size == (60 * 6 + 80, 60 * 6 + 80)
    # Tree tiles are drawn dark green and gold mines yellow somewhere on the map.
    colors = {c for _, c in img.getcolors(1 << 20)}
    assert TREE_COLOR in colors and GOLD_COLOR in colors


def test_render_square_pixel_matches_tile(small_map):
    img = render_scenario(small_map.scenario, scale=4, show_units=False, show_elevation=False, grid=False)
    c = small_map.canvas
    x, y = 30, 7
    # Tile (x, y) covers pixels [m + 4x, m + 4x + 4) horizontally and the same for y (margin 40).
    px = img.getpixel((40 + 4 * x + 2, 40 + 4 * y + 2))
    assert px == TERRAIN_COLORS[c.terrain[c.i(x, y)]]


def test_render_diamond(small_map, tmp_path):
    img = render_scenario(small_map.scenario, tmp_path / "d.png", orientation="diamond", scale=6)
    w, h = img.size
    assert w > h  # 2:1 minimap shape plus margins


def test_bad_orientation(small_map):
    with pytest.raises(ValueError):
        render_scenario(small_map.scenario, orientation="iso")


def test_elevation_changes_shading():
    m = generate(MapSpec(size=48, seed=2, players=1, elevation={"hills": 0},
                         forests={"coverage": 0, "player_woodlines": 0, "stragglers": 0}))
    flat = render_scenario(m.scenario, scale=2, show_units=False, grid=False)
    for t in m.scenario.map_manager.terrain:
        if t.x > 30:
            t.elevation = 3
    hilly = render_scenario(m.scenario, scale=2, show_units=False, grid=False)
    assert list(flat.getdata()) != list(hilly.getdata())


def test_render_real_scenario_from_path_with_trigger_areas(tmp_path):
    out = tmp_path / "siege.png"
    render_scenario(str(SIEGE), out, scale=2, show_trigger_areas=True)
    assert out.exists()
    areas = trigger_areas(AoE2DEScenario.from_file(str(SIEGE)))
    assert areas and all(len(r) == 4 for r in areas.values())
