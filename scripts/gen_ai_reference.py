"""Build src/aoe2ed/data/ai_reference.json from the AI Scripting Encyclopedia (airef.github.io).

airef is the community reference for the AoE2 AI language (AoC, UserPatch and DE). Its site keeps every command,
parameter and strategic number as data in js/commands.js. This reads that file as text (it is never run) and keeps
only the structural facts the checker and lookups need, with a link to the airef page for each:

  commands: name -> kind (fact | action | ...), version it appeared in (AoC, UP, DE), parameters (type and range)
  parameters: type -> range text, named values (dark-age -> 0 ...), operators for compareOp / mathOp / typeOp
  strategic_numbers: name -> id, default, valid range, whether DE uses it

airef publishes no license, so its descriptions and examples are not copied here: ai_lookup links to them, and
aoe2ed.ai.reference can fetch them into the user's own cache when asked.

  uv run python scripts/gen_ai_reference.py [path/to/commands.js]
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from aoe2ed.ai.reference import COMMANDS_URL, parse

OUT = Path(__file__).resolve().parents[1] / "src" / "aoe2ed" / "data" / "ai_reference.json"
COMMIT_URL = "https://api.github.com/repos/airef/airef.github.io/commits/master"


def main() -> int:
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
        commit = "local file"
    else:
        with urllib.request.urlopen(COMMANDS_URL, timeout=60) as r:
            text = r.read().decode("utf-8", errors="replace")
        with urllib.request.urlopen(COMMIT_URL, timeout=60) as r:
            commit = json.load(r)["sha"]
    ref = parse(text, descriptions=False)
    OUT.write_text(json.dumps({
        "source": "airef.github.io (AI Scripting Encyclopedia), js/commands.js; structural facts only",
        "commit": commit,
        **ref,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(ref['commands'])} commands, {len(ref['parameters'])} parameter types, "
          f"{len(ref['strategic_numbers'])} strategic numbers (airef {commit[:10]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
