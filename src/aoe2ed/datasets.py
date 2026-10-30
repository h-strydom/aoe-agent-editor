"""Name <-> id lookups over the parser's datasets (units, techs, terrains, trigger enums).

Agents write names ("ARCHER", "FEUDAL_AGE", "Set"), the file stores ints. Every resolver
accepts an int, a numeric string or a case-insensitive member name.
"""
from __future__ import annotations

import enum
from functools import lru_cache

from . import _parser  # noqa: F401  (configures the parser)
from AoE2ScenarioParser.datasets import trigger_lists
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.heroes import HeroInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.players import PlayerColorId, PlayerId
from AoE2ScenarioParser.datasets.techs import TechInfo
from AoE2ScenarioParser.datasets.terrains import TerrainId
from AoE2ScenarioParser.datasets.units import UnitInfo

OBJECT_DATASETS = {"unit": UnitInfo, "building": BuildingInfo, "hero": HeroInfo, "other": OtherInfo}

# Datasets whose members carry an .ID (InfoDatasetBase) rather than being int enums.
INFO_DATASETS = {"UnitInfo": UnitInfo, "BuildingInfo": BuildingInfo, "HeroInfo": HeroInfo,
                 "OtherInfo": OtherInfo, "TechInfo": TechInfo}

ENUM_DATASETS: dict[str, type[enum.Enum]] = {
    "PlayerId": PlayerId,
    "PlayerColorId": PlayerColorId,
    "TerrainId": TerrainId,
}
for _name in dir(trigger_lists):
    _obj = getattr(trigger_lists, _name)
    if isinstance(_obj, type) and issubclass(_obj, enum.Enum):
        ENUM_DATASETS[_name] = _obj


def _norm(s: str) -> str:
    return s.strip().upper().replace(" ", "_").replace("-", "_")


@lru_cache(maxsize=None)
def _info_index(dataset_name: str) -> dict[str, int]:
    ds = INFO_DATASETS[dataset_name]
    return {m.name: m.ID for m in ds}


@lru_cache(maxsize=None)
def _object_index() -> dict[str, int]:
    """Any placeable object name -> unit const (units, buildings, heroes, gaia)."""
    out: dict[str, int] = {}
    for ds in (OtherInfo, HeroInfo, BuildingInfo, UnitInfo):  # later wins: units most specific
        for m in ds:
            out[m.name] = m.ID
    return out


def object_id(value: int | str) -> int:
    """Resolve a unit/building/hero/gaia object name or id to its unit const."""
    if isinstance(value, int):
        return value
    if str(value).lstrip("-").isdigit():
        return int(value)
    key = _norm(str(value))
    idx = _object_index()
    if key in idx:
        return idx[key]
    raise KeyError(f"Unknown object '{value}'. Try lookup('{value}').")


def tech_id(value: int | str) -> int:
    if isinstance(value, int) or str(value).lstrip("-").isdigit():
        return int(value)
    key = _norm(str(value))
    idx = _info_index("TechInfo")
    if key in idx:
        return idx[key]
    raise KeyError(f"Unknown technology '{value}'")


def terrain_id(value: int | str) -> int:
    if isinstance(value, int) or str(value).lstrip("-").isdigit():
        return int(value)
    return TerrainId[_norm(str(value))].value


def resolve_dataset_value(dataset_name: str, value):
    """Resolve value for an attribute presented by `dataset_name` (from the parser's
    attribute_presentation table). Returns the raw value the file stores."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, list):
        return value
    s = str(value)
    if s.lstrip("-").isdigit():
        return int(s)
    if dataset_name in ("UnitInfo", "BuildingInfo", "HeroInfo", "OtherInfo"):
        return object_id(s)
    if dataset_name == "TechInfo":
        return tech_id(s)
    if dataset_name == "bool":
        return s.lower() in ("1", "true", "yes", "on")
    if dataset_name in ENUM_DATASETS:
        ds = ENUM_DATASETS[dataset_name]
        key = _norm(s)
        for m in ds:
            if m.name.upper() == key:  # some enums use mixed-case names (DecisionOption.Option1)
                return m.value
        raise KeyError(f"'{value}' is not a {dataset_name}. Options: {[m.name for m in ds][:40]}")
    return value  # str attributes (message, sound_name) or unknown datasets


def describe_value(dataset_name: str, value) -> str | None:
    """Human name for a stored value, or None."""
    if value is None or value == -1 or isinstance(value, (list, str)):
        return None
    try:
        if dataset_name in INFO_DATASETS:
            for m in INFO_DATASETS[dataset_name]:
                if m.ID == value:
                    return m.name
            if dataset_name == "UnitInfo":
                for ds in (BuildingInfo, HeroInfo, OtherInfo):
                    for m in ds:
                        if m.ID == value:
                            return m.name
        elif dataset_name in ENUM_DATASETS:
            return ENUM_DATASETS[dataset_name](value).name
    except (ValueError, KeyError):
        return None
    return None


def search(query: str, kinds: list[str] | None = None, limit: int = 25) -> list[dict]:
    """Fuzzy-ish search across objects, techs, terrains and trigger enums."""
    q = _norm(query)
    kinds = kinds or ["unit", "building", "hero", "other", "tech", "terrain", "enum"]
    hits: list[dict] = []

    kind_rank = {"unit": 0, "building": 0, "hero": 1, "other": 1, "tech": 1, "terrain": 2, "enum": 3}

    def consider(kind, name, id_, extra=None):
        if q in name:
            score = (0 if name == q else 1 if name.startswith(q) else 2, kind_rank[kind], len(name))
            hits.append({"kind": kind, "name": name, "id": id_, **(extra or {}), "_s": score})

    for kind, ds in OBJECT_DATASETS.items():
        if kind in kinds:
            for m in ds:
                consider(kind, m.name, m.ID)
    if "tech" in kinds:
        for m in TechInfo:
            consider("tech", m.name, m.ID)
    if "terrain" in kinds:
        for m in TerrainId:
            consider("terrain", m.name, m.value)
    if "enum" in kinds:
        for ds_name, ds in ENUM_DATASETS.items():
            if ds_name == "TerrainId":
                continue
            for m in ds:
                if isinstance(m.value, (int, str)):
                    consider("enum", m.name, m.value, {"enum": ds_name})
    hits.sort(key=lambda h: h["_s"])
    for h in hits:
        h.pop("_s")
    return hits[:limit]


def enum_members(dataset_name: str) -> list[dict]:
    if dataset_name in INFO_DATASETS:
        return [{"name": m.name, "id": m.ID} for m in INFO_DATASETS[dataset_name]]
    ds = ENUM_DATASETS[dataset_name]
    return [{"name": m.name, "value": m.value} for m in ds]
