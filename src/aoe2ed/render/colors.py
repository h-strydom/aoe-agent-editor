"""Color tables for the renderer: terrain minimap colors, player colors, gaia object classes.

The terrain colors approximate each terrain's in-game minimap color. They are hand-tuned
rather than read from the game's data files, so treat them as "close enough to recognise".
"""
from __future__ import annotations

from functools import lru_cache

from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

RGB = tuple[int, int, int]

_GRASS = (51, 117, 50)
_GRASS_LIGHT = (75, 135, 55)
_GRASS_DRY = (120, 135, 60)
_DIRT = (155, 125, 75)
_DIRT_DARK = (130, 100, 60)
_SAND = (205, 180, 120)
_BEACH = (215, 195, 140)
_SNOW = (225, 230, 240)
_ICE = (180, 205, 225)
_SHALLOW = (85, 140, 170)
_WATER = (40, 85, 170)
_WATER_DEEP = (25, 55, 135)
_FOREST = (25, 80, 30)
_FOREST_DRY = (70, 85, 35)
_FOREST_SNOW = (95, 125, 105)
_ROAD = (165, 150, 120)
_FARM = (170, 140, 70)
_BLACK = (10, 10, 10)

TERRAIN_COLORS: dict[int, RGB] = {
    0: _GRASS, 1: _WATER, 2: _BEACH, 3: _DIRT, 4: _SHALLOW, 5: (95, 115, 55), 6: _DIRT,
    7: _FARM, 8: (120, 100, 60), 9: (60, 125, 45), 10: _FOREST, 11: _DIRT_DARK, 12: (65, 130, 55),
    13: (95, 110, 45), 14: _SAND, 15: _WATER, 16: (60, 120, 50), 17: (20, 75, 25), 18: (55, 100, 30),
    19: (20, 65, 35), 20: (35, 90, 35), 21: _FOREST_SNOW, 22: _WATER_DEEP, 23: (35, 75, 155),
    24: _ROAD, 25: (150, 135, 105), 26: _ICE, 27: (110, 105, 70), 28: _WATER, 29: _FARM,
    30: _FARM, 31: _FARM, 32: _SNOW, 33: (200, 195, 180), 34: (190, 205, 185), 35: _ICE,
    36: (200, 200, 205), 37: (200, 215, 230), 38: (190, 185, 175), 39: (120, 110, 90),
    40: (120, 125, 70), 41: (170, 145, 80), 42: (145, 110, 70), 43: (185, 160, 115),
    44: (120, 95, 60), 45: (190, 155, 105), 46: (175, 150, 95), 47: _BLACK, 48: (45, 85, 40),
    49: (105, 105, 45), 50: (95, 105, 45), 51: (220, 210, 165), 52: (195, 190, 125),
    53: (235, 225, 190), 54: (70, 115, 110), 55: (35, 80, 55), 56: (15, 70, 30), 57: (20, 50, 125),
    58: (45, 120, 185), 59: (95, 165, 195), 60: (70, 125, 45), 61: (120, 110, 80), 62: (60, 100, 40),
    63: (110, 145, 80), 64: (130, 120, 80), 65: _BLACK, 66: _BLACK, 67: _BLACK, 68: _BLACK,
    69: (110, 60, 120), 70: (140, 135, 120), 71: (130, 105, 55), 72: (200, 205, 210),
    73: (215, 220, 230), 74: (235, 240, 245), 75: (110, 95, 85), 76: (100, 85, 55),
    77: (80, 110, 45), 78: (145, 140, 125), 79: (205, 185, 130), 80: (190, 170, 120),
    81: (150, 145, 130), 82: (135, 130, 120), 83: (55, 115, 45), 84: _GRASS, 85: _GRASS,
    86: _GRASS, 87: _GRASS, 88: (55, 85, 35), 89: (55, 95, 40), 90: (80, 130, 120),
    91: (150, 160, 100), 92: (90, 125, 60), 93: _SHALLOW, 94: _SHALLOW, 95: (45, 105, 95),
    96: (85, 85, 65), 97: _WATER, 98: _WATER, 99: _WATER_DEEP, 100: _GRASS_DRY,
    101: (85, 95, 55), 102: (175, 155, 115), 103: (145, 140, 125), 104: (105, 70, 25),
    105: (150, 120, 100), 106: (85, 75, 50), 107: (180, 165, 120), 108: (130, 125, 115),
    109: (115, 110, 105), 110: (55, 95, 45), 111: (75, 100, 80), 112: (40, 95, 35),
    113: (45, 105, 35), 114: (140, 145, 90), 115: (160, 160, 110), 116: (115, 115, 60),
    117: (95, 140, 60), 118: (125, 125, 75), 119: (95, 140, 60), 120: (95, 140, 60),
    121: (95, 140, 60), 122: (80, 135, 60), 123: (85, 135, 70), 124: (220, 225, 235),
    125: (210, 215, 225), 126: (235, 240, 245), 127: (185, 210, 230), 128: _FOREST_DRY,
    129: _BLACK, 130: (40, 95, 110), 131: (20, 70, 40), 132: (90, 120, 110), 133: (30, 90, 35),
}
UNKNOWN_TERRAIN: RGB = (255, 0, 255)

# Indexed by ColorId (the player color dropdown: 0 = blue ... 7 = orange).
PLAYER_COLORS: list[RGB] = [
    (45, 90, 255), (230, 20, 20), (0, 200, 0), (255, 230, 0),
    (0, 220, 220), (190, 40, 220), (150, 150, 150), (255, 130, 0),
]
GAIA_COLOR: RGB = (235, 235, 235)

TREE_COLOR: RGB = (0, 55, 10)
GOLD_COLOR: RGB = (255, 215, 0)
STONE_COLOR: RGB = (165, 165, 170)
FOOD_COLOR: RGB = (255, 120, 190)
CLIFF_COLOR: RGB = (110, 85, 60)
OTHER_GAIA_COLOR: RGB = (200, 200, 200)

_FOOD_ANIMALS = ("DEER", "BOAR", "SHEEP", "TURKEY", "GOAT", "PIG", "COW", "LLAMA", "ZEBRA",
                 "OSTRICH", "IBEX", "GAZELLE", "ELEPHANT", "RHINO", "WATER_BUFFALO", "GOOSE",
                 "CAMEL", "YAK", "HORSE", "PIGLET", "BOAR_JAVELINA", "RABBIT", "BEAR")


def player_color(color_id: int | None, player_id: int) -> RGB:
    if player_id == 0:
        return GAIA_COLOR
    if color_id is not None and 0 <= int(color_id) < len(PLAYER_COLORS):
        return PLAYER_COLORS[int(color_id)]
    return PLAYER_COLORS[(player_id - 1) % len(PLAYER_COLORS)]


@lru_cache(maxsize=1)
def _object_classes() -> dict[int, str]:
    classes: dict[int, str] = {}
    for u in OtherInfo:
        n = u.name
        if "CLIFF" in n:
            classes[u.ID] = "cliff"
        elif "GOLD" in n and ("MINE" in n or "ORE" in n):
            classes[u.ID] = "gold"
        elif "STONE_MINE" in n or n == "STONE":
            classes[u.ID] = "stone"
        elif "BUSH" in n and ("FORAGE" in n or "FRUIT" in n or "BERR" in n) or "FISH" in n:
            classes[u.ID] = "food"
    for t in OtherInfo.trees():
        classes[t.ID] = "tree"
    for u in UnitInfo:
        if any(k == u.name or u.name.startswith(k + "_") for k in _FOOD_ANIMALS):
            classes[u.ID] = "food_animal"
    for b in BuildingInfo:
        classes.setdefault(b.ID, "building")
    return classes


def object_class(unit_const: int) -> str:
    """'tree' | 'gold' | 'stone' | 'food' | 'food_animal' | 'cliff' | 'building' | 'unit'."""
    return _object_classes().get(int(unit_const), "unit")


@lru_cache(maxsize=1)
def _building_sizes() -> dict[int, int]:
    sizes = {}
    for b in BuildingInfo:
        n = b.name
        if n.startswith(("TOWN_CENTER", "CASTLE", "MARKET", "KREPOST", "FEITORIA", "HARBOR")):
            s = 4
        elif n.startswith("WONDER"):
            s = 5
        elif n.startswith(("HOUSE", "MILL", "LUMBER_CAMP", "MINING_CAMP", "OUTPOST")):
            s = 2
        elif "WALL" in n or "TOWER" in n or "GATE" in n or "PALISADE" in n:
            s = 1
        else:
            s = 3
        sizes[b.ID] = s
    return sizes


def building_size(unit_const: int) -> int:
    """Approximate square footprint in tiles (3 when unknown)."""
    return _building_sizes().get(int(unit_const), 3)
