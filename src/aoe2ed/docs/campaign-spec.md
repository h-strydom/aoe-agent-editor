# Campaign spec

A campaign spec is a YAML (or JSON) file that `compile_campaign` turns into scenarios, PNG
previews, a `.aoe2campaign` and `build_report.json`. Two full working examples:
`examples/crucible/campaign.yaml` (roguelite: hub shop plus survival runs) and
`examples/frontier/campaign.yaml` (story campaign: escort, siege with a choice, counter-attack).

```yaml
name: my_campaign        # internal name. The campaign bank is scoped by it, so never rename a released campaign
title: My Campaign       # optional
test_mode: {time_scale: 0.1}   # used when compiling with test_mode=true
defaults:                # optional: keys every mission inherits. Dict values (map, players, options...)
  map: {size: 144, seed: 11, water: [...]}   # merge one level with the mission's own, so missions can
  options: {victory_condition: CUSTOM}       # share one map and override single fields
missions:                # play order. Mission N+1 unlocks after mission N is won
  - id: m1               # your reference
    file: my_campaign_1_intro    # scenario file name, no extension. Prefix with the campaign name
    # --- map: one of
    map: {...}           # generated map, see "Map spec" below
    base: some_scenario  # or start from an existing scenario (path or profile name)
    map_size: 120        # or a blank map
    areas:  {name: [x1, y1, x2, y2]}   # extra named rectangles (tiles, inclusive)
    points: {name: [x, y]}
    # --- setup
    players: {1: {civilization: BRITONS, starting_age: FEUDAL, food: 200, population_cap: 200}, 2: {...}}
    diplomacy: [{player: 1, others: [2], state: ENEMY}]     # ALLY | NEUTRAL | ENEMY, mutual by default
    options: {victory_condition: CUSTOM}                    # always CUSTOM when triggers decide the ending
    messages: {instructions: "...", hints: "...", victory: "...", loss: "...", history: "..."}
    units: [{player: 1, type: KNIGHT, x: 10, y: 12}, {player: 1, type: CHAMPION, at: plaza, caption: Hero},
            {player: 2, type: CROSSBOWMAN, at: camp, count: 5, min_dist: 2}]   # count: spread over free tiles
    # --- logic, applied in this order
    blocks:   [{use: <block>, when: [<conditions>]?, ...params}]   # see blocks_list()
    triggers: [<trigger dict>]              # raw triggers (triggers_add format)
    xs: "..."                               # extra XS (lint with xs_check first)
    telemetry: true | {players: [1, 2], track_vars: [...], interval_sec: 10, events: {"Trigger name": 1}}
```

Keys starting with `x-` are ignored (use them for YAML anchors). Any other unknown key is reported
in `build_report.json` → `warnings`, so a typo like `trigers:` doesn't silently do nothing.

## Blocks
`blocks_list()` documents every block, including the trigger names it creates (hook into them with
`activate_trigger` or `deactivate_trigger`). The ones you'll use most:
- **Structure:** `survive`, `objective`, `lose_if_destroyed`, `anchor`, `run_end`
- **Enemies:** `waves` (+ `{$helper: escalating}`), with `chase: {player, unit}` to hunt moving units
- **Story:** `escort` (a convoy that drives itself, with arrival count and Done/Lost hooks) and `choice`
  (a two-option decision whose answer is stored, with a timeout default)
- **Progression:** `bank_load`, `bank_store`, `pad_shop`, `perk_effects` (also handy for "apply once per
  unit of a variable"), `boon_offers`
- **Testing:** `telemetry` (or the mission-level `telemetry:` key)

`when: [conditions]` on any block adds those conditions to every trigger the block creates, which
switches the whole block on a variable, e.g. extra raids only if `bridge_choice == 1`. One-shot
triggers then fire when the condition becomes true, even if their timer passed earlier.

Raw `triggers:` exist before the blocks run, so blocks can reference them by name (for example
`done_effects: [{type: activate_trigger, trigger_id: My Victory}]`). They are still placed after the
block triggers in the final list.

## Directives (usable inside block params and triggers)
- `{$helper: escalating, ...}`, `{$helper: earn, var: earned, amount: 10}`, `{$helper: var_to_resource, var: x}`,
  `{$helper: resource_to_var, var: x}`: replaced by the helper's result. A helper that returns a list
  (`spawn`, `escalating`) inside a list is spliced in, so it can sit among other effects.
- `{$helper: say_var, text: "Carts delivered: %d", var: carts_arrived}`: a chat line showing a variable.
- `{$helper: spawn, unit: KNIGHT, count: 5, at: player1_base, min_dist: 4}`: N `create_object` effects on
  distinct tiles. Use it whenever you create more than one unit, because effects aimed at the same tile place only one.
- `{$secs: 2700}`: game seconds, scaled in test mode like every block timer. Use it for every
  raw `timer` condition, or test builds will be out of sync.
- `area: <name>` and `location: <name>` resolve to named areas and points (a point name falls back to
  the centre of an area with that name).
- YAML anchors (`&eco` / `*eco`) are handy for repeating effect lists.

## Map spec (`map:`)
Every field is optional. The same seed always gives the same map.

**Compass:** names follow the in-game diamond view, not the square preview. Tile (0, 0) is the
**w** corner, (max, 0) **n**, (max, max) **e**, (0, max) **s**. The edges between them are
**nw** (y = 0), **ne** (x = max), **se** (y = max) and **sw** (x = 0). So `edge:e` is a corner and
a river from `sw` to `ne` runs left to right across the preview. The preview labels the corners.
```yaml
size: 144                 # 36..480
seed: 45
biome: temperate          # temperate | autumn | pine | desert | snow | jungle | mediterranean | steppe
players: 2                # or [{position: center|[x,y]|edge:<dir>[:inset]|player<N>|<zone name>,
                          #      base_radius: 13, villagers: 6, town_center: true, scout: true}]
player_layout: ring       # ring | center | line
extra_players: 1          # active players without a base (wave enemies). Anchor them!
forests:   {coverage: 0.2, clumps: 14, border: 4, player_woodlines: 3, stragglers: 4}
resources: {gold: [8, 6], stone: [6], berries: 6, sheep: 4, deer: 4, neutral_gold: [6], neutral_stone: [5]}
water:     [{kind: lake, name: lake_w, radius: 7, center: [x, y], fish: 4},
            {kind: river, start: nw, end: se, width: 4, fords: 2}]   # start/end: compass names only;
                          # the river always runs start -> map centre -> end. Fords become river_<n>_ford_<k>
elevation: {hills: 6, height: [2, 4], radius: [6, 11]}
cliffs:    [{points: [[20, 20], [40, 30]]}]   # experimental
roads:     [{points: [spawn_north, player1], width: 3, wobble: 1.0}]
zones:                    # named areas, returned to blocks
  - {name: spawn_north, kind: edge, side: n, width: 14, depth: 12}
  - {name: choke_n, kind: choke, between: [spawn_north, center], at: 0.45, gap: 7, wall_length: 20}
  - {name: plaza, kind: circle, center: center, radius: 7, terrain: ROAD, flat: true}
  - {name: arena, kind: rect, rect: [10, 10, 30, 30]}
units: [{unit: MARKET, position: plaza, player: 1, offset: [0, 11]}]
```
Generated areas always include `player<N>_base`, plus every zone, lake and hill. Look at the
PNG preview before going further.

## Rules of thumb
- One mission = one clear goal. Put the hub/meta mission first when the campaign has metaprogression.
- Wave-only enemies need `{use: anchor, player: N}`, or the game ends at t=0.
- Load bank keys at mission start and store them at the end (or on purchase). Store unlocks as flags (= 1), never as running counters.
- Missions that must keep their stores should end in victory. `run_end` does this for roguelite runs.
- Don't use fractional quantities on integer stats such as HP or attack; the compiler rejects them.
- Check `guide("engine-facts")` before relying on any engine behaviour, and add to it after playtests.
- Errors name the mission and block or trigger: `[siege] block 3 (waves): ...`,
  `[m1] triggers: trigger 'Bridge' effect 2 (create_object): ...`. A failed compile writes nothing.
- Test mode scales time, not movement. A mission paced by unit travel (escorts) needs a real-speed
  playtest, or a spec-level speed tweak while testing.
