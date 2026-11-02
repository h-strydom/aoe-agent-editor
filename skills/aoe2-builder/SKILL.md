---
name: aoe2-builder
description: Build, inspect and edit Age of Empires II DE scenarios and campaigns with the aoe2-editor MCP tools. Covers compiling a campaign spec, generating maps and previews, editing triggers, units, terrain, players and XS directly, and installing into the game. Use whenever a .aoe2scenario/.aoe2campaign must be created or changed.
---

# AoE2 builder

Two ways to build, which you can mix:
- **Spec → compile** (preferred for new work): `compile_campaign(spec, test_mode, install)`.
- **Direct editing** of an open scenario: `scenario_open/new` → edit tools → `scenario_save`.

## Compile loop
1. Write or adjust the spec (see `aoe2-campaign-designer`, `guide("campaign-spec")`).
2. `compile_campaign(spec="path/campaign.yaml", out_dir="out/<name>", test_mode=true)`
   - Errors name the mission and the block or trigger/effect, e.g.
     `[m1] triggers: trigger 'Bridge' effect 2 (create_object): Unknown object 'X'`. Fix the spec, not
     the output. A failed compile leaves `out_dir` untouched.
   - Read `warnings` in the report: unknown keys (typos like `trigers:`) and several units created on
     one tile (use `spawn`) show up there.
   - Check `xs_ok` and `xs_errors` in the report; they must be clean.
3. **Look at every preview PNG** (`missions[].preview`). Check that spawns, pads, gates and bases sit where the design says, that no building sits on a road or in water, and that areas don't overlap by accident.
4. Spot-check the logic: `scenario_open(<scenario>)`, then `triggers_list` and `trigger_get(name)` for the key triggers.
5. Install: compile again with `install=true`, or call `game_install(path)`. Playtest with **aoe2-playtest**.
6. For release, compile without test_mode.

## Direct editing essentials
- Handles: every tool takes `handle` ("s1"). With the CLI, handles die with the process, so chain
  handle-based calls with `aoe2ed script steps.json` (`[{"tool": ..., "args": {...}}, ...]`), not separate `aoe2ed call`s. `scenario_save(handle, path, overwrite)` keeps a `.bak`. `install=true` writes into the game's scenario folder.
- Names work wherever ids do: units `"KNIGHT"`, players `"ONE"`/`1`, terrain `"GRASS_1"`, enums `"ADD"`. Use `lookup("pike")` to find a name and `enum_values("ObjectAttribute")` to list an enum.
- Return of Rome: `scenario_new(game="ror")` or `game: ror` in a spec. Unit, tech and civ names then resolve against RoR's own data (`lookup("bowman", game="ror")`); tools switch automatically for any open RoR scenario.
- Triggers: `triggers_add(handle, [ {name, conditions:[{type,...}], effects:[{type,...}]} ])`.
  - Shorthands: `area: [x1,y1,x2,y2]`, `location: [x,y]`, variables by name (created automatically), `trigger_id` by trigger name.
  - Look up parameters with `effect_schema(handle, "create_object")`. The full list is in `skills/aoe2-triggers`.
- Blocks on an open scenario: `block_apply(handle, "waves", params, areas={...})`.
- Maps: `map_generate(spec, out, preview)` creates a map with named areas; then `map_set_terrain` / `map_set_elevation` / `units_add` refine it. `map_preview` shows it.
- XS: `xs_check(code)`, then `xs_embed(handle, code)`. See `skills/aoe2-xs`.
- Campaign files: `campaign_build(name, [scenario paths in order], install=true)`, `campaign_read`, `campaign_extract`.
- Computer player AI: `ai_set(handle, player, spec)` with an AI spec (build order, attacks); see the `aoe2-ai` skill.
- Campaign screens (map, mission icons, intros; needed for more than 9 missions): `campaign_screens(game)` to pick an
  official screen, then `campaign_install_mod(campaign, mod, official=..., title=..., labels=[...])`, or `screen:` in
  the spec. They only load from a mod: tell the user to enable it (Mods > Installed Mods) and restart.
- Escape hatch: `run_python(code, handle)` exposes the full AoE2ScenarioParser API (`scenario.*_manager`, raw `scenario.sections`). Use it for anything no tool covers, and say so in your summary.

## Pitfalls (verified)
- Enemies that only send waves need the `anchor` block, or the game is won at t=0.
- Integer stats (HP, attack, armor) can't take fractional quantities; use ADD with a whole number.
- XS: define before use (the shared XS trigger goes first; the compiler handles it). Int literals have at most 9 digits.
- Don't edit files inside the game install folder. Write only to the profile folders (`paths_info`).
- `guide("engine-facts")` lists everything verified so far. Treat anything not in it as unverified until a playtest proves it.
