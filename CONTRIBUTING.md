# Contributing

## Setup
```bash
uv sync
```
```bash
uv run pytest
```
```bash
uv run ruff check src tests scripts
```
Tests need no game install. Tests that read the real game or profile skip themselves when the paths
aren't found (set `AOE2DE_PATH` / `AOE2DE_PROFILE` to point at them).

## Layout
| Path | What it is |
|---|---|
| `.claude-plugin/` | Plugin manifest and marketplace file (the repo root is the plugin) |
| `skills/` | Claude Code skills; `skills/aoe2-triggers/reference/` is generated |
| `src/aoe2ed/tools/` | Every MCP/CLI tool, registered with `@tool` (one registry for both front ends) |
| `src/aoe2ed/blocks/` | Building blocks used by campaign specs |
| `src/aoe2ed/compiler.py` | Campaign spec → scenarios, previews, `.aoe2campaign`, build report |
| `src/aoe2ed/mapgen/`, `render/` | Procedural maps and PNG previews |
| `src/aoe2ed/docs/` | Docs served by the `guide()` tool (spec format, engine facts, coverage) |
| `examples/` | Example campaign specs, also listed by the `examples()` tool |
| `scripts/` | Smoke and probe scenarios for in-game checks, reference generator |
| `docs/` | Notes for maintainers (acceptance test results) |

## Rules of the road
- **Engine facts are evidence-only.** Add to `src/aoe2ed/docs/engine-facts.md` only what a playtest or a
  read of game-written files proved, and say how. Blocks and skills rely on that file.
- **New mechanics go into blocks**, with a test that builds a scenario, reloads it and checks the triggers.
  List the trigger names a block creates in its docstring, since other triggers hook into them.
- **Docs change with the code.** If a tool, block or spec key changes, update `campaign-spec.md`, the
  relevant skill and `coverage.md` in the same change.
- **Regenerate the trigger reference** after upgrading AoE2ScenarioParser:
  `uv run python scripts/gen_trigger_reference.py`.
- **Skills must work from an installed plugin**: no repo-relative paths (use tools or
  `${CLAUDE_PLUGIN_ROOT}`), portable frontmatter only. `tests/test_plugin_structure.py` enforces this.

## Releasing
1. Bump the version in `pyproject.toml`, `src/aoe2ed/__init__.py` and `.claude-plugin/plugin.json`
   (a test checks they agree). The plugin version pins installed users until it changes.
2. Add a `CHANGELOG.md` entry, run `uv lock`, the tests and `claude plugin validate . --strict`.
3. Commit, tag `vX.Y.Z`, push.
