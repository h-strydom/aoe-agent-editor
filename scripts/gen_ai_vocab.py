"""Build src/aoe2ed/data/ai_vocab.json from the AI scripts shipped with AoE2 DE and Return of Rome.

Every fact, action, strategic number and built-in symbol those scripts use (symbols they define with
defconst themselves are left out). Run after a game update: uv run python scripts/gen_ai_vocab.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aoe2ed.ai.per import Node, _head, _walk_facts, constants, parse, rules
from aoe2ed.config import find_game_dir

OUT = Path(__file__).resolve().parents[1] / "src" / "aoe2ed" / "data" / "ai_vocab.json"
FOLDERS = (Path("resources") / "_common" / "ai", Path("modes") / "Pompeii" / "resources" / "_common" / "ai")


def main() -> int:
    game = find_game_dir()
    if game is None:
        print("AoE2 DE not found (set AOE2DE_PATH)", file=sys.stderr)
        return 1
    files = sorted(p for folder in FOLDERS for p in (game / folder).rglob("*.per"))
    facts, actions, sns, symbols, defined = set(), set(), set(), set(), set()
    arity: dict[str, set[int]] = {}
    for path in files:
        forms, _ = parse(path.read_text(encoding="utf-8", errors="replace"))
        defined |= set(constants(forms))
        for _rule, fs, acts in rules(forms):
            for nodes, into in ((list(_walk_facts(fs)), facts), (acts or [], actions)):
                for node in nodes:
                    if not isinstance(node, Node) or not _head(node):
                        continue
                    into.add(_head(node))
                    arity.setdefault(_head(node), set()).add(len(node.items) - 1)
                    for arg in node.items[1:]:
                        if isinstance(arg, str) and not arg.startswith('"') and not arg.lstrip("-").isdigit():
                            (sns if arg.startswith("sn-") else symbols).add(arg)
    symbols -= defined | facts | actions
    OUT.write_text(json.dumps({
        "source": f"{len(files)} .per files shipped with AoE2 DE and Return of Rome",
        "facts": sorted(facts), "actions": sorted(actions), "strategic_numbers": sorted(sns),
        "symbols": sorted(symbols),
        "arity": {k: sorted(v) for k, v in sorted(arity.items())},   # argument counts each command is used with
    }, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(facts)} facts, {len(actions)} actions, {len(sns)} strategic numbers, "
          f"{len(symbols)} symbols from {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
