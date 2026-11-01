# Changelog

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
