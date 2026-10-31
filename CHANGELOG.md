# Changelog

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
