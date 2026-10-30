"""Shops and perks.

pad_shop: the buyer walks a unit onto a pad (flag + caption) to buy the next level of a perk with
a resource. Pure triggers, no custom technologies needed, so it works on every map and civ.
perk_effects: apply owned perk levels (from bank-loaded variables) at mission start.
"""
from __future__ import annotations

from .base import Ctx


def pad_shop(ctx: Ctx, *, perks: list[dict], buyer: int = 1, buyer_unit: str | int | None = None,
             resource: str = "GOLD_STORAGE", exit_point=None, store_on_buy: bool = True,
             marker: str = "FLAG_A", on_buy: list[dict] | None = None, name: str = "Shop") -> dict:
    """perks: [{"key": "perk_eco", "label": "Eager Hands", "pad": area, "costs": [100, 200, 400],
               "description": "+10% gather rate per level"}]
    Each perk keeps its level in a variable named like its key (load it from the bank first).
    Buying level L needs level == L-1 and resource >= costs[L-1]; it deducts the cost, raises the
    level, stores the key (if store_on_buy) and teleports the buyer to `exit_point`.
    on_buy: extra effects after every purchase, e.g. store the remaining currency right away so
    quitting the mission cannot keep perks without paying for them.

    Triggers created per perk: "<name> <key> L<n>" (buy), "<name> <key> L<n> poor", "<name> <key> maxed"."""
    ex, ey = ctx.point(exit_point) if exit_point is not None else (None, None)
    created = []
    for perk in perks:
        key, label, costs = perk["key"], perk["label"], perk["costs"]
        var = ctx.var(perk.get("var", key))
        pad = ctx.area(perk["pad"])
        px, py = (pad[0] + pad[2]) // 2, (pad[1] + pad[3]) // 2
        desc = perk.get("description", "")
        caption = f"{label} ({'/'.join(map(str, costs))})"
        ctx.scenario.unit_manager.add_unit(player=0, unit_const=_obj(marker), x=px + 0.5, y=py + 0.5,
                                           caption_string=caption)
        in_pad = {"type": "objects_in_area", "source_player": buyer, "area": list(pad), "quantity": 1,
                  **({"object_list": buyer_unit} if buyer_unit is not None else {"object_type": "MILITARY"})}
        bounce = ([{"type": "teleport_object", "source_player": buyer, "area": list(pad), "location": [ex, ey]}]
                  if ex is not None else [])
        for lvl, cost in enumerate(costs, 1):
            t = f"{name} {key} L{lvl}"
            effects = [
                {"type": "modify_resource", "tribute_list": resource, "source_player": buyer,
                 "quantity": cost, "operation": "SUBTRACT"},
                {"type": "change_variable", "variable": var, "operation": "SET", "quantity": lvl},
                *([{"type": "store_key_value", "variable": var, "message": key}] if store_on_buy else []),
                {"type": "display_instructions", "source_player": buyer, "display_time": 6,
                 "message": f"Bought {label} level {lvl}. {desc}".strip(), "instruction_panel_position": 0},
                *bounce,
                *(on_buy or []),
            ]
            ctx.trigger(t, [in_pad,
                            {"type": "accumulate_attribute", "attribute": resource, "source_player": buyer,
                             "quantity": cost},
                            {"type": "variable_value", "variable": var, "comparison": "EQUAL", "quantity": lvl - 1}],
                        effects, looping=True)
            created.append(t)
            # Not enough currency: tell the player and push them off the pad.
            ctx.trigger(f"{t} poor", [
                in_pad,
                {"type": "accumulate_attribute", "attribute": resource, "source_player": buyer,
                 "quantity": cost, "inverted": True},
                {"type": "variable_value", "variable": var, "comparison": "EQUAL", "quantity": lvl - 1}],
                [{"type": "display_instructions", "source_player": buyer, "display_time": 4,
                  "message": f"{label} level {lvl} costs {cost}.", "instruction_panel_position": 0}, *bounce],
                looping=True)
        ctx.trigger(f"{name} {key} maxed", [in_pad,
                    {"type": "variable_value", "variable": var, "comparison": "LARGER_OR_EQUAL",
                     "quantity": len(costs)}],
                    [{"type": "display_instructions", "source_player": buyer, "display_time": 4,
                      "message": f"{label} is fully upgraded.", "instruction_panel_position": 0}, *bounce],
                    looping=True)
    return {"triggers": created}


def perk_effects(ctx: Ctx, *, var: str, levels: dict[int, list[dict]], name: str | None = None) -> dict:
    """At mission start, apply the effects of every level the player owns:
    levels: {1: [effects...], 2: [effects...]} — level L's effects apply if var >= L (cumulative).
    Give each level only its increment (e.g. +10% per level).
    Also the general tool for "apply N times for var = N", e.g. +100 food per cart delivered:
    levels 1..5 with the same effects.

    Triggers created: "<name or 'Perk <var>'> L<n>"."""
    var = ctx.var(var)
    created = []
    for lvl, effects in sorted(levels.items()):
        t = f"{name or 'Perk ' + var} L{lvl}"
        ctx.trigger(t, [{"type": "variable_value", "variable": var, "comparison": "LARGER_OR_EQUAL",
                         "quantity": int(lvl)}], effects)
        created.append(t)
    return {"triggers": created}


def _obj(name):
    from ..datasets import object_id
    return object_id(name)
