"""CLI over the same tool registry, for agents without MCP.

  aoe2ed tools                         list tools with their first doc line
  aoe2ed help <tool>                   full doc + signature
  aoe2ed call <tool> '<json args>'     run one tool (no state between calls)
  aoe2ed script <file.json>            run a sequence: [{"tool": ..., "args": {...}}, ...]
                                       "$prev.handle"-style refs read the previous result

Handles only live within one process, so multi-step edits use `script`.
"""
from __future__ import annotations

import inspect
import json
import sys

from .tools import load_all


def _resolve_refs(obj, results: list):
    if isinstance(obj, str) and obj.startswith("$"):
        head, *path = obj[1:].split(".")
        cur = results[-1] if head == "prev" else results[int(head)]
        for p in path:
            cur = cur[int(p)] if isinstance(cur, list) else cur[p]
        return cur
    if isinstance(obj, dict):
        return {k: _resolve_refs(v, results) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_refs(v, results) for v in obj]
    return obj


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tools = load_all()
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "tools":
        for name, fn in sorted(tools.items()):
            print(f"{name:24} {(fn.__doc__ or '').strip().splitlines()[0] if fn.__doc__ else ''}")
        return 0
    if cmd == "help":
        fn = tools[argv[1]]
        print(f"{argv[1]}{inspect.signature(fn)}\n\n{inspect.getdoc(fn)}")
        return 0
    if cmd == "call":
        args = json.loads(argv[2]) if len(argv) > 2 else {}
        print(json.dumps(tools[argv[1]](**args), indent=2, default=str))
        return 0
    if cmd == "script":
        with open(argv[1], encoding="utf-8") as f:
            steps = json.load(f)
        results: list = []
        for step in steps:
            args = _resolve_refs(step.get("args", {}), results)
            results.append(tools[step["tool"]](**args))
        print(json.dumps(results, indent=2, default=str))
        return 0
    print(f"Unknown command {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
