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
- **Correction (2026-11-09): a trigger can add an attack class** via Modify Object Attribute *Add Attack Type* (161):
  set 161 to the class first, then set Attack for that class. An Axeman given 161 = 11 (buildings) then +50 vs
  buildings razed a House in ~15 s; setting +50 vs buildings alone (class missing) took ~80 s.
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

## Ruins, the Monument and artifacts (Return of Rome)
*Crucible ruins and artifacts test, 2026-11-09.*
- King of the Hill's monument trickles (221-224, which tech 151 sets to 1) pay the owner of the Monument (826)
  about 0.8 of each resource a second, but nothing for owning Artifact Ruins (52), even though both carry
  resource storage 14.
- Artifacts can't garrison: Relic Carts (159) wouldn't enter a Barracks with garrison type 127 (every category).
  Their unit class (1, artifact) matches no garrison category.
- Units: the AoE1 artifact is 25 "Artifact" (graphic 8369 "Artifact (Idle)"), with no garrison task; 44 is the War
  Chest; 159 is a "Relic Cart" with AoE2's relic look (graphic 647); 944 and 1304 are Relic Carts with the artifact
  look, hidden in the editor.
- A data mod copy of the Monument with the Artifact Ruins' graphic, icon and name earns the monument trickle just
  like the Monument (about 0.8 of each a second), including after it's captured from Gaia: the way to make
  "ruins" that trickle. An XS rule that pays per `xsGetObjectCount(p, 52)` also works, without a data mod.
- Garrison checks the unit's class, not just its task: with the villager's garrison task (action 3, class 3) and
  a Barracks at `building.garrison_type` 127, the artifact (class 1) still won't enter, but copies switched to the
  infantry (6) or priest (18) class garrison. `xsGetGarrisonedUnitIds` then sees them.
  But Gaia copies in those classes join player 1 at the start of the game (map revealed), while the real artifact
  stays Gaia until reached. Owned copies still capture the real artifact on contact.
- The per-unit Capture setting (`capture_flag`: -1 default, 0 never, 1 once, 2 multiple times, 3 never/Gaia
  aggressive; scenario format 1.59+) decides that. With 1 (Once), even the real Gaia artifact joined player 1 at
  the start; with 0, 2 or 3, none of the three did, class copies included. On contact: with 2 (Multiple Times)
  all three were captured, so a garrisonable copy placed with flag 2 acts like a real artifact. With 0 the copies
  stayed Gaia (the real artifact was captured anyway). With 3 the infantry copy turned hostile and attacked, and
  the priest copy, attacked to 0 HP, never died.
- A building's work rate (13) speeds up both its training and its research. Set it on every age look of the
  building (`xsEffectAmount(0, id, 13, rate, p)`) and it applies to all of that player's copies: 1.5 and 2.0
  gave 150% and 200% (verified on RoR's Barracks).

## Porting units from AoE2 into Return of Rome
*Crucible port test, 2026-11-09.*
- Chronicles civs and units are in AoE2's main data file (units from 2101), sprites in the shared graphics folder.
  RoR reads sprites from that folder, so a RoR data mod can add AoE2 and Chronicles units without copying art.
- RoR keeps AoE2's unit ids but reuses some slots (38: Knight / Cavalry), and about a third of the graphic ids point
  at other sprites: copy the unit's graphics, sounds and linked units (dead unit, projectiles, the alternate form in
  genieutils' `nothing` field) and renumber those whose RoR entry differs. Ported units then animate, attack, shoot
  and die correctly.
- `icon_id` indexes RoR's own icon set (no fallback to AoE2's icon files): an AoE2 id shows the wrong portrait, a
  Chronicles one (past RoR's set) shows black.
- Mutually exclusive techs: each tech's effect disables every tech in the set (command 102), as Chronicles does. But
  costs are paid at queue time, so a player can queue two and get both.
- A tech cost in a spare resource (e.g. 30, which a civ can start with) is ignored: not shown, not charged, doesn't
  block queueing.
- Chronicles-style exclusivity (red cross on hover, the other blocked while one researches) doesn't happen in RoR,
  whatever the tech type (0, 9 or 33 tried). Disabling the others by script (`xsEffectAmount(cModifyTech, tech,
  cAttributeDisable, 0, p)`) when one is queued didn't block them either. Only the disable on completion works.
- Ported units' alternate forms (Immortal melee/ranged) come across once genieutils' `nothing` field is followed
  (0 means none).

## AoE2 unit tasks and effects in Return of Rome (data mod)
*Crucible mechanics test, 2026-11-09.*
- Work when copied onto RoR units or ported: HP transform (task 158), AoE2's Mule Cart as a movable drop site (task 153,
  plus a dropsites.json entry and the cart listed in every villager job unit's drop sites).
- Tech effects work: spawn unit (7: unit, building, count), enemy attribute multiply (25), team resource (11, the
  player included).
- Didn't work when copied onto RoR units: aura (155: a count-based armour aura, a speed aura on a building) and loot
  (154). Cause not found yet.

## Adding buildings in a data mod
- **A data mod can add a new building** that villagers build: a copy of an existing unit appended to every civ's
  unit list (genieutils-py), with its own id, `enabled` 1 and a train location at the builder (118). A Catapult Tower
  (a Guard Tower copy with the Stone Thrower's attack) built and fired. An upgrade-only building (the Ballista Tower)
  becomes buildable the same way. *Crucible tower build test, 2026-11-09.*
- The build page comes from the building's interface kind (2 economic, 10 military). On the military page, slots 5
  and 10 showed; 14 and 15 didn't (AoE2's highest used slot is 13, the Castle).
- Names: the build button shows the copied unit's text (it read "Guard Tower"). The built tower showed the name of
  string 7079, which RoR uses for "Ballista Tower" even though its tech is called "Catapult Tower". A new unit
  needs strings of its own (unverified how a mod adds them).

## Combat settings (Return of Rome, per unit with Modify Object Attribute)
- Mechanics test (2026-11-09): Regeneration (109, HP per minute) works on units and buildings, in and out of combat.
  Damage reflection (118) reflects melee only, and weakly. Area damage (115) needs a blast width (22) and works on
  ranged and melee attackers. Bonus damage resistance (24) works. Dead unit (57) can leave a live unit (Horse Archer
  -> Bowman worked; Camel Rider -> Broad Swordsman didn't). Charge (59 max, 60 recharge, 61 event 1, 62 type 1)
  gives a charged first hit; type 3 adds its charge but didn't splash.
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
- `xsEffectAmount(cSetUnitAttribute, unitId, attribute, value, player)` changes one unit (verified with regeneration 109,
  2026-11-09: a per-unit, out-of-combat-only regen). Don't call it on a unit at 0 HP: the game crashed the moment
  such a unit died (it still passes `xsDoesUnitExist`).
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
- Modify (Object) Attribute on Population (110): the parser lists 110 as an integer attribute (`ObjectAttribute._storage_type`), so a
  quantity of -0.5 is cut to -1 when the effect is made and only the integer field is written. aoe-editor's
  fraction guard refuses it outright. But RoR's own Logistics sets 110 to -0.5 (half a pop slot), so the game
  takes fractions there. Writing -0.5 into the effect's float field needs a workaround (crucible's mechdatatest
  swaps in an Effect subclass); whether the game then honours it is being tested (2026-11-09).
- Modify Object Attribute on Attack (9) or Armour (8) must use `armour_attack_class` and `armour_attack_quantity`. Putting the
  encoded value (class * 256 + amount) in `quantity` saves a file the parser can't read back (seen 2026-11-09).
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
