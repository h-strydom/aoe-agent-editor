# aoe2-agent-editor

Let an AI agent build **Age of Empires II: Definitive Edition** scenarios and whole campaigns from a
plain-language idea:

> "I want a custom campaign that works like AoE4's Crucible mode. The player survives a map for 45
> minutes, then reaches a hub map where they spend metaprogression currency to upgrade their faction."

The agent designs it, generates the maps, wires the triggers and XS, packages a `.aoe2campaign`,
installs it, and checks it in playtests through telemetry. `examples/crucible/` is that exact
campaign, built with this toolkit.

## What's inside
- **MCP server and CLI (63 tools)** over [AoE2ScenarioParser](https://github.com/KSneijders/AoE2ScenarioParser):
  scenarios, players, diplomacy, terrain, units, triggers (JSON, names instead of ids), variables, XS
  with offline linting ([xs-check](https://github.com/Divy1211/xs-check)), campaign files, the campaign
  bank, and the installed game. `run_python` covers anything left. See [docs/coverage.md](docs/coverage.md).
- **Map generator:** spec-driven procedural maps (biomes, bases, spawns, choke points, lakes, rivers,
  hills, roads, forests, resources) that return *named areas*, plus PNG previews so the agent can see the map.
- **Building blocks:** tested mechanics such as survive timers, escalating waves, pad shops with perk
  levels, persistent bank load/store, random boon decisions, roguelite run endings, and anchors for wave enemies.
- **Campaign compiler:** one YAML spec becomes every scenario, preview, the campaign file and a build
  report. A test mode scales all timers ×0.1.
- **Telemetry:** injected XS records resources, kills, variables and trigger events to an `.xsdat`
  file, so the agent can see what happened in a playtest.
- **Claude Code plugin** with skills for designing, building, playtesting, triggers, XS and editor UI.
- **Verified engine facts:** `guide("engine-facts")` lists game behaviour proven in playtests, and grows with each one.

## Install

Requirements: AoE2 DE (Steam), [uv](https://docs.astral.sh/uv/), Windows (Linux/Proton paths are detected but untested).

**Claude Code plugin** (skills + MCP server):
```bash
claude plugin marketplace add h-strydom/aoe2-agent-editor
```
```bash
claude plugin install aoe2-editor@aoe2-editor
```

**Any MCP client:** clone the repo, then point your client at the server:
```json
{ "mcpServers": { "aoe2-editor": { "command": "uv",
  "args": ["run", "--directory", "/path/to/aoe2-agent-editor", "aoe2-editor-mcp"] } } }
```

**CLI only:** `uv run aoe2ed tools`, `uv run aoe2ed help triggers_add`,
`uv run aoe2ed call compile_campaign '{"spec": "examples/crucible/campaign.yaml", "install": true}'`.

Paths are auto-detected. Override them with `AOE2DE_PATH` (game install) and `AOE2DE_PROFILE`
(`%USERPROFILE%\Games\Age of Empires 2 DE\<id>`).

## Try the example
```bash
uv run aoe2ed call compile_campaign "{\"spec\": \"examples/crucible/campaign.yaml\", \"test_mode\": true, \"install\": true}"
```
In game: Single Player → Campaigns → **crucible**. Play the Encampment, then the run, then replay the
Encampment (answer **Yes** to "save your choices") to spend what you earned.

## Development
```bash
uv sync
```
```bash
uv run pytest
```
- `scripts/smoke_scenario.py --install` builds a 2-minute scenario that exercises every block once.
- `scripts/gen_trigger_reference.py` regenerates the trigger reference used by the skills.
- `scripts/demo_mapgen.py` writes example maps and previews to `out/`.

## Credits
AoE2ScenarioParser (KSneijders) handles the scenario format. xs-check (Divy1211 / Alian713) provides
XS linting and the documented XS API. Age of Empires is a trademark of Microsoft; this is an unofficial fan tool.
