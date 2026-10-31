"""End to end over stdio: tools are listed with their schemas, and errors reach the client with
their message (MCP SDK 2.x hides the text of anything that isn't a ToolError)."""
from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _session_calls():
    params = StdioServerParameters(command=sys.executable, args=["-m", "aoe2ed.mcp_server"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = {t.name: t for t in (await s.list_tools()).tools}
        new = await s.call_tool("scenario_new", {"map_size": 40})
        handle = json.loads(new.content[0].text)["handle"]
        bad = await s.call_tool("triggers_add", {"handle": handle, "triggers": [
            {"name": "Lose", "effects": [{"type": "declare_defeat", "source_player": 1}]}]})
        spec = {"name": "t", "missions": [{"id": "m", "map_size": 40, "blocks": [{"use": "nope"}]}]}
        bad_compile = await s.call_tool("compile_campaign", {"spec": spec, "out_dir": "unused"})
        return tools, bad, bad_compile


def test_tools_listed_and_errors_carry_messages():
    tools, bad, bad_compile = asyncio.run(_session_calls())
    assert "compile_campaign" in tools and "handle" in tools["triggers_add"].input_schema["properties"]
    assert bad.is_error
    text = bad.content[0].text
    assert "trigger 'Lose' effect 0" in text and "Unknown effect type 'declare_defeat'" in text, text
    assert "declare victory for the opponent" in text
    assert bad_compile.is_error and "unknown block 'nope'" in bad_compile.content[0].text
