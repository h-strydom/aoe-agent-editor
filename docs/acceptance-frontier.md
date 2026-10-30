# Acceptance test: The Frontier Fort

A cold build of an idea the toolkit had not seen, using only the skills, `guide()`, `blocks_list()`
and the CLI. The spec is `examples/frontier/campaign.yaml`.

> A three-mission campaign about defending a frontier river fort. M1: escort a supply caravan
> along a river road to the fort while raiders attack; losing all carts fails. M2: hold the fort for
> 20 minutes against waves crossing at two fords; carts that arrived in M1 give bonus starting
> resources. During M2 a decision popup picks rebuilding the bridge (+economy) or burning it (fewer
> waves). M3: a counter-attack on the enemy camp, shaped by that choice.

**Result:** compiles with `test_mode`, `xs_ok: true` for all 3 missions, previews checked, 59 tests
still pass. Not playtested in game, so everything in "Unverified engine behaviour" below is still open.

## Status after the follow-up fixes (2026-10-30)

The spec was rewritten with the new features and compiles with no warnings.

| # | Gap | Status |
|---|---|---|
| 1 | Escort / convoy | **Fixed:** `escort` block (route, speed, arrival count, Done/Lost hooks, bank store) |
| 2 | Waves that hunt moving units | **Fixed:** `waves` `chase: {player, unit}` (XS rule); unverified in game |
| 3 | Decision block | **Fixed:** `choice` block (stored answer, timeout default) |
| 4 | Gating blocks; generated trigger names | **Fixed:** `when:` on every block; each block doc lists its trigger names |
| 5 | Per-unit bonuses, showing a variable | **Fixed:** `perk_effects` doc covers it; `say_var` helper |
| 6 | Bridges | Open |
| 7 | Steerable rivers / fixed fords | Open (current behaviour documented) |
| 8 | Sharing a map across missions | **Fixed:** top-level `defaults:` (dicts merge one level) |
| 9 | `units` with `at:` stacking | **Fixed:** `count:` and `min_dist:`; entries never share a tile |
| 10 | Test mode and travel speed | Documented, not automated |
| 11 | `Option1` rejected | **Fixed:** enum names match case-insensitively |
| 12 | Raw-trigger errors without location | **Fixed:** errors name mission, trigger, condition/effect index and type |
| 13 | Unknown keys ignored | **Fixed:** reported in `warnings` (`x-*` keys allowed) |
| 14 | CLI tracebacks | **Fixed:** one-line `error: ...`; `--debug` for the traceback |
| 15 | Partial output on failure | **Fixed:** builds in a staging folder |
| 16 | `map_get` / `enum_values` shapes | **Fixed:** `map_get(area=...)`; `enum_values(name=...)` alias |
| 17 | `lookup` ranks enums first | **Fixed:** units and buildings rank above enums |
| 23–25 | river bbox area, per-player resources, preview glyphs | Open |
| 26 | Stacked spawns not warned | **Fixed:** compile warning; triggers skill points at `spawn` |
| 27 | Helpers can't be spliced | **Fixed:** list results splice into lists |
| 28 | Misleading `scenario_open` error | **Fixed:** lists both paths it tried |
| new | Blocks can't reference raw triggers | **Fixed:** raw triggers are created as shells before the blocks |

## The design as built (first version)

All three missions share one 144×144 river valley (`<<: *valley`: same seed, size and river). The
river runs across the middle with fords at x≈48 and x≈98, the fort sits on the south-east bank and
the raiders live north of the river. The fords the caravan passes in M1 are where the waves cross in
M2 and where you cross in M3.

| Mission | Goal | Mechanics | Bank |
|---|---|---|---|
| 1 The River Road | Bring 5 supply carts to the fort | carts auto-move (`task_object MOVE`, speed 0.55); two `waves` blocks hit road waypoints near each ford; a looping trigger removes one cart per second in the fort and counts it; all lost with 0 arrived means defeat, otherwise victory | writes `carts_arrived` |
| 2 The Two Fords | Survive 20 min | `survive`, escalating `waves` alternating the two ford spawns, `lose_if_destroyed` CASTLE, `perk_effects` +100F/+100W/+50G per cart, a decision at 8:00 | reads `carts_arrived`, writes `bridge_choice` (1 rebuilt, 2 burned) |
| 3 Across the River | Destroy every building in the raider camp | `objective` (P2 buildings in `enemy_camp` = 0), `Counter Raid` waves always; `Bridge Raid` waves switched off when burned; rebuilt gives +400W, +400G, 4 villagers and a trade cart | reads `bridge_choice` (default 1) |

## Gaps, ranked

Each entry gives what I needed, what I did instead, and a suggested fix. **[fixed]** means the
doc was corrected in this commit.

### Missing blocks and tools

1. **No escort / convoy block.** *Needed:* units that travel a route on their own, a count of how
   many arrive, failure when all are lost, and the count stored to the bank. *Did:* five raw
   triggers in M1: a speed change, `task_object` MOVE, a looping "Cart Unloads" (remove 1 cart in
   the fort, +1 var), "Caravan Lost" and "Caravan Done" (+ a delayed victory). The arrival counter
   needs `remove_object max_units_affected: 1`, which isn't obvious. *Fix:* an `escort` block:
   `{units: {TRADE_CART_FULL: 5}, start, waypoints: [...], destination, speed, count_var, store_key,
   min_arrived: 1, on_fail, on_done}`. It should expose `<name> Done` / `<name> Lost` triggers like
   `survive` does.

2. **`waves` can only target a fixed area.** *Needed:* raiders that hunt the moving carts. *Did:*
   two `waves` blocks aimed at road waypoints (`way_west`, `way_east`), timed to roughly when the
   carts pass. Raiders that arrive late attack-move to an empty waypoint and loiter there, and the
   keep-alive keeps sending them back to it. *Fix:* `target_units: <type or class>` on `waves`, with
   the keep-alive re-targeting the nearest matching unit (XS `xsGetObjectCount` /
   `xsTaskAmount`, or a per-unit `task_object` on a reference).

3. **No decision block.** *Needed:* a 2-option popup whose answer sets a variable and is stored.
   *Did:* three raw triggers (`create_decision`, then two `decision_triggered` triggers each doing
   set var + `store_key_value` + chat). There's no default if the player never answers; M3 falls back
   to `bridge_choice` 1 through `bank_load`'s default. *Fix:* a `choice` block:
   `{at, prompt, options: [{label, value, effects}], var, store_key, default, timeout_sec}`.
   `boon_offers` already does half of this, with random pairs.

4. **Blocks can't be gated on a variable.** *Needed:* "fewer waves if the bridge was burned".
   *Did:* split the waves into two blocks and added a raw trigger that deactivates `Bridge Raid 1..3`
   when `bridge_choice == 2`. Those trigger names are undocumented; I guessed `<name> <n>` and
   confirmed with `triggers_list`. *Fix:* (a) a common `when: [conditions]` param on every block
   (`bank_store` already has `conditions`); (b) list the generated trigger names in each block's
   `blocks_list` doc, as `survive` does for `<name> Complete`. `waves` makes `<name> 1..N` and
   `<name> Keepalive`; `perk_effects` makes `<name> L1..Ln`.

5. **Per-unit bonuses read like shop perks.** *Needed:* "+X resources per cart delivered". *Did:*
   `perk_effects` with five identical levels through a YAML anchor. It works, but nothing says
   `perk_effects` is the general "apply N times for var = N" tool. *Fix:* mention that use in its
   doc, or add a `per_var` helper that emits `modify_resource_by_variable` with a multiplier. Also,
   showing a variable in a message (e.g. "5 carts delivered") needs hand-written XS
   (`xsChatData("%d")`). A `{$helper: say_var, text: "Carts: %d", var: carts_arrived}` would cover it.

6. **No bridges.** *Needed:* an old bridge to rebuild or burn. *Did:* kept it narrative. Only raw
   pieces exist (`BRIDGE_A_TOP/MIDDLE/BOTTOM`, `*_BROKEN_*`, `BRIDGE_PIECE_*`), with nothing on
   orientation, footprint, or whether they make water passable. *Fix:* `water[].bridges: [{at: 0.5,
   state: intact|broken}]` in the map spec, returning `river_1_bridge_1`, plus an engine-facts
   playtest of whether `kill_object` / `create_object` on bridge pieces changes passability at runtime.

7. **Rivers can't be steered.** `start`/`end` take only compass names (a `[x, y]` crashes with
   `'list' object has no attribute 'lower'`), the river always passes through the map centre, and
   ford positions are random. *Did:* adapted the layout to the river (left to right across the
   middle) and read the ford areas from a trial `map_generate`. *Fix:* accept `[x, y]` and
   `waypoints`, and `fords: [{at: 0.33}, {at: 0.66}]`. **[fixed]** documented the current behaviour.

8. **No official way to share a map across missions.** *Did:* a top-level `valley: &valley` and
   `map: {<<: *valley, ...}`. It worked (identical river and fords in all three missions) only
   because unknown top-level keys are ignored (see 13). *Fix:* a documented top-level `defaults:` or
   `maps:` section, and mention the merge-key pattern in `guide("campaign-spec")`.

9. **`units: [{at: area}]` stacks everything on one tile.** Five M3 camp guards ended up on the
   camp centre. *Did:* explicit `x, y`. *Fix:* `count: 5` + spread (ring or grid inside the area),
   like `create_object` × N in `waves`.

10. **Test mode doesn't scale travel.** M1 is paced by cart speed (~5 min), but at ×0.1 all
    raids fire in the first 30 s while the carts are still near the start. *Fix:* in test mode also
    multiply `MOVEMENT_SPEED` for units the spec lists (e.g. `test_mode: {speed_units: [TRADE_CART_FULL]}`),
    or document that movement-paced missions need `time_scale: 1`.

### Bugs and wrong error messages

11. **`decision_option: Option1` is rejected** with `'Option1' is not a DecisionOption. Options:
    ['Option1', 'Option2']`. `OPTION1` and `option1` fail too, so no name works, only `1`/`2`. The
    resolver seems to upper-case the input but compare against the mixed-case member names. *Did:*
    integers. *Fix:* case-insensitive match in `resolve_dataset_value`. **[fixed]** noted in the
    triggers skill.

12. **Raw-trigger errors don't say where.** Block errors read `[a] block 0 (survive): ...`, but a
    bad value in `triggers:` gives a bare `KeyError` with no mission or trigger name. The builder skill
    claimed "errors name the mission and block". *Fix:* wrap `add_triggers` like blocks:
    `[siege] trigger 'Bridge Rebuilt' condition 0: ...`. **[fixed]** the skill text now says only block errors do.

13. **Unknown keys are ignored silently.** A mission with `trigers:` compiles with `ok: true` and
    no triggers. Block params *are* checked (`unexpected keyword argument 'minuts'`). *Fix:* warn on
    unknown mission and top-level keys in `build_report.json` (allowing `x-*` or a documented
    `defaults:` for anchors). **[fixed]** noted in the builder skill.

14. **The CLI prints full Python tracebacks** for every tool error (bad point name, wrong param
    name, a missing handle). The useful line is the last one. *Fix:* catch exceptions in `cli.py`
    and print `error: <message>` (keeping `--debug` for the traceback).

15. **A failed compile leaves partial output.** The first compile (which failed in M2) still wrote
    M1's scenario, so the next run left a `.bak-<timestamp>` in `out/frontier`. *Fix:* build
    into a temp directory and move into place on success, or skip `.bak` inside `out_dir`.

16. **Inconsistent parameter shapes.** `map_get` takes `x1, y1, x2, y2` while every other tool
    takes `area: [x1, y1, x2, y2]`; `enum_values` takes `dataset` (I guessed `name`). *Fix:* accept
    `area` in `map_get`; alias `name` in `enum_values`.

17. **`lookup("trade")` hides the units.** The top 25 are mostly enums; the trade cart units
    (`TRADE_CART_FULL` / `TRADE_CART_EMPTY`) only show with `kinds: ["unit"]` and the query "cart".
    *Fix:* rank units and buildings before enums, or group results by kind.

### Docs

18. **[fixed]** The spec guide said `position: center|[x,y]|<compass>`. A compass word errors; the
    real forms are `edge:<dir>[:inset]`, `player<N>` or a zone name.
19. **[fixed]** The compass convention wasn't documented anywhere outside `src/`: `w` is tile (0, 0),
    the four letters are *corners* and `nw/ne/se/sw` are edges. My first map put the river corner
    to corner and the "east" player in a corner, sitting in the river. I had to read
    `src/aoe2ed/mapgen/compass.py` to understand it. Now in `guide("campaign-spec")`.
20. **[fixed]** River behaviour (compass-only ends, through the centre, `river_<n>_ford_<k>`
    areas) is now in the guide.
21. **[fixed]** The builder skill told CLI users to `scenario_open` and then `triggers_list`, but
    handles don't survive between `aoe2ed call`s. It now points to `aoe2ed script`.
22. **[fixed]** `compile_campaign`'s doc pointed to a non-existent `specs/campaign-spec.md`, and
    `map_generate`'s pointed to `aoe2ed.mapgen.MapSpec` in `src/`. Both now point to `guide('campaign-spec')`.
    (`compiler.py`'s module docstring still mentions `MapSpec`; it's internal.)
23. **The `river_1` area is the river's bounding box**, which for a diagonal river is the whole
    map. Using it as a block area would be a mistake. *Fix:* leave it out of the returned areas, or
    document it as "bbox only".
24. **Resources are placed for every player.** The M3 raider camp (no villagers) got its own gold
    and stone piles. *Fix:* allow `resources` per entry in `players: [...]`.
25. **Previews draw every unit as the same dot,** so carts, knights and archers can't be told apart
    when checking an escort start. *Fix:* a shape per class (cart, cavalry, infantry, ranged), or
    label `caption`ed units.

26. **Several units spawned on one tile become one unit.** A Crucible playtest on the same day
    showed that `create_object` effects aimed at the same tile place only one unit. My first M3
    "bridge rebuilt" bonus created 4 villagers at `location: fort`, so it would have given one.
    Nothing at compile time warns about this. *Did:* the `spawn` helper (015f8ec, landed during this
    test) in its own trigger, see 27. *Findability:* easy if you read `guide("campaign-spec")`
    (Directives) or `blocks_list()`, which lists it as a helper. But the triggers skill's
    "Spawn and attack" pattern still says `create_object` × N and doesn't mention it, and that is where
    a raw-trigger author looks. *Fix:* point that pattern at `spawn`, and warn at compile time when two or
    more `create_object` effects in one trigger share a location.

27. **A helper that returns a list can't be spliced into a longer list.** `effects: [{modify_resource...},
    {$helper: spawn, ...}, {display_instructions...}]` crashes with
    `TypeError: list indices must be integers or slices, not str`, with no mission or trigger named.
    `spawn` only works as the entire `effects:` value. *Did:* moved the villagers into a separate
    trigger, `Bridge Rebuilt Settlers`, with the same condition. *Fix:* flatten list-valued helper
    results inside lists in `_expand`, or support `{$splice: ...}`. Until then, say "use it as the
    whole `effects:` value" in the guide.

28. **`scenario_open` with a relative path that doesn't exist** reports a `FileNotFoundError` for
    `<profile>/resources/_common/scenario/out/frontier/...`, so it looks as if the tool looked in the
    game profile instead of the working directory. The real cause was that the file hadn't been built.
    *Fix:* say both places it tried.

## Unverified engine behaviour this campaign relies on

None of these are in `guide("engine-facts")`. Check them in the first playtest and record the results.

- `task_object` with `action_type: MOVE` over an area moves player-owned trade carts to a point (M1).
- `modify_attribute MOVEMENT_SPEED SET 0.55` on `TRADE_CART_FULL` slows existing carts.
- `remove_object` with `max_units_affected: 1` removes exactly one unit per firing (M1 counter).
- At t=0, `Bank Load` (earlier trigger) has filled `bridge_choice` before the `variable_value`
  triggers after it run (M3). If not, they need a 1 s timer.
- `deactivate_trigger` on a not-yet-fired timer trigger stops it from firing (M3 Bridge Raid).
- `own_fewer_objects` with `object_type: BUILDING` + area counts P2's camp buildings (M3 objective).
- Whether a decision popup stays up until it's answered, or can be dismissed without a choice (M2).

## What worked well

- `map_generate` with named zones plus the preview made layout iteration fast (four trial maps).
  Same seed with the same river gave identical fords across missions, as promised.
- `waves`, `survive`, `lose_if_destroyed`, `bank_load`, `perk_effects`, `objective` and `anchor`
  covered most of M2 and M3 without raw triggers.
- `trigger_id` by name resolves to block-generated triggers (`Bridge Raid 1` → id 9).
- `{$secs: N}` and `area:`/`location:` shorthands in raw triggers worked first time.
- Block param errors are clear and name the mission and block.
