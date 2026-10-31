"""MCP server exposing every registered aoe2ed tool over stdio."""
from __future__ import annotations

import functools
from collections.abc import Callable

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

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


def _report_errors(fn: Callable) -> Callable:
    """MCP SDK 2.x shows the client only "Error executing tool <name>" for any exception that isn't a
    ToolError, which hid every message the tools write for agents ("[m1] trigger 'X' effect 2: ...").
    Re-raise as ToolError so the message reaches the client. functools.wraps keeps the signature the
    SDK builds the tool's input schema from."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except Exception as e:
            msg = e.args[0] if isinstance(e, KeyError) and e.args else e
            raise ToolError(f"{type(e).__name__}: {msg}") from e
    return wrapper


def build_server() -> MCPServer:
    server = MCPServer(name="aoe2-editor", instructions=INSTRUCTIONS)
    for fn in load_all().values():
        server.add_tool(_report_errors(fn))
    return server


def main() -> None:
    build_server().run("stdio")


if __name__ == "__main__":
    main()
