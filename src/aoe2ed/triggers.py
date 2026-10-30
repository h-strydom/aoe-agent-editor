"""Triggers as JSON-friendly dicts, in both directions.

Trigger dict:
  {"name": "Wave 1", "enabled": true, "looping": false, "execute_on_load": false,
   "description": "...", "short_description": "...", "display_as_objective": false,
   "display_on_screen": false, "description_order": 0, "header": false, "mute_objectives": false,
   "conditions": [{"type": "timer", "timer": 60}],
   "effects": [{"type": "create_object", "object_list_unit_id": "MAN_AT_ARMS",
                "source_player": 2, "location": [10, 10]}]}

Shorthands accepted in conditions/effects:
  area: [x1, y1, x2, y2]      -> area_x1..area_y2
  location: [x, y]            -> location_x, location_y
  variable / variable2: name  -> variable id (created if missing when create_variables=True)
  trigger_id: name            -> trigger index (may reference triggers defined later in a batch)
  enum/dataset values by name -> "ARCHER", "ONE", "Set", "FEUDAL_AGE"
"""
from __future__ import annotations

from typing import Any

from ._parser import ConditionId, EffectId, condition_dataset, effect_dataset
from .datasets import describe_value, resolve_dataset_value

TRIGGER_FIELDS = ("name", "description", "short_description", "enabled", "looping", "execute_on_load",
                  "display_as_objective", "display_on_screen", "description_order", "header",
                  "mute_objectives", "short_description_order")
BOOL_FIELDS = {"enabled", "looping", "execute_on_load", "display_as_objective", "display_on_screen",
               "header", "mute_objectives"}


# ---------------------------------------------------------------- schema

def _presentation(dataset, type_id: int, attr: str) -> str:
    pres = dataset.attribute_presentation
    return (pres.get(type_id) or {}).get(attr) or pres.get(-1, {}).get(attr, "")


def _ensure_loaded() -> None:
    if not effect_dataset.attributes:
        raise RuntimeError("Open or create a scenario first: effect schemas load with a scenario version")


def effect_types() -> list[dict]:
    _ensure_loaded()
    return [{"type": e.name.lower(), "id": e.value} for e in EffectId if e.value in effect_dataset.attributes]


def condition_types() -> list[dict]:
    _ensure_loaded()
    return [{"type": c.name.lower(), "id": c.value} for c in ConditionId
            if c.value in condition_dataset.attributes]


def _schema(dataset, enum_cls, type_name: str) -> dict:
    _ensure_loaded()
    member = enum_cls[type_name.upper()]
    attrs = [a for a in dataset.attributes[member.value] if a not in ("effect_type", "condition_type")]
    defaults = dataset.default_attributes.get(member.value, {})
    doc = (member.__doc__ or "").strip()
    added = next((ln.strip() for ln in doc.splitlines() if "added in" in ln), None)
    return {
        "type": member.name.lower(),
        "id": member.value,
        "params": [{"name": a, "dataset": _presentation(dataset, member.value, a) or None,
                    **({"default": defaults[a]} if a in defaults else {})} for a in attrs],
        "added_in": added,
    }


def effect_schema(type_name: str) -> dict:
    return _schema(effect_dataset, EffectId, type_name)


def condition_schema(type_name: str) -> dict:
    return _schema(condition_dataset, ConditionId, type_name)


# ---------------------------------------------------------------- to dict

def _ce_to_dict(obj, dataset, type_attr: str, enum_cls, verbose: bool) -> dict:
    type_id = getattr(obj, type_attr)
    out: dict[str, Any] = {"type": enum_cls(type_id).name.lower()}
    names: dict[str, str] = {}
    for a in dataset.attributes.get(type_id, []):
        if a == type_attr or a == "quantity_float":  # quantity_float is surfaced through `quantity`
            continue
        v = getattr(obj, a, None)
        if v is None or v == -1 or v == [] or v == "":
            continue
        out[a] = v
        if verbose:
            n = describe_value(_presentation(dataset, type_id, a), v)
            if n:
                names[a] = n
    if names:
        out["_names"] = names
    return out


def trigger_to_dict(trigger, verbose: bool = False) -> dict:
    d: dict[str, Any] = {"index": trigger.trigger_id}
    for f in TRIGGER_FIELDS:
        if hasattr(trigger, f):
            v = getattr(trigger, f)
            d[f] = bool(v) if f in BOOL_FIELDS else v
    d["conditions"] = [_ce_to_dict(c, condition_dataset, "condition_type", ConditionId, verbose)
                       for c in trigger.conditions]
    d["effects"] = [_ce_to_dict(e, effect_dataset, "effect_type", EffectId, verbose) for e in trigger.effects]
    return d


def trigger_summary(trigger) -> dict:
    return {"index": trigger.trigger_id, "name": trigger.name, "enabled": bool(trigger.enabled),
            "looping": bool(trigger.looping),
            "conditions": [ConditionId(c.condition_type).name.lower() for c in trigger.conditions],
            "effects": [EffectId(e.effect_type).name.lower() for e in trigger.effects]}


# ---------------------------------------------------------------- from dict

class Resolver:
    """Resolves names used in trigger dicts against one scenario."""

    def __init__(self, scenario, create_variables: bool = True, pending_triggers: dict | None = None):
        self.s = scenario
        self.create_variables = create_variables
        self.pending_triggers = pending_triggers or {}

    def variable(self, value) -> int:
        if isinstance(value, int) or str(value).isdigit():
            return int(value)
        tm = self.s.trigger_manager
        for v in tm.variables:
            if v.name == value:
                return v.variable_id
        if not self.create_variables:
            raise KeyError(f"Unknown variable '{value}'")
        return tm.add_variable(str(value)).variable_id

    def trigger(self, value) -> int:
        if isinstance(value, int) or str(value).isdigit():
            return int(value)
        if value in self.pending_triggers:
            return self.pending_triggers[value]
        for t in self.s.trigger_manager.triggers:
            if t.name == value:
                return t.trigger_id
        raise KeyError(f"Unknown trigger '{value}'")

    def params(self, dataset, type_id: int, raw: dict) -> dict:
        p = {k: v for k, v in raw.items() if k not in ("type", "_names", "index")}
        if "area" in p:
            x1, y1, x2, y2 = p.pop("area")
            p.update(area_x1=x1, area_y1=y1, area_x2=x2, area_y2=y2)
        if "location" in p:
            x, y = p.pop("location")
            p.update(location_x=x, location_y=y)
        if "quantity_float" in p:
            p["quantity"] = p.pop("quantity_float")
        allowed = set(dataset.attributes[type_id])
        unknown = set(p) - allowed
        if unknown:
            raise ValueError(f"Unknown params {sorted(unknown)}; allowed: {sorted(allowed - {'effect_type', 'condition_type'})}")
        out = {}
        for k, v in p.items():
            ds = _presentation(dataset, type_id, k)
            if ds == "VariableId":
                out[k] = self.variable(v)
            elif ds == "TriggerId" or k == "trigger_id":
                out[k] = self.trigger(v)
            elif k.startswith("message") or k in ("sound_name", "xs_function"):
                out[k] = str(v)
            else:
                out[k] = resolve_dataset_value(ds, v)
        _check_fractional_quantity(dataset, type_id, out)
        return out


def _check_fractional_quantity(dataset, type_id: int, params: dict) -> None:
    """Verified in game: a fractional quantity on an integer attribute is truncated, so
    'MULTIPLY HIT_POINTS by 1.5' silently becomes 'multiply by 1'. Only attributes the engine
    stores as floats (speed, rate of fire, work rate...) accept fractions."""
    q = params.get("quantity")
    if not isinstance(q, float) or q.is_integer():
        return
    from AoE2ScenarioParser.datasets.trigger_lists import ObjectAttribute
    attr = params.get("object_attributes")
    if attr is not None and "quantity_float" in dataset.attributes[type_id] \
            and ObjectAttribute._storage_type(attr) == "float":
        return
    name = ObjectAttribute(attr).name if attr is not None else "this parameter"
    raise ValueError(f"quantity {q} would be truncated: {name} is an integer value. Use a whole "
                     f"number, e.g. operation ADD with the computed amount instead of MULTIPLY by {q}.")


def add_condition(trigger, spec: dict, resolver: Resolver):
    member = ConditionId[spec["type"].upper()]
    params = resolver.params(condition_dataset, member.value, spec)
    return getattr(trigger.new_condition, member.name.lower())(**params)


def add_effect(trigger, spec: dict, resolver: Resolver):
    member = EffectId[spec["type"].upper()]
    params = resolver.params(effect_dataset, member.value, spec)
    return getattr(trigger.new_effect, member.name.lower())(**params)


def _apply_fields(trigger, spec: dict) -> None:
    for f in TRIGGER_FIELDS:
        if f in spec and f != "name":
            v = spec[f]
            setattr(trigger, f, int(v) if f in BOOL_FIELDS else v)


def add_triggers(scenario, specs: list[dict], create_variables: bool = True) -> list[int]:
    """Create triggers from dicts. Two passes so triggers can reference each other by name."""
    tm = scenario.trigger_manager
    created = []
    for spec in specs:
        t = tm.add_trigger(spec["name"])
        _apply_fields(t, spec)
        created.append(t)
    resolver = Resolver(scenario, create_variables, {t.name: t.trigger_id for t in created})
    for t, spec in zip(created, specs):
        for c in spec.get("conditions", []):
            add_condition(t, c, resolver)
        for e in spec.get("effects", []):
            add_effect(t, e, resolver)
    return [t.trigger_id for t in created]


def update_trigger(scenario, index: int, spec: dict, create_variables: bool = True) -> dict:
    """Patch fields; if 'conditions'/'effects' are given they replace the existing lists."""
    t = scenario.trigger_manager.get_trigger(index)
    if "name" in spec:
        t.name = spec["name"]
    _apply_fields(t, spec)
    resolver = Resolver(scenario, create_variables)
    if "conditions" in spec:
        t.conditions = []
        for c in spec["conditions"]:
            add_condition(t, c, resolver)
    if "effects" in spec:
        t.effects = []
        for e in spec["effects"]:
            add_effect(t, e, resolver)
    return trigger_to_dict(t)


def find_trigger(scenario, ref: int | str):
    if isinstance(ref, int) or str(ref).isdigit():
        return scenario.trigger_manager.get_trigger(int(ref))
    for t in scenario.trigger_manager.triggers:
        if t.name == ref:
            return t
    raise KeyError(f"No trigger '{ref}'")
