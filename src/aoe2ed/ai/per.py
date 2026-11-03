"""The AoE2 DE AI script language (.per): reading, and checking scripts against what the game knows.

A script is a list of top-level forms: (defconst name value), (defrule facts... => actions...), (load "file"),
plus preprocessor lines starting with # (#load-if-defined, #else, #end-if). Facts and actions are lists whose
first symbol is the command; facts can nest in (not ...), (or ...), (and ...), (nand ...), (nor ...).

The vocabulary (data/ai_vocab.json) is everything the game's own scripts use: every fact, action, strategic
number and built-in symbol in the .per files shipped with AoE2 DE and Return of Rome
(scripts/gen_ai_vocab.py). A script using only that vocabulary uses only what the engine is known to accept.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources

_TOKEN = re.compile(r'"[^"]*"|\(|\)|[^\s()]+')
LOGIC = {"not", "or", "and", "nand", "nor"}
COMPARISON = {"<", "<=", ">", ">=", "==", "!=", "less-than", "less-or-equal", "greater-than",
              "greater-or-equal", "equal", "not-equal"}
RULE_LIMIT = 10000
# Longest rules in the game's own scripts: 16 facts, 32 facts and actions together. A longer rule fails to
# load with "ERR6002: Rule too long" (seen in RoR with ~40 actions).
MAX_FACTS, MAX_RULE_SIZE = 16, 32


@dataclass
class Node:
    items: list
    line: int


@dataclass
class Diagnostic:
    severity: str          # error | warning
    line: int
    message: str

    def as_dict(self) -> dict:
        return {"severity": self.severity, "line": self.line, "message": self.message}


def _strip_comment(line: str) -> str:
    """The line's code: up to a ';' comment or a '#' preprocessor directive (#load-if-defined ... can follow
    code on the same line) that isn't inside a "string"."""
    quoted = False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        elif ch in ";#" and not quoted:
            return line[:i]
    return line


def _tokens(text: str):
    for n, raw in enumerate(text.splitlines(), start=1):
        for m in _TOKEN.finditer(_strip_comment(raw)):
            yield m.group(0), n


def parse(text: str) -> tuple[list[Node], list[Diagnostic]]:
    """Top-level forms, and any bracket errors."""
    stack: list[Node] = []
    top: list[Node] = []
    problems = []
    for tok, line in _tokens(text):
        if tok == "(":
            stack.append(Node([], line))
        elif tok == ")":
            if not stack:
                problems.append(Diagnostic("error", line, "unmatched ')'"))
                continue
            node = stack.pop()
            (stack[-1].items if stack else top).append(node)
        elif stack:
            stack[-1].items.append(tok)
        else:
            problems.append(Diagnostic("error", line, f"'{tok}' outside any form"))
    for node in stack:
        problems.append(Diagnostic("error", node.line, "'(' is never closed"))
    return top, problems


def _head(node: Node) -> str | None:
    return node.items[0] if node.items and isinstance(node.items[0], str) else None


def rules(forms: list[Node]):
    """(rule node, facts, actions) per defrule."""
    for f in forms:
        if _head(f) == "defrule":
            body = f.items[1:]
            if "=>" in body:
                i = body.index("=>")
                yield f, body[:i], body[i + 1:]
            else:
                yield f, body, None


def _walk_facts(facts):
    for f in facts:
        if isinstance(f, Node):
            if _head(f) in LOGIC:
                yield from _walk_facts(f.items[1:])
            else:
                yield f


@cache
def vocab() -> dict:
    data = resources.files("aoe2ed").joinpath("data/ai_vocab.json").read_text(encoding="utf-8")
    v = json.loads(data)
    return {k: set(v[k]) if isinstance(v[k], list) else v[k] for k in v}


def constants(forms: list[Node]) -> dict[str, str]:
    return {f.items[1]: f.items[2] for f in forms if _head(f) == "defconst" and len(f.items) >= 3}


def _number(tok: str) -> bool:
    return bool(re.fullmatch(r"-?\d+", tok))


def check(text: str) -> list[Diagnostic]:
    """Errors (the game would reject the script) and warnings (names the game's own scripts never use)."""
    forms, problems = parse(text)
    v = vocab()
    defined = set(constants(forms))
    known = v["symbols"] | v["strategic_numbers"] | defined | COMPARISON
    count = 0
    for f in forms:
        head = _head(f)
        if head == "defconst":
            if len(f.items) != 3 or not isinstance(f.items[1], str):
                problems.append(Diagnostic("error", f.line, "defconst takes a name and a value"))
            elif f.items[1] in v["symbols"] | v["facts"] | v["actions"]:
                problems.append(Diagnostic("warning", f.line, f"defconst '{f.items[1]}' shadows a built-in name"))
        elif head not in ("defrule", "load", "load-random"):
            problems.append(Diagnostic("error", f.line, f"unknown top-level form '{head}'"))
    for rule, facts, actions in rules(forms):
        count += 1
        if actions is None:
            problems.append(Diagnostic("error", rule.line, "defrule has no '=>'"))
            continue
        if not facts or not actions:
            problems.append(Diagnostic("error", rule.line, "defrule needs at least one fact and one action"))
        if len(facts) > MAX_FACTS:
            problems.append(Diagnostic("error", rule.line, f"rule too long: {len(facts)} facts (at most {MAX_FACTS})"))
        if len(facts) + len(actions) > MAX_RULE_SIZE:
            problems.append(Diagnostic("error", rule.line, f"rule too long: {len(facts) + len(actions)} facts and "
                                                           f"actions (at most {MAX_RULE_SIZE})"))
        for kind, forms_, names in (("fact", list(_walk_facts(facts)), v["facts"]), ("action", actions, v["actions"])):
            for node in forms_:
                if not isinstance(node, Node):
                    problems.append(Diagnostic("error", rule.line, f"{kind} '{node}' isn't in brackets"))
                    continue
                cmd = _head(node)
                if cmd not in names:
                    problems.append(Diagnostic("warning", node.line, f"unknown {kind} '{cmd}'"))
                for arg in node.items[1:]:
                    if isinstance(arg, Node):
                        continue
                    if arg.startswith('"') or _number(arg) or arg in known:
                        continue
                    if arg.startswith("sn-"):
                        problems.append(Diagnostic("warning", node.line, f"unknown strategic number '{arg}'"))
                    else:
                        problems.append(Diagnostic("warning", node.line, f"unknown name '{arg}' in ({cmd} ...)"))
    if count > RULE_LIMIT:
        problems.append(Diagnostic("error", 1, f"{count} rules; the engine allows {RULE_LIMIT}"))
    return problems
