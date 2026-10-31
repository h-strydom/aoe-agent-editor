---
name: aoe2-triggers
description: Reference for Age of Empires II DE scenario triggers, covering all 103 effects, 41 conditions and their parameters and enum values, plus patterns for common mechanics. Use when writing or debugging raw triggers (triggers_add, campaign spec `triggers:`), or when no building block covers a mechanic.
---

# AoE2 triggers

- `reference/effects.md` and `reference/conditions.md` list every type with its parameters. They are generated from the parser's schemas, so they match what the tools accept.
- `reference/enums.md` lists the names accepted for enum parameters.
- For a live schema with defaults, call `effect_schema(handle, type)` / `condition_schema(handle, type)`.

## How triggers run
- Each enabled trigger checks its conditions about once per second. With conditions met, it runs all effects in order. Unless `looping` is set, it then disables itself.
- Every condition must hold (AND), unless you use the `or` condition between groups.
- `timer` counts from when the trigger became active, so a trigger activated later counts from then.
- `activate_trigger` / `deactivate_trigger` chain logic. Build state machines from disabled triggers.
- Objectives: `display_as_objective`, `description`, `short_description`, `description_order`. The line ticks off when the trigger fires.
- Variables are 256 named ints (ids 0–255). Change them with `change_variable`, test them with `variable_value`, `compare_variables`. They connect to resources through `modify_resource_by_variable` / `modify_variable_by_resource`, and to XS through `xsTriggerVariable` / `xsSetTriggerVariable`.

## Patterns
- **Once at start:** no conditions.
- **Every N seconds:** `looping: true` plus `timer: N`.
- **Area entry:** `objects_in_area` with `source_player`, `area` and `quantity: 1`. Add `object_list` for a specific unit.
- **Unit death / building lost:** `own_fewer_objects` with `object_list` and `quantity: 0`, or `destroy_object` with `unit_object` (a ref).
- **Resource threshold:** `accumulate_attribute` (attribute e.g. `GOLD_STORAGE`). Add `inverted: true` for "less than".
- **Spawn and attack:** one `create_object` per unit **on distinct tiles** (effects aimed at one tile place
  only one unit: use `{$helper: spawn, unit, count, at}`), then `attack_move` with the spawn `area` and the
  target `location`. The `waves` block does all of this.
- **Two-way choice:** `create_decision` with `decision_id` plus `decision_triggered` for each option.
  `decision_option` takes 1/2 or `Option1`/`Option2`. The `choice` block wraps the whole pattern.
- **Random:** the `chance` condition, or set a variable from XS with `xsGetRandomNumberLH` (see `boon_offers`).
- **Persistence (campaign only):** `load_key_value` / `store_key_value` / `delete_key`, with the key in `message`.
- **Selecting specific placed units:** `selected_object_ids: [ref, ...]` (refs come from `units_list`).

## Gotchas (verified)
- Fractional `quantity` is truncated on integer attributes. aoe2ed rejects it, so use whole numbers.
- A player owning only Houses counts as defeated, and an all-defeated enemy means instant victory.
- `display_timer` messages and `xsChatData` support `%d`.
- See `guide("engine-facts")` for the full verified list.
