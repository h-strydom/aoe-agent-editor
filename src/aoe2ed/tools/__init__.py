"""Tool registry. Every agent-facing operation is a plain function registered with @tool.

The MCP server and the CLI both expose exactly this registry, so the two never drift.
Tools take and return JSON-compatible values.
"""
from __future__ import annotations

from typing import Callable

TOOLS: dict[str, Callable] = {}


def tool(fn: Callable) -> Callable:
    TOOLS[fn.__name__] = fn
    return fn


def load_all() -> dict[str, Callable]:
    from . import files, logic, meta, scenario, world  # noqa: F401  (registration side effects)
    return TOOLS
