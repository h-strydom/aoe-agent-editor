"""Resolve terrain and object names (parser dataset names) to ids."""
from __future__ import annotations

from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.heroes import HeroInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.terrains import TerrainId
from AoE2ScenarioParser.datasets.units import UnitInfo

# Forest terrain -> the tree object the editor places on it.
FOREST_TREES = {
    "FOREST_OAK": "TREE_OAK_FOREST", "FOREST_OAK_BUSH": "TREE_OAK_FOREST",
    "FOREST_OAK_GREEN": "TREE_OAK_GREEN", "FOREST_PINE": "TREE_PINE_FOREST",
    "FOREST_PINE_SNOW": "TREE_SNOW_PINE", "FOREST_PALM_DESERT": "TREE_PALM_FOREST",
    "FOREST_PALM_GRASS": "TREE_PALM_FOREST", "FOREST_JUNGLE": "TREE_JUNGLE",
    "FOREST_BAMBOO": "TREE_BAMBOO_FOREST", "FOREST_LUSH_BAMBOO": "TREE_LUSH_BAMBOO_FOREST",
    "FOREST_AUTUMN": "TREE_OAK_AUTUMN", "FOREST_AUTUMN_SNOW": "TREE_OAK_AUTUMN_SNOW",
    "FOREST_DEAD": "TREE_DEAD", "FOREST_BIRCH": "TREE_BIRCH", "FOREST_ACACIA": "TREE_ACACIA",
    "FOREST_BAOBAB": "TREE_BAOBAB", "FOREST_DRAGON_TREE": "TREE_DRAGON",
    "FOREST_MANGROVE": "TREE_MANGROVE", "FOREST_MEDITERRANEAN": "TREE_ITALIAN_PINE",
    "FOREST_RAINFOREST": "TREE_RAINFOREST", "FOREST_SPRUCE": "TREE_SPRUCE",
    "FOREST_SPRUCE_SNOW": "TREE_SPRUCE_SNOW", "FOREST_DRY_SOUTH_AMERICAN": "TREE_MONKEY_PUZZLE",
    "FOREST_REEDS": "TREE_REEDS", "FOREST_BUSH": "BUSH_A",
}


def terrain_id(v: str | int) -> int:
    if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
        return int(v)
    try:
        return int(TerrainId[v.upper()])
    except KeyError:
        raise ValueError(f"Unknown terrain {v!r} (use a TerrainId name such as GRASS_1)") from None


def unit_id(v: str | int) -> int:
    if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
        return int(v)
    from .. import games
    if games.current() == "ror":  # Return of Rome names (see aoe2ed.games)
        from ..datasets import object_id
        try:
            return object_id(v)
        except KeyError as e:
            raise ValueError(e.args[0]) from None
    name = v.upper().replace(" ", "_")
    for ds in (BuildingInfo, UnitInfo, OtherInfo, HeroInfo):
        if name in ds.__members__:
            return ds[name].ID
    raise ValueError(f"Unknown object {v!r} (use a BuildingInfo/UnitInfo/OtherInfo name)")


def tree_for_forest(forest: str | int) -> int:
    tid = terrain_id(forest)
    try:
        name = TerrainId(tid).name
    except ValueError:
        name = ""
    return unit_id(FOREST_TREES.get(name, "TREE_OAK_FOREST"))


def cliff_ids(family: str) -> list[int]:
    """The 9 cliff pieces of a family (CLIFF_DEFAULT, CLIFF_DESERT, CLIFF_SNOW)."""
    return [OtherInfo[f"{family.upper()}_{k}"].ID for k in range(1, 10)]
