"""MCP server exposing every registered aoe2ed tool over stdio."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .tools import load_all

INSTRUCTIONS = """\
Tools for building Age of Empires II: Definitive Edition scenarios and campaigns.

Workflow: scenario_new or scenario_open -> returns a handle ("s1"); pass it to every other tool.
Edit with players_*/map_*/units_*/triggers_*/xs_* tools, then scenario_save (install=True puts
it in the game's scenario folder). Names are accepted wherever ids are: units 'ARCHER',
players 'ONE', terrains 'GRASS_1', operation 'Add'. Use lookup() to find names and
effect_schema()/condition_schema() for trigger parameters. run_python is the escape hatch for
anything AoE2ScenarioParser can do that no tool covers. Lint XS with xs_check before embedding.

Whole campaigns: write a YAML spec (guide("campaign-spec"), examples() for working specs) and build
it with compile_campaign. Check guide("engine-facts") before relying on any game behaviour.
Relative paths resolve against the current working directory.
"""


def build_server() -> MCPServer:
    server = MCPServer(name="aoe2-editor", instructions=INSTRUCTIONS)
    for fn in load_all().values():
        server.add_tool(fn)
    return server


def main() -> None:
    build_server().run("stdio")


if __name__ == "__main__":
    main()
