"""Campaign bank: values that persist between missions of one campaign (and across game restarts).

Engine facts (verified in game, see docs/engine-facts.md):
  - Store/Load Key Value effects read/write int64 per campaign name; standalone scenarios get defaults.
  - Not directional: any mission reads any key. A store overwrites; no history.
  - Replaying an earlier mission asks "save your choices?"; No discards that visit's stores.
  - Safe pattern: load at mission start, store at mission end. Unlocks are flags (=1), not counters.
"""
from __future__ import annotations

from .base import Ctx


def load(ctx: Ctx, keys: dict[str, dict | int], *, name: str = "Bank Load") -> dict:
    """At mission start, load keys into variables. keys: {"meta_points": {"var": "meta", "default": 0}}
    or {"meta_points": 0} (variable named like the key)."""
    effects = []
    for key, spec in keys.items():
        spec = {"default": spec} if isinstance(spec, int) else spec
        var = ctx.var(spec.get("var", key))
        effects.append({"type": "load_key_value", "variable": var, "message": key,
                        "quantity": spec.get("default", 0)})
    ctx.trigger(name, [], effects)
    return {"triggers": [name], "variables": [e["variable"] for e in effects]}


def store(ctx: Ctx, keys: dict[str, str] | list[str], *, name: str = "Bank Store",
          enabled: bool = False, conditions: list[dict] | None = None) -> dict:
    """Store variables under keys. keys: {"meta_points": "meta"} or ["meta_points"] (same-named var).
    Disabled by default: activate it from your mission-end trigger."""
    if isinstance(keys, list):
        keys = {k: k for k in keys}
    effects = [{"type": "store_key_value", "variable": ctx.var(v), "message": k} for k, v in keys.items()]
    ctx.trigger(name, conditions or [], effects, enabled=enabled)
    return {"triggers": [name]}


def var_to_resource(var: str, resource: str = "GOLD_STORAGE", player: int = 1, operation: str = "SET") -> dict:
    """Effect dict: set a player's resource from a variable (e.g. meta currency -> Gold in the hub)."""
    return {"type": "modify_resource_by_variable", "tribute_list": resource, "source_player": player,
            "operation": operation, "variable": var}


def resource_to_var(var: str, resource: str = "GOLD_STORAGE", player: int = 1, operation: str = "SET") -> dict:
    """Effect dict: copy a player's resource into a variable (e.g. leftover Gold -> meta currency)."""
    return {"type": "modify_variable_by_resource", "tribute_list": resource, "source_player": player,
            "operation": operation, "variable": var}
