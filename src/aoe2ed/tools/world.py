"""Players, diplomacy, options, messages, map terrain/elevation, units."""
from __future__ import annotations

from AoE2ScenarioParser.datasets.object_support import Civilization, StartingAge

from .. import games
from ..datasets import ENUM_DATASETS, describe_value, object_id, resolve_dataset_value, terrain_id
from ..session import SESSIONS
from . import tool

# ---------------------------------------------------------------- players

PLAYER_FIELDS = ("active", "human", "civilization", "architecture_set", "color", "starting_age",
                 "food", "wood", "gold", "stone", "population_cap", "lock_civ", "lock_personality",
                 "allied_victory", "tribe_name", "base_priority",
                 "initial_player_view_x", "initial_player_view_y", "disabled_units", "disabled_techs",
                 "disabled_buildings", "ai_type", "personality")


def _player_dict(p) -> dict:
    d = {"id": p.player_id}
    for f in PLAYER_FIELDS:
        if hasattr(p, f):
            v = getattr(p, f)
            d[f] = getattr(v, "name", v)
    d["diplomacy"] = getattr(p, "diplomacy", None)
    return d


@tool
def players_get(handle: str) -> list[dict]:
    """All 9 player slots (0 = Gaia): civ, color, age, resources, pop cap, disables, diplomacy."""
    return [_player_dict(p) for p in SESSIONS.get(handle).scenario.player_manager.players]


def _civ(v):
    if isinstance(v, str) and not v.isdigit():
        name = v.upper().replace(" ", "_").replace("-", "_")
        if games.current() == "ror":
            civs = games.ror_data()["civs"]
            if name in civs:
                return civs[name]
            if name in ("RANDOM", "FULL_RANDOM"):
                return Civilization[name]
            raise ValueError(f"Unknown Return of Rome civilization '{v}'. Options: {sorted(civs)}")
        return Civilization[name]
    return v


def _set_civ(p, field: str, value) -> None:
    if isinstance(value, str):  # RoR civs aren't in the parser's Civilization enum; store the data name
        setattr(p, f"_{field}", value)
    else:
        setattr(p, field, value)


def _age(v):
    if isinstance(v, str) and not v.isdigit():
        name = v.upper().replace(" ", "_")
        return StartingAge[name if name.endswith("_AGE") else name + "_AGE"]
    return v


def set_ai(p, ai) -> None:
    if isinstance(ai, dict) and "spec" in ai:          # an AI spec (aoe2ed.ai.spec), built for the current game
        from ..ai.per import check
        from ..ai.spec import build_script
        script = build_script(ai["spec"], games.current())
        errors = [d.message for d in check(script) if d.severity == "error"]
        if errors:
            raise ValueError(f"AI spec gives a script with errors: {errors[:5]}")
        p.set_custom_ai(ai.get("name") or ai["spec"].get("name") or "Custom AI", ai_script=script)
    elif isinstance(ai, dict) and "standard" in ai:     # the game's standard AI playing a chosen difficulty
        from ..ai.standard import standard_script
        cfg = ai["standard"] or {}
        p.set_custom_ai(ai.get("name") or "Standard AI",
                        ai_script=standard_script(cfg.get("plays"), resign=bool(cfg.get("resign")),
                                                  attack_after=int(cfg.get("attack_after") or 0),
                                                  game=games.current()))
    elif isinstance(ai, dict):
        p.set_custom_ai(ai["name"], ai_script=ai.get("script"), per_file_path=ai.get("per_file"))
    elif ai == "none":
        p.set_none_ai()
    elif ai == "immobile":
        p.set_immobile_ai()
    elif ai != "default":
        raise ValueError("ai must be 'none', 'immobile', 'default' or {name, spec|script|per_file|standard}")


@tool
def player_set(handle: str, player: int, fields: dict) -> dict:
    """Set player fields. Names allowed: civilization 'BRITONS', starting_age 'FEUDAL',
    disabled_units/disabled_techs/disabled_buildings as lists of names or ids.
    ai: 'none' (no AI script: never resigns or acts on its own, the right choice for trigger-driven
    enemies), 'immobile', 'default' (the game's standard AI, which resigns when it judges the game
    lost), {"name": ..., "spec": {<AI spec: build order, attacks, ...; guide("ai-spec")>}},
    or {"name": ..., "script": "<.per text>"} / {"name": ..., "per_file": path}, or {"standard": {"plays":
    {"moderate": "hard", "hard": "hardest"}, "resign": false, "attack_after": 1800}}: the game's standard
    skirmish AI (embedded,
    loading the game's ai/default files), each listed difficulty playing another's settings, its first attack no
    sooner than attack_after seconds (aoe2ed.ai.standard).
    Fields: see players_get output."""
    s = SESSIONS.get(handle).scenario
    p = s.player_manager.players[player]
    for k, v in fields.items():
        if k == "ai":
            set_ai(p, v)
            continue
        if k not in PLAYER_FIELDS:
            raise ValueError(f"Unknown player field '{k}'. Fields: {PLAYER_FIELDS}")
        if k in ("civilization", "architecture_set"):
            _set_civ(p, k, _civ(v))
            continue
        elif k == "starting_age":
            v = _age(v)
        elif k in ("disabled_units", "disabled_buildings"):
            v = [object_id(x) for x in v]
        elif k == "disabled_techs":
            from ..datasets import tech_id
            v = [tech_id(x) for x in v]
        setattr(p, k, v)
    return _player_dict(p)


@tool
def diplomacy_set(handle: str, player: int, others: list[int], state: str = "ALLY", mutual: bool = True) -> dict:
    """Set diplomacy from `player` to each of `others`. state: ALLY | NEUTRAL | ENEMY."""
    s = SESSIONS.get(handle).scenario
    d = resolve_dataset_value("DiplomacyState", state)
    pm = s.player_manager
    pm.players[player].set_player_diplomacy(others, d)
    if mutual:
        for o in others:
            pm.players[o].set_player_diplomacy([player], d)
    return {"player": player, "diplomacy": pm.players[player].diplomacy}


# ---------------------------------------------------------------- options & messages

OPTION_DATASETS = {"victory_condition": "VictoryCondition", "secondary_game_modes": "SecondaryGameMode"}
OPTION_FIELDS = ("victory_condition", "victory_score", "victory_years", "victory_custom_conditions_required",
                 "secondary_game_modes", "lock_teams", "allow_players_choose_teams", "random_start_points",
                 "lock_coop_alliances", "villager_force_drop", "collide_and_correct", "legacy_execution_order",
                 "victory_conquest", "victory_relics", "ai_map_type")
# Options the option manager doesn't carry: name -> (scenario section, field, type).
#   victory_conquest: the Conquest checkbox of a Custom victory, on by default.
#   victory_relics: the Relics a Custom victory asks for (0: the box unchecked).
#   ai_map_type: the map the standard AI plays it as (Options > AI Map Type; a map id: RoR's Small Islands is
#     166, Continental 144, read from maps saved by the RoR editor, 2026-11-12; the others from the game's
#     modes/Pompeii/resources/_common/dat/maps.json storage_id). Islands teach it boats and transports. Coastal,
#     Continental, Mediterranean, Rivers, Narrows and Inland tell it there is water to use, so it builds a Dock and
#     galleys (galley-rushes while its enemy has no army) whatever the map; Highland doesn't (ai/default/init.per:
#     only fish, over 5 ocean or 25 shore fish, then does).
SECTION_OPTIONS = {"victory_conquest": ("GlobalVictory", "conquest_required", bool),
                   "victory_relics": ("GlobalVictory", "artifacts_required", int),
                   "ai_map_type": ("Options", "ai_map_type", int)}
AI_MAP_TYPES = {"ror": {"small_islands": 166, "continental": 144, "coastal": 143, "highland": 148,
                         "large_islands": 153, "mediterranean": 154, "inland": 150}}
MESSAGE_FIELDS = ("instructions", "hints", "victory", "loss", "history", "scouts")


@tool
def options_get(handle: str) -> dict:
    """Scenario options: victory condition/score/years, the Custom victory's Conquest checkbox and Relics, team
    locks, game modes, etc."""
    scenario = SESSIONS.get(handle).scenario
    om = scenario.option_manager
    out = {}
    for f in OPTION_FIELDS:
        if f in SECTION_OPTIONS:
            section, field, kind = SECTION_OPTIONS[f]
            out[f] = kind(getattr(scenario.sections[section], field))
            continue
        v = getattr(om, f, None)
        out[f] = getattr(v, "name", v) if not isinstance(v, list) else [getattr(x, "name", x) for x in v]
    return out


@tool
def options_set(handle: str, fields: dict) -> dict:
    """Set scenario options (see options_get for fields). Enum values by name, e.g.
    victory_condition='CUSTOM'."""
    scenario = SESSIONS.get(handle).scenario
    om = scenario.option_manager
    for k, v in fields.items():
        if k not in OPTION_FIELDS:
            raise ValueError(f"Unknown option '{k}'. Options: {OPTION_FIELDS}")
        if k in SECTION_OPTIONS:
            section, field, kind = SECTION_OPTIONS[k]
            if k == "ai_map_type" and isinstance(v, str):
                types = AI_MAP_TYPES.get(games.scenario_game(scenario), {})
                if v not in types:
                    raise ValueError(f"ai_map_type: a map id or one of {sorted(types)}, got {v!r}")
                v = types[v]
            setattr(scenario.sections[section], field, int(kind(v)))
            continue
        ds = OPTION_DATASETS.get(k)
        if ds:
            enum_cls = ENUM_DATASETS[ds]
            v = [enum_cls(resolve_dataset_value(ds, x)) for x in v] if isinstance(v, list) \
                else enum_cls(resolve_dataset_value(ds, v))
        setattr(om, k, v)
    return options_get(handle)


@tool
def messages_set(handle: str, fields: dict) -> dict:
    """Set the Messages panel texts: instructions, hints, victory, loss, history, scouts."""
    mm = SESSIONS.get(handle).scenario.message_manager
    for k, v in fields.items():
        if k not in MESSAGE_FIELDS:
            raise ValueError(f"Unknown message field '{k}'. Fields: {MESSAGE_FIELDS}")
        setattr(mm, k, v)
    return {k: getattr(mm, k) for k in MESSAGE_FIELDS}


# ---------------------------------------------------------------- map

MAX_GRID = 80 * 80


def _clip_rect(size: int, x1, y1, x2, y2):
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(size - 1, int(x2)), min(size - 1, int(y2))
    if x1 > x2 or y1 > y2:
        raise ValueError("Empty area")
    return x1, y1, x2, y2


@tool
def map_info(handle: str) -> dict:
    """Map size, color mood and a histogram of terrain ids and elevations."""
    mm = SESSIONS.get(handle).scenario.map_manager
    terr, elev = {}, {}
    for t in mm.terrain:
        terr[t.terrain_id] = terr.get(t.terrain_id, 0) + 1
        elev[t.elevation] = elev.get(t.elevation, 0) + 1
    return {"map_size": mm.map_size, "color_mood": getattr(mm.map_color_mood, "name", mm.map_color_mood),
            "terrain_histogram": {f"{describe_value('TerrainId', k) or k}": v for k, v in
                                  sorted(terr.items(), key=lambda kv: -kv[1])},
            "elevation_histogram": dict(sorted(elev.items()))}


@tool
def map_resize(handle: str, map_size: int) -> dict:
    """Change the map size (square, 36..480). Units outside the new bounds should be removed first."""
    mm = SESSIONS.get(handle).scenario.map_manager
    mm.map_size = map_size
    return {"map_size": mm.map_size}


@tool
def map_get(handle: str, area: list[int] | None = None, layer: str = "terrain", x1: int | None = None,
            y1: int | None = None, x2: int | None = None, y2: int | None = None) -> dict:
    """Read area [x1,y1,x2,y2] of the map as rows (y) of values (x). layer: terrain | elevation |
    layer. Max 6400 tiles per call. (x1..y2 as separate params also work.)"""
    mm = SESSIONS.get(handle).scenario.map_manager
    if area is not None:
        x1, y1, x2, y2 = area
    if None in (x1, y1, x2, y2):
        raise ValueError("Pass area=[x1, y1, x2, y2]")
    x1, y1, x2, y2 = _clip_rect(mm.map_size, x1, y1, x2, y2)
    if (x2 - x1 + 1) * (y2 - y1 + 1) > MAX_GRID:
        raise ValueError("Area too large; read it in chunks of <= 80x80")
    attr = {"terrain": "terrain_id", "elevation": "elevation", "layer": "layer"}[layer]
    rows = [[getattr(mm.get_tile(x, y), attr) for x in range(x1, x2 + 1)] for y in range(y1, y2 + 1)]
    return {"origin": [x1, y1], "layer": layer, "rows": rows}


@tool
def map_set_terrain(handle: str, terrain: str | int, area: list[int] | None = None,
                    tiles: list[list[int]] | None = None, layer: str | int | None = None) -> dict:
    """Paint terrain over area [x1,y1,x2,y2] (inclusive) and/or a list of [x,y] tiles.
    terrain by name ('GRASS_1', 'WATER_DEEP', 'FOREST_OAK') or id. `layer` sets the overlay terrain."""
    mm = SESSIONS.get(handle).scenario.map_manager
    tid = terrain_id(terrain)
    lid = terrain_id(layer) if layer is not None else None
    n = 0
    targets = []
    if area:
        x1, y1, x2, y2 = _clip_rect(mm.map_size, *area)
        targets += [(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1)]
    for x, y in tiles or []:
        targets.append((x, y))
    for x, y in targets:
        t = mm.get_tile_safe(x, y) if hasattr(mm, "get_tile_safe") else mm.get_tile(x, y)
        if t is None:
            continue
        t.terrain_id = tid
        if lid is not None:
            t.layer = lid
        n += 1
    return {"painted": n, "terrain": tid}


@tool
def map_set_elevation(handle: str, elevation: int, area: list[int], smooth: bool = True) -> dict:
    """Set elevation (0-7) over area [x1,y1,x2,y2]. smooth=True uses the parser's sloped
    set_elevation (like the editor's elevation brush); False sets raw tile heights."""
    mm = SESSIONS.get(handle).scenario.map_manager
    x1, y1, x2, y2 = _clip_rect(mm.map_size, *area)
    if smooth:
        mm.set_elevation(elevation, x1, y1, x2, y2)
    else:
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                mm.get_tile(x, y).elevation = elevation
    return {"area": [x1, y1, x2, y2], "elevation": elevation}


# ---------------------------------------------------------------- units

def _unit_dict(u) -> dict:
    return {"ref": u.reference_id, "player": int(u.player), "type": u.unit_const,
            "name": describe_value("UnitInfo", u.unit_const), "x": round(u.x, 2), "y": round(u.y, 2),
            "z": round(u.z, 2), "rotation": round(u.rotation, 3), "status": u.status,
            "garrisoned_in": u.garrisoned_in_id if u.garrisoned_in_id != -1 else None,
            **({"caption": u.caption_string} if getattr(u, "caption_string", "") else {})}


def _select_units(s, player=None, area=None, types=None):
    um = s.unit_manager
    units = um.get_all_units() if player is None else um.get_player_units(player)
    if area:
        x1, y1, x2, y2 = area
        units = [u for u in units if x1 <= u.x <= x2 + 1 and y1 <= u.y <= y2 + 1]
    if types:
        consts = {object_id(t) for t in types}
        units = [u for u in units if u.unit_const in consts]
    return units


@tool
def units_list(handle: str, player: int | None = None, area: list[int] | None = None,
               types: list[str | int] | None = None, limit: int = 200) -> dict:
    """List units, filtered by player (0 = Gaia), area [x1,y1,x2,y2] and/or types (names or ids)."""
    units = _select_units(SESSIONS.get(handle).scenario, player, area, types)
    return {"count": len(units), "units": [_unit_dict(u) for u in units[:limit]]}


@tool
def units_add(handle: str, units: list[dict]) -> list[dict]:
    """Place units. Each: {player, type ('CASTLE', 'ARCHER', 'TREE_OAK_FOREST', id), x, y,
    rotation? (radians), status? (2 = normal), garrisoned_in? (ref), caption?}.
    Coordinates are tile coordinates; use x+0.5 to centre on a tile."""
    s = SESSIONS.get(handle).scenario
    out = []
    for spec in units:
        u = s.unit_manager.add_unit(
            player=spec.get("player", 0), unit_const=object_id(spec["type"]),
            x=float(spec["x"]), y=float(spec["y"]), z=float(spec.get("z", 0)),
            rotation=float(spec.get("rotation", 0)), status=spec.get("status", 2),
            garrisoned_in_id=spec.get("garrisoned_in", -1), caption_string=spec.get("caption", ""))
        out.append(_unit_dict(u))
    return out


@tool
def units_remove(handle: str, refs: list[int] | None = None, player: int | None = None,
                 area: list[int] | None = None, types: list[str | int] | None = None) -> dict:
    """Remove units by reference ids, or by filter (player/area/types). At least one is required."""
    s = SESSIONS.get(handle).scenario
    if refs:
        ref_set = set(refs)
        victims = [u for u in s.unit_manager.get_all_units() if u.reference_id in ref_set]
    elif player is not None or area or types:
        victims = _select_units(s, player, area, types)
    else:
        raise ValueError("Pass refs or a filter")
    for u in victims:
        s.unit_manager.remove_unit(unit=u)
    return {"removed": len(victims)}


@tool
def unit_update(handle: str, ref: int, fields: dict) -> dict:
    """Change a placed unit: x, y, z, rotation, status, player, type, caption, garrisoned_in."""
    s = SESSIONS.get(handle).scenario
    um = s.unit_manager
    u = next((u for u in um.get_all_units() if u.reference_id == ref), None)
    if u is None:
        raise KeyError(f"No unit with ref {ref}")
    for k, v in fields.items():
        if k == "player":
            um.change_ownership(u, v)
        elif k == "type":
            u.unit_const = object_id(v)
        elif k == "caption":
            u.caption_string = v
        elif k == "garrisoned_in":
            u.garrisoned_in_id = v
        elif k in ("x", "y", "z", "rotation", "status"):
            setattr(u, k, v)
        else:
            raise ValueError(f"Unknown unit field '{k}'")
    return _unit_dict(u)
