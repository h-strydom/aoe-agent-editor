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
  at most 9 mission flags. Intro slide images load from the mod's `modes/Pompeii/widgetui/` (not the mod's
  root `widgetui/`) via "SlideImageSequence": "textures/campaign/<name>/<n>/intro/%d.png", with %d counting
  from 1. *RoR layout tests (Ascent of Egypt layout on a generated 12-mission campaign), 2026-11-01.*
- An intro's (or outro's) "Sound" plays the game's own Wwise events (RoR's campaigns: `PLAY_AOECAM1_01_INTRO`)
  or a mod's own `.wem` by file name without the extension, from `resources/_common/drs/sounds` (`modes/Pompeii`
  for RoR). MP3, WAV and OGG there are ignored, but plain 16-bit PCM in a RIFF/WAVE container named `.wem`
  plays, both Wwise's PCM layout (format 0xFFFE) and an ordinary WAV renamed (`aoe2ed.audio.pcm_wem`).
  *RoR campaign intro test, 2026-11-07: both played, mono 48 kHz, files in both sounds folders; which folder
  RoR reads isn't pinned down yet.*

## Data mods
- Campaigns can use a data mod: the campaign screen (Return of Rome too) has a **Data Mod** dropdown next to AI
  Difficulty. Its tooltip: "Scenario Default will load the Data Mod with which it was created, if available." So a
  scenario records the data mod it was made with, and a campaign can depend on one. Still open: which scenario
  field records it. *User's screenshot of the RoR campaign screen, 2026-11-09.*
- Picking a data mod other than the scenario's own in that dropdown shows a warning first.
- **A chosen data mod applies in a campaign:** RoR's data file edited with genieutils-py (Hoplites 999 HP,
  Axemen 400 HP, the Greek bonuses removed) took effect in both missions. Mods > Installed Mods marks data mods
  with a gear icon. *Crucible data mod test, 2026-11-09.*
- A drop site needs two changes: `dropsites.json` makes the building accept the resource (the drop-off cursor
  shows), but each villager job unit (lumberjack 123/218, miners, hunters...) also lists the buildings it drops
  at (`bird.drop_sites` in the data file). With only the JSON, villagers went idle at the House. *Same test;
  the fix (House added to the lumberjacks' lists) is unverified in game.*
- A mod that only holds `modes/Pompeii/resources/_common/dat/dropsites.json` is listed in the dropdown as a data mod
  of its own, so only one can be active: drop sites and data changes have to ship together in one data mod.
  *Crucible data mod test, 2026-11-09.*

## Resources (Return of Rome)
*Crucible resource test scenario, 2026-11-09, logged by XS every 10 s.*
- Work rate 0 (Modify Attribute 13) on the stone miner units: villagers gather nothing and the mine isn't touched.
- The gather multipliers (Stone Bonus 79, Gold Bonus 47, Wood Bonus 189, Food Bonus 190, Fishing Productivity 219)
  are "resources last longer": Stone Bonus 10 gave about 10 stone per unit the mine lost. A value of 0 is
  ignored (it plays like the default).
- Food/Wood Generation (230/231) are **per minute**: 60 gave +1 food a second.
- No effect in RoR: Military Food Trickle (287) with soldiers, and Chopping Gold Productivity (266).
- What a gather task takes is decided by the target, not the task's `resource_in`: fishing boats edited to take wood
  still took fish and paid food.
- `xsGetUnitProperty(id, cUnitAttributeHeld)` reads a resource pile's remaining amount (a stone mine: 350).
- Changing what a pile holds (Type First Storage, 168) takes effect, per object and per type (a type-wide Modify
  Attribute reaches objects already on the map), but **doesn't change what gatherers receive**: lumberjacks on "gold"
  trees got wood, foragers on "stone" bushes got food, a boat on a "gold" fish got food. The gatherer's task decides
  the payout. *Resource test round 2, 2026-11-09.*
- XS can convert resources at any ratio: reading wood gathered (167) each second and paying 10% as gold
  (`xsSetPlayerAttribute`) gave exactly 21 gold for 212 wood. *Same test.*

## Attack classes
- **Triggers can't give a unit an attack class it doesn't have.** Towers (pierce attack only) got melee and
  building attacks four ways: Modify Attribute Add and Set for the type, Modify Object Attribute Add, Change
  Object Attack. In every case `xsGetUnitAttribute(tower, 9, class)` read −1 for melee and buildings, and each
  stone did 1 damage. Changing an existing class works (pierce Set 0 read 0). Armour has Add Armor Type (160);
  attacks have no equivalent. *Crucible catapult tower demo, round 2, 2026-11-09.*
- `xsEffectAmount` (Add or Set, value class × 256 + amount) can't add one either; the classes still read −1.
  Setting a tower's existing pierce attack to 50 by trigger works: it read 50, and each stone did 50 damage.
  *Round 3.*
- **A data mod can.** A Guard Tower with melee 50 and buildings 140 added to its attack list (genieutils-py) read
  0/50/140 in game, and its catapult stones hit an elephant for about 46 (its melee armour taken off). *Round 3,
  rerun with the data mod picked.*

## Combat settings (Return of Rome, per unit with Modify Object Attribute)
*Crucible combat test, 2026-11-09; some units strayed out of their lanes.*
- Blast Width (22) 3 on a Stone Thrower: targets 2 tiles from the impact were hit.
- Minimum Range (20) 0 on a Ballista: it hit an adjacent enemy; the unchanged one didn't.
- Projectile Unit (16) swapped on a Catapult: it fires the new projectile (a ballista bolt showed as a bolt) with
  its own damage. A projectile given Movement Speed ×3 and Projectile Arc 0 flew fast and flat, like a cannon shot.
- Maximum Range (12) 3 on a Hoplite (melee, no projectile): it attacked from range.
- Friendly Fire Damage (119) doesn't stop friendly fire, in any form: one unit or the whole type, 0 or 0.01, or on
  the projectile (friendly fire test, 2026-11-09). The attribute reference calls it the "blast damage multiplier to
  non directly targeted units". The documented switch is Blast Attack Level (44): base 0-3 plus flags 4 "damage
  enemy units only", 8 "ignore friendly fire", 64 distance falloff, 128 narrow cone (ugc.aoe2.rocks, attribute 44).
  RoR's data uses 6, 10, 34, 66 and 138.
- **No friendly fire: Blast Attack Level + 4.** Level 6 (2 + "enemy units only") on a Stone Thrower (one unit) and on
  every Catapult (Modify Attribute) left friendly units untouched while splash still hit enemies. Level 10 (+ 8,
  "ignore friendly fire") did nothing in RoR. *Friendly fire test round 2, 2026-11-09.*
- Trade Food/Wood/Stone Percent (251-253) work: at 25 each, a 24-gold trade paid 13 gold and 3 of each (about half
  the setting each). The trade boat's panel still shows only gold.

## Garrisoned arrows
- In RoR, raising a tower's Maximum Total Missiles (107) from 1 to 6 doesn't make garrisoned villagers add arrows,
  and only villagers can garrison in towers. *Crucible data mod test, mission 3, 2026-11-09.*
- What AoE2's data has and RoR's lacks (data files compared, 2026-11-09):
  - towers: Maximum Total Missiles 5 (RoR 1);
  - Secondary Projectile Unit 505 (RoR −1; 505 exists in RoR's data);
  - garrison type 11, villagers, infantry and priests (RoR 1, villagers only).
  - Units: garrison firepower, archers 1 and villagers −2.5 (RoR 0 for every unit).
  All are trigger attributes (107, 65, 30, 130).
- **Garrison arrows work in RoR by trigger:** with a tower's Maximum Total Missiles 6, Secondary Projectile Unit 505
  and villagers' garrison firepower 1, each garrisoned villager added an arrow. *Crucible mission 3, 2026-11-09.*
- RoR's soldiers have no garrison command for buildings: their only garrison task (action 3) aims at transport
  ships (class 20). AoE2's archers and infantry also have one aimed at buildings (class 3). Tasks live in the data
  file, so only a data mod adds them. The crucible test mod copies the villager's task onto foot soldiers
  (unverified in game).

## Triggers: training
- A building can train a unit it normally doesn't with triggers alone: Enable Object for the unit, then Modify
  Attribute on it, Train Location (42) set to the building and Train Button (43) set to a free slot. Scouts trained
  at the Barracks in RoR. *Crucible data mod test, 2026-11-09.*

## AI scripts
- RoR buildings exist once per age look (Academy 103/105/18/19 for Ages 1-4); AIs build the Age1 base, and the
  Town Center by 109 (the engine places its foundation, 621). *Trojan War playtest, 2026-11-03: an AI given 18
  never built an Academy.*
- Scenario-embedded AI scripts (custom AI on a player) load in Return of Rome. A rule with about 40 actions
  fails to load with "AI Script Error ... ERR6002: Rule too long"; the game's own scripts never exceed 16 facts
  or 32 facts and actions in a rule, which the checker enforces. *RoR playtest, Trojan War, 2026-11-03.*

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
- Modify Attribute POPULATION (110) is a whole number in triggers: `SET -0.5` on every villager type (the value
  RoR's Logistics tech uses for infantry) left villagers at 1 population. *RoR-RI playtest, 2026-11-07.*
- A Return of Rome scenario must be saved the way the RoR editor saves it: data set list [11] (FileHeader) and
  the DataHeader's 9 unnamed bytes all zero (the parser's default starts with 1). With that first byte at 1, a
  converted mission ended in victory the moment the last enemy was defeated, whatever its victory settings;
  zeroing it alone stopped it. With AoE2's data sets, saved games from a campaign of such scenarios wouldn't
  load ("Package has no dependencies, can't determine data set"); [11] fixed it. *RoR-RI probes against the
  user's own scenario and Ascent of Egypt 3 saves, verified in game 2026-11-08.*
- `remove_object` by unit type over an area (Gaia forage bushes, object state alive) removed nothing; on
  `selected_object_ids` it works. *RoR-RI playtest, 2026-11-07.*
- `task_object` MOVE with `selected_object_ids` and queued (`queue_action`) waypoints drives player-owned
  carts along a route on their own, but the player can still select and stop them, so the `escort` block
  now disables selection by default. *Frontier playtest.*
- A looping `objects_in_area` + `remove_object` (`max_units_affected: 1`) + `change_variable` counts arrivals
  one by one correctly. *Frontier playtest: the count carried to mission 2 exactly.*
- Create Decision followed by a stored answer carries into the next mission. *Frontier playtest.*
- Several `create_object` effects at the same tile place only **one** unit ("+4 Men-at-Arms" gave 1).
  Give each unit its own tile with the `spawn` helper. *Crucible playtest, 2026-10-30.*

## Known parser issue (AoE2ScenarioParser 0.9.8)
- Effects on float-valued attributes (Modify Attribute / Modify Object Attribute on work rate, friendly fire, minimum
  range...) store the value in `quantity_float`. **Writing 0 works** (the file holds 0.0), but **reading one back
  returns −1**: the parser's Effect constructor does `quantity = _quantity_float or quantity`, and 0.0 is falsy, so
  it falls back to the integer field, which is −1 for these effects. So opening a scenario and saving it again turns
  such a 0 into −1. Scenarios built in one go are unaffected. *Found 2026-11-09 by reading the raw section values
  of the crucible combat test (quantity_float 0.0, quantity −1). Not yet fixed in aoe2ed or reported upstream.*

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
