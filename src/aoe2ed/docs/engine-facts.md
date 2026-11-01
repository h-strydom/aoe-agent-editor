# Engine facts (verified in game)

Behaviour of AoE2 DE that blocks and skills rely on. Each entry says how it was verified.
Add to this file whenever a playtest teaches something; never record guesses here.

## Files and loading
- Return of Rome scenarios are the same 1.59 format with header variant 2 (AoE2 is 1); RoR keeps user
  files under `<profile>/modes/Pompeii/resources/_common/`. RoR has its own data file: ids differ
  (74 = Short Swordsman, 4 = Bowman, 93 = Hoplite) but terrains and gaia objects (trees, gold, stone,
  berries, Town Center 109, villager 83) match AoE2. *Editor-saved RoR scenarios + both data files read
  with genieutils-py, 2026-10-31.*
- Generated RoR scenarios and campaigns (variant 2, installed under `modes/Pompeii`) show up in RoR's own
  lists and play like the AoE2 builds: embedded XS runs, waves, timer, decision popup, victory, the hub/run
  loop and the campaign bank (`crucible_ror`: `meta_points` and a bought perk persisted). RoR writes `.xsdat`
  telemetry to the **shared** `<profile>/profile/` folder, named after the campaign like AoE2.
  *RoR smoke + crucible_ror playtest, 2026-10-31.*
- Scenarios written by AoE2ScenarioParser 0.9.8 at version 1.59 load and run in the current
  game (build 101.103.54800, Oct 2026). *Smoke test, 2026-10-30.*
- `.aoe2campaign` layout is documented in `src/aoe2ed/campaign.py`; the writer reproduces all 47
  campaigns on the dev machine byte for byte, and generated campaigns load. *Round-trip + earlier tests.*

## Campaign screens
- A campaign's screen (background map, one flag/icon button per mission, title) comes from
  `<name>_layout.json`, its intro slideshows from `<name>.json`, next to `<name>.aoe2campaign`.
- The game reads them **only from a mod** (`<profile>/mods/local/<Mod>/modes/Pompeii/resources/_common/campaign/`
  for RoR); beside a campaign in the profile's own campaign folder they are ignored.
- The campaign's **internal name must equal the file name** (`<name>`), as in the official files
  (`acam1.aoe2campaign` holds "acam1"); with any other internal name the layout isn't found.
- Literal text works in the layout's title; the game's own materials (RoR: CampaignBackgroundAscent,
  CampaignIconVillagerHunter, ...) work from a mod's layout. Without a layout, the default book shows
  at most 9 mission flags. *RoR layout tests (Ascent of Egypt layout on a generated 12-mission campaign),
  2026-11-01.*

## XS
- XS embedded in a Script Call effect (the parser's XS trigger) compiles and runs, including
  `rule` blocks. *Smoke test: chat line at t=0.*
- Script Call messages compile in trigger order and XS requires definition before use, so the
  shared XS trigger must be the first trigger (`Ctx.flush_xs` does this).
- Int literals are limited to 9 digits. *xs-check, matches engine.*
- `xsGetRandomNumber*` gives different values on every fresh start, both in campaigns and in standalone
  scenarios. So XS randomness is usable for rolls (unlike the Random civ setting in campaigns).
  *RNG probe, 2 fresh starts each, 2026-10-31.*
- `xsCreateFile` writes `<profile>/profile/<scenario file name>.xsdat` for a standalone scenario, but
  `<campaign name>.xsdat` when the scenario is played inside a campaign, so all missions of a campaign share
  one file. `xsWriteInt` writes raw little-endian int32. *Smoke test + civ probe campaigns, 2026-10-31.*
- XS chat/print output does not appear in `logs/<session>/MainLog.txt`.
- `xsChatData("... %d", value)` substitutes the value. *Smoke test results message.*

## Players and victory
- A player who owns only Houses is defeated immediately; if that is the only enemy, the other
  side wins at t=0 even with victory condition Custom. Use the `anchor` block. *Smoke test.*
- A computer player with the game's default AI **resigns** once it judges the game lost (frontier
  M3: it resigned after one camp building fell), which ends trigger-driven missions early. The
  compiler now gives players 2+ "None AI" unless the spec sets `players.<n>.ai`. *Frontier playtest, 2026-10-30.*
- Civilization `RANDOM` (stored as `RANDOM-CIV`, the same value the editor writes and the parser's blank-scenario
  default) is only resolved by the **scenario lobby** (Single Player → Scenario), which rolls a civ at launch;
  Restart keeps it. **Inside a campaign, `RANDOM` and `FULL_RANDOM` always become Britons (civ 1)**, in every
  new campaign too, so random civs aren't available in campaigns. Set every civ explicitly; the compiler warns.
  *Editor-saved scenario compared field by field + civ probe in 3 campaigns (XS read civ id 1), 2026-10-31.*
- `random_faction` works as the replacement: civ name, unique unit in a building, disabled units and bonus
  applied; with `store_key` the pick was saved (bank `faction = 2`) and loaded in mission 2.
  *Factions playtest, 2026-10-31.* To re-roll a saved pick, delete the key: `bank_set(campaign, {}, delete=["faction"])`
  with the game closed.
- Setting player 1's `REVEAL_MAP` resource (203) to 2 at start reveals the whole map with no fog; 1 = explored.
  *Frontier/probe playtest, 2026-10-31.*

## Triggers
- Timer conditions on triggers enabled at start fire at that game time (waves at 20 s and 50 s
  logged at exactly t=20/t=50). *Smoke telemetry.*
- Display Timer with message `"Survive: %d"` shows the remaining seconds. *Smoke test.*
- `create_object` + `attack_move` over the spawn area sends spawned units to the target. *Smoke
  test: all 7 wave units engaged and died.*
- Create Decision shows a two-option popup; Decision Triggered fires for the chosen option. *Smoke test.*
- Modify Attribute quantities are integers unless the attribute is stored as a float (speed, rate
  of fire, work rate...). `MULTIPLY HIT_POINTS by 1.5` became "multiply by 1" — no effect. The
  trigger layer now rejects fractional quantities on integer attributes. *Smoke test.*
- Modify Attribute HIT_POINTS ADD 15 on ARCHER took effect in game. *Smoke replay, user-confirmed.*
- `task_object` MOVE with `selected_object_ids` and queued (`queue_action`) waypoints drives player-owned
  carts along a route on their own, but the player can still select and stop them, so the `escort` block
  now disables selection by default. *Frontier playtest.*
- A looping `objects_in_area` + `remove_object` (`max_units_affected: 1`) + `change_variable` counts arrivals
  one by one correctly. *Frontier playtest: the count carried to mission 2 exactly.*
- Create Decision followed by a stored answer carries into the next mission. *Frontier playtest.*
- Several `create_object` effects at the same tile place only **one** unit ("+4 Men-at-Arms" gave 1).
  Give each unit its own tile with the `spawn` helper. *Crucible playtest, 2026-10-30.*

## Campaign bank (Store / Load / Delete Key Value)
*Verified with the kv_* test campaigns, 2026-10-19.*
- Values are int64 per campaign, stored in `profile/Player.nfp` as `PKEY:<campaign>:<key>`.
- They persist across game restarts. They are scoped to one campaign, and standalone scenarios get the default.
- The bank is not directional: any mission reads any key. Store overwrites; there is no history.
- Load Key Value returns the effect's quantity when the key is missing.
- Replaying an earlier mission asks "save your choices?"; answering No discards that visit's stores.
- Works in Return of Rome too.
- Full hub/run loop works in a generated campaign: currency earned in a run is stored, loaded as
  Gold in the replayed hub, perks bought there are stored, and the next run applies them (starting
  resources, Town Center HP). Winning and losing a run both end correctly. *Crucible playtest, 2026-10-30.*
- Open: whether stores survive a mission that ends in defeat or is quit mid-way. `run_end`
  always ends in victory to sidestep this.
