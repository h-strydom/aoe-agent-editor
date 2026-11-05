# Changelog

## 0.6.0

- AI specs: `levels` plays an easy, normal or hard version by the game's difficulty (`auto`: easy barely attacks,
  hard attacks often and in bigger groups from a bigger economy; no level cheats; or override keys per level).
  `army: {civ}` leans the keep list's soldiers toward the units the civ's bonuses favour. A build-order train
  step moves on after one step timeout, so losses in attacks no longer stall the rest of the plan.
- Civ bonuses for Return of Rome from the game's data (`aoe2ed.civs`, `scripts/gen_civ_bonuses.py`): each
  civ's favoured units with their bonuses, where they're made and their age, and the units it can't make. `start: {trigger: N}` makes
  the AI wait until the scenario's AI Script Goal effect sends N.
- Blocks: `start_ai` sends that signal when its conditions hold; `claim_base` hands the Gaia buildings, villagers
  and soldiers in an area to the player when their units arrive, optionally starting the AIs; `reveal` starts a
  player with an area explored (map revealers, removed after a second, or kept for permanent sight).

## 0.5.0

- AI specs, from the Trojan War probes. `window` (default 3): the AI works on the next steps at once instead of
  one at a time. `keep_from` (default start): the keep list reinforces from the beginning, not only after the
  whole build order. `rebalance` (default on): every minute 5% of villagers move to a resource the plan spends
  that's running out, from the biggest pile. `scout` (default with naval attacks or transports): a scout ship explores, because the attack
  rule needs a known enemy building and across water nothing finds one. `report`: the AI publishes its step,
  waits, attacks and villager split on AI signals for probes.
- AI investigation. `ai_lint` finds problems in an AI spec before playing: units whose building is never
  built, later-age building looks, attacks without an army, naval attacks without ships. `ai_probe` writes an
  instrumented copy of a scenario that records every player's stockpile, gathering, population, villagers,
  army, kills, idle time and object counts, and stops itself after a set time (15 game minutes is about 2 real
  minutes at 8x with the DEBUGSPEEDS launch option). `ai_probe_report` decodes the record and runs the checks
  (stalled build order, never made, hoarding, too few villagers, housed, no income, no attack, idle villagers).
- Guide `ai-behaviour`: how to investigate an AI, every check, and what's known about AI behaviour and the test
  setup, each with how it was found; the aoe2-ai skill points to it.
## 0.4.1

- AI scripts know the AI Scripting Encyclopedia (airef.github.io): every command's signature and parameter
  types, the version that added it, parameter value names, and each strategic number's id, default, range and
  whether DE uses it (`data/ai_reference.json`, `scripts/gen_ai_reference.py`; structural facts only, since airef
  has no license: descriptions are fetched into the user's cache on request). The checker now accepts commands
  the game's own scripts never use but airef documents, and reports facts used as actions, non-operators where a
  compareOp/mathOp/typeOp goes, goals above 16000 and timers above 100 (errors), plus strategic numbers set
  outside their range or that DE ignores (warnings). The game's 87 shipped scripts check without errors.
  `ai_lookup` returns signatures, ranges and airef links; `describe=True` adds airef's description.
- Full unit, building and tech tables for Return of Rome and AoE2 (`data/tables/{ror,aoe2}.json`, from the
  game's own data: `scripts/gen_unit_tables.py`): every object id with its display and internal name, kind,
  class, hit points, cost and where it's made; buildings that exist once per age look know their age and the
  Age1 base to build; every tech with its cost and where it's researched. Tool `unit_info`. The tables are
  pinned to the game build (101.103.57257.0) and each data file's SHA-256; tool `game_build_check` (and a test)
  says when a patch or DLC has changed the game since. AoE2 names the parser's datasets don't list yet (newer
  DLC units) now resolve from the table.
- RoR names: ACADEMY is 103 and TEMPLE 104, the Age1 buildings villagers build, not later-age looks (18, 30)
  that have lower ids. An AI told to build ACADEMY never could, so it never trained hoplites. The Town Center
  stays 109 (its "Age1" entry, 621, is the foundation).
- The AI checker knows how many arguments each command takes in the game's own scripts and reports any other
  count as an error: `(goal 3 < 4)` (there's no comparison form; it's `up-compare-goal`) loaded in RoR as
  "ERR2011: Missing closing parenthesis". Waiting steps now use `up-compare-goal`.
- Unit, building and tech costs for RoR and AoE2 (`data/costs.json`, from both games' data;
  `scripts/gen_ror_dataset.py`). AI specs use them: `gatherers: auto` (the default) splits villagers by what the
  build order and keep list cost, blended with AIBuilder's 45/30/15/10; a stalled step is only skipped when it's
  affordable (so it can't be made), and waited for while it isn't. Default split is now AIBuilder's.
- AI specs attack the way DE's AIBuilder (RoR's scenario AI framework) does: target the closest enemy, set the
  share of soldiers that go (`attack.percent`, default 80), attack-now; `attack.naval` sends warships too. The
  setup always enables DE's building system and full response to sighted enemies. `debug: true` announces each
  build step and attack in chat, for playtests.
- AI specs: `transports` keeps that many transport ships from the start (default unit per game), so attacks can
  cross water on island and coast maps; `keep` also takes `build` entries, so destroyed buildings are rebuilt.
- AI scripts: rules longer than the engine allows are now checker errors (more than 16 facts, or more than 32
  facts and actions together: the game's own longest), and AI specs split their setup into rules of at most
  16 actions. A spec with many strategic numbers made a setup rule RoR refused ("ERR6002: Rule too long").

## 0.4.0

AI scripts: first-class computer player AI.

- AI specs: a readable description of a computer player (build order of build/train/research steps,
  villagers, houses, gatherer split, attack timing and group sizes, strategic numbers, raw rules) compiled
  to a `.per` script (`aoe2ed.ai.spec`). Generated scripts give unit, building and tech ids with defconst,
  as Return of Rome's own AIs do, so they work for RoR and AoE2.
- A `.per` checker (`aoe2ed.ai.per`): bracket and rule-shape errors, plus warnings for facts, actions,
  strategic numbers and names the game's own scripts never use. The vocabulary is extracted from the 87
  AI scripts shipped with AoE2 DE and RoR (`scripts/gen_ai_vocab.py`), all of which check clean.
- Tools `ai_build`, `ai_check`, `ai_set` (embed a spec, script or none/immobile/default in a scenario
  player), `ai_lookup`; `player_set` and campaign specs take `ai: {name, spec}`.
- Guide `ai-spec`, skill `aoe2-ai`.

## 0.3.1

- `campaign_install_mod(widget_files=...)` / `install_campaign_mod(widget_files=...)`: intro slide images,
  written to the mod's `[modes/Pompeii/]widgetui/` and referenced with "SlideImageSequence" (%d from 1).
- Engine facts: where slide images load from, and that custom narration doesn't play (only the game's
  own sound events).

## 0.3.0

Campaign screens: map backgrounds, mission icons and intro slideshows.

- `campaign_screens(game)` lists the game's own campaign screens (background, one icon per mission
  button, intro file); `campaign_install_mod(...)` installs a campaign with a screen as a local mod,
  reusing an official screen with your title and mission labels (and its narrated intros), or your
  own layout/intro JSON and images.
- `screen:` in campaign specs: `compile_campaign(..., install=True)` installs the campaign as a mod
  with its screen.
- `aoe2ed.screens`: layout/intro reading (tolerates the game's leading-zero numbers), building layouts
  from scratch, mod install. Verified in game: screens are only read from mods, and only when the
  campaign's internal name equals its file name. Without a screen the default book shows 9 missions.

## 0.2.0

Return of Rome support.

- `game: ror` in campaign specs (per mission too), `scenario_new(game="ror")`: scenarios are flagged
  for RoR and install into RoR's own profile folders (`modes/Pompeii/...`).
- RoR unit, building, tech and civ names, generated from RoR's game data
  (`scripts/gen_ror_dataset.py`, `src/aoe2ed/data/ror.json`). Every resolver, `lookup` and
  `enum_values` switch tables for RoR scenarios. AoE2 names that mean a different RoR unit are
  rejected with the RoR name (MILITIA's id is a Short Swordsman in RoR).
- RoR civilizations (EGYPTIANS, GREEKS, ROMANS, ...) can be set even though the parser's civ list
  lacks them.
- Examples: `crucible_ror`, the Crucible rebuilt for RoR. `scripts/smoke_scenario.py --game ror`.
- Installing, `scenario_open` and `campaign_read` find files in either game's folders; telemetry
  files are looked for in both profiles.

## 0.1.1

Fixes from the first install test (a fresh session using only the installed plugin).

- MCP tool errors now reach the client with their message. MCP SDK 2.x showed only
  "Error executing tool <name>" for anything that wasn't a ToolError.
- Unknown effect or condition types say so, suggest close matches and explain the defeat idiom.
- `lose_if_destroyed` defaults to a defeat (the opponent is declared the victor); `effects` is optional.
- Map specs accept lobby size names (`size: medium` = 168).
- Mission telemetry is included in test builds only, unless `telemetry: {release: true}`.
- Map generation errors name the mission.
- Docs: defeat idiom, corner vs edge zones, dense forest maps.

## 0.1.0

First public version.

- MCP server and CLI over AoE2ScenarioParser: scenarios, players, diplomacy, terrain, units,
  triggers (JSON with names instead of ids), variables, XS with offline linting and API search,
  campaign files, the campaign bank (`Player.nfp`), the installed game, telemetry and `run_python`.
- Procedural map generator with named areas, and PNG previews.
- Building blocks: survive, objective, lose_if_destroyed, waves (escalating, chase), anchor, escort,
  choice, random_faction, bank load/store, pad shop, perk effects, boon offers, run endings, telemetry.
- Campaign compiler: YAML spec → scenarios, previews, `.aoe2campaign` and build report; test mode
  (timers scaled, map revealed), shared defaults, `when:` gates, errors that name the mission and trigger.
- Examples: Crucible-style roguelite, frontier story campaign, random factions.
- Claude Code plugin with skills for designing, building, playtesting, triggers, XS and editor UI.
- Engine facts verified in playtests, served by `guide("engine-facts")`.
