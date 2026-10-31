"""Map spec: the declarative description the generator turns into terrain, elevation and units.

Every field has a usable default, so `MapSpec(size=120, seed=1)` already makes a playable
two-player land map. `MapSpec.from_dict` builds a spec from plain dicts (YAML/JSON) and
rejects unknown keys with the list of allowed ones.

Points ("Point") can be given as:
  [x, y]            a tile
  "center"          the map center
  "edge:<dir>[:n]"  the map edge/corner in compass direction <dir>, n tiles inwards (default 4)
  "player<N>"       player N's start (town center) position
  "<area name>"     the center of a named area created by an earlier step
"""
from __future__ import annotations

import dataclasses
import types
from dataclasses import dataclass, field
from typing import Any, Union, get_args, get_origin, get_type_hints

Point = tuple[int, int] | list[int] | str
Rect = tuple[int, int, int, int]


@dataclass
class Biome:
    """Terrain palette. Names are TerrainId names (or ids)."""
    base: str | int = "GRASS_1"
    forest: str | int = "FOREST_OAK"
    tree: str | int | None = None          # tree unit; derived from `forest` when None
    accents: list[str | int] = field(default_factory=lambda: ["GRASS_2", "GRASS_3"])
    accent_coverage: float = 0.3           # fraction of land covered by accent patches
    water: str | int = "WATER_MEDIUM"
    deep_water: str | int = "WATER_DEEP"
    shallows: str | int = "SHALLOWS"
    beach: str | int | None = "BEACH"
    road: str | int = "ROAD"
    base_floor: str | int | None = "DIRT_3"  # painted under player town centers
    cliff: str = "CLIFF_DEFAULT"           # cliff unit family: CLIFF_DEFAULT | CLIFF_DESERT | CLIFF_SNOW


BIOMES: dict[str, Biome] = {
    "temperate": Biome(),
    "autumn": Biome(base="GRASS_3", forest="FOREST_AUTUMN", accents=["GRASS_DRY", "DIRT_3"],
                    base_floor="DIRT_1"),
    "pine": Biome(base="GRASS_2", forest="FOREST_PINE", accents=["GRASS_1", "DIRT_3"]),
    "desert": Biome(base="DESERT_SAND", forest="FOREST_PALM_DESERT", accents=["DIRT_1", "DESERT_CRACKED"],
                    beach="BEACH_WHITE", road="ROAD_BROKEN", base_floor="DIRT_2", cliff="CLIFF_DESERT"),
    "snow": Biome(base="SNOW", forest="FOREST_PINE_SNOW", accents=["SNOW_LIGHT", "SNOW_STRONG"],
                  beach="BEACH_ICE", road="ROAD_GRAVEL", base_floor="SNOW_FOUNDATION", cliff="CLIFF_SNOW"),
    "jungle": Biome(base="GRASS_JUNGLE", forest="FOREST_JUNGLE", accents=["GRASS_JUNGLE_RAINFOREST", "DIRT_MUD"],
                    road="ROAD_FUNGUS", base_floor="DIRT_MUD"),
    "mediterranean": Biome(base="GRASS_DRY", forest="FOREST_MEDITERRANEAN", accents=["GRASS_1", "DIRT_1"],
                           water="WATER_AZURE", shallows="SHALLOWS_AZURE", base_floor="DIRT_1"),
    "steppe": Biome(base="DIRT_SAVANNAH", forest="FOREST_ACACIA", accents=["GRASS_DRY", "DIRT_4"],
                    base_floor="DIRT_4"),
}


@dataclass
class PlayerStart:
    position: Point | None = None   # None: placed by MapSpec.player_layout
    base_radius: int = 9            # flat, tree-free radius around the town center
    town_center: bool = True
    villagers: int = 3
    scout: bool = True


@dataclass
class ForestSpec:
    coverage: float = 0.18              # target fraction of the map covered by forest
    clumps: int = 12                    # roughly how many forest clumps carry that coverage
    border: int = 0                     # thickness of a forest ring along the map edge (0 = none)
    player_woodlines: int = 2           # woodline clumps just outside each player base
    woodline_size: int = 45             # tiles per woodline clump
    stragglers: int = 3                 # single trees inside each base


@dataclass
class ResourceSpec:
    gold: list[int] = field(default_factory=lambda: [7, 4])   # pile sizes per player
    stone: list[int] = field(default_factory=lambda: [5, 4])
    berries: int = 6
    sheep: int = 4                      # player-owned, next to the town center
    deer: int = 3                       # gaia, a bit further out
    gold_distance: tuple[int, int] = (9, 17)     # distance band from the town center
    stone_distance: tuple[int, int] = (10, 18)
    berries_distance: tuple[int, int] = (6, 10)
    deer_distance: tuple[int, int] = (14, 22)
    neutral_gold: list[int] = field(default_factory=list)   # extra piles away from bases
    neutral_stone: list[int] = field(default_factory=list)


@dataclass
class WaterSpec:
    kind: str = "lake"                  # lake | river
    name: str | None = None
    center: Point | None = None         # lake: None = random spot away from bases
    radius: int = 8                     # lake radius
    points: list[Point] = field(default_factory=list)   # river path; default edge `start` -> `end`
    start: str = "nw"                   # river: compass direction it enters from
    end: str = "se"
    width: int = 4                      # river width
    fords: int = 2                      # shallow crossings across a river
    fish: int = 4


@dataclass
class Hill:
    center: Point
    height: int = 3
    radius: int = 7
    name: str | None = None


@dataclass
class ElevationSpec:
    hills: int = 0                      # random hills (in addition to `explicit`)
    height: tuple[int, int] = (2, 4)    # random hill height range (max 7)
    radius: tuple[int, int] = (5, 10)
    explicit: list[Hill] = field(default_factory=list)


@dataclass
class CliffSpec:
    """Experimental: cliff objects along a polyline."""
    points: list[Point]
    name: str | None = None


@dataclass
class RoadSpec:
    points: list[Point]
    width: int = 2
    terrain: str | int | None = None    # default: biome road
    name: str | None = None
    wobble: float = 1.5                 # max sideways drift in tiles (0 = straight)


@dataclass
class ZoneSpec:
    """A named area. kinds:
    rect   - `rect` [x1,y1,x2,y2]
    edge   - along the map edge/corner `side` (compass dir), `width` along the edge x `depth` inwards
    circle - around `center` with `radius`
    choke  - a gap of `gap` tiles across the line `between` [A, B] at fraction `at`, walled
             by forest (or cliffs with wall='cliff') `wall_length` tiles to each side
    """
    name: str
    kind: str = "rect"
    rect: Rect | None = None
    side: str | None = None
    width: int = 14
    depth: int = 8
    center: Point | None = None
    radius: int = 6
    between: list[Point] = field(default_factory=list)
    at: float = 0.5
    gap: int = 5
    wall_length: int = 22
    wall: str = "forest"
    clear: bool = True                  # keep trees and resources out
    flat: bool = False                  # keep hills out
    terrain: str | int | None = None    # paint the zone with this terrain


@dataclass
class UnitPlacement:
    unit: str | int                     # BuildingInfo/UnitInfo/OtherInfo name or id
    position: Point
    player: int = 0
    offset: tuple[float, float] = (0, 0)
    rotation: float = 0


@dataclass
class MapSpec:
    size: int = 120
    seed: int = 0
    biome: str | Biome = "temperate"
    players: list[PlayerStart] | int = 2
    player_layout: str = "ring"         # ring | center | line (ignored for explicit positions)
    player_distance: float = 0.34       # ring radius as a fraction of map size
    extra_players: int = 0              # active players without starting units (e.g. enemy waves)
    forests: ForestSpec = field(default_factory=ForestSpec)
    resources: ResourceSpec = field(default_factory=ResourceSpec)
    water: list[WaterSpec] = field(default_factory=list)
    elevation: ElevationSpec = field(default_factory=ElevationSpec)
    cliffs: list[CliffSpec] = field(default_factory=list)
    roads: list[RoadSpec] = field(default_factory=list)
    zones: list[ZoneSpec] = field(default_factory=list)
    units: list[UnitPlacement] = field(default_factory=list)
    steps: list[str] | None = None      # pipeline override (names from mapgen.steps.STEPS)

    def __post_init__(self):
        hints = get_type_hints(MapSpec)
        for f in dataclasses.fields(self):  # accept plain dicts for nested specs
            v = getattr(self, f.name)
            if isinstance(v, (dict, list)):
                setattr(self, f.name, _convert(hints[f.name], v))
        if not 36 <= self.size <= 480:
            raise ValueError("size must be between 36 and 480")
        if isinstance(self.players, int):
            self.players = [PlayerStart() for _ in range(self.players)]
        if not 1 <= len(self.players) + self.extra_players <= 8:
            raise ValueError("players + extra_players must be between 1 and 8")

    @property
    def biome_spec(self) -> Biome:
        if isinstance(self.biome, Biome):
            return self.biome
        try:
            return BIOMES[self.biome]
        except KeyError:
            raise ValueError(f"Unknown biome {self.biome!r}; presets: {sorted(BIOMES)}") from None

    @classmethod
    def from_dict(cls, data: dict) -> MapSpec:
        return _from_dict(cls, data)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _from_dict(cls, data: dict):
    hints = get_type_hints(cls)
    names = {f.name for f in dataclasses.fields(cls)}
    unknown = set(data) - names
    if unknown:
        raise ValueError(f"{cls.__name__}: unknown keys {sorted(unknown)}; allowed: {sorted(names)}")
    return cls(**{k: _convert(hints[k], v) for k, v in data.items()})


def _convert(tp, v: Any):
    if v is None:
        return None
    if dataclasses.is_dataclass(tp) and isinstance(v, dict):
        return _from_dict(tp, v)
    origin, args = get_origin(tp), get_args(tp)
    if origin is list and isinstance(v, (list, tuple)):
        return [_convert(args[0], x) for x in v] if args else list(v)
    if origin is tuple and isinstance(v, (list, tuple)):
        return tuple(v)
    if origin in (Union, types.UnionType):
        for a in args:
            if dataclasses.is_dataclass(a) and isinstance(v, dict):
                return _from_dict(a, v)
        for a in args:
            if get_origin(a) is list and isinstance(v, list):
                return _convert(a, v)
    return v
