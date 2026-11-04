"""The AoE2 DE AI script language (.per): reading, and checking scripts against what the game knows.

A script is a list of top-level forms: (defconst name value), (defrule facts... => actions...), (load "file"),
plus preprocessor lines starting with # (#load-if-defined, #else, #end-if). Facts and actions are lists whose
first symbol is the command; facts can nest in (not ...), (or ...), (and ...), (nand ...), (nor ...).

The vocabulary (data/ai_vocab.json) is everything the game's own scripts use: every fact, action, strategic
number and built-in symbol in the .per files shipped with AoE2 DE and Return of Rome
(scripts/gen_ai_vocab.py). A script using only that vocabulary uses only what the engine is known to accept.

The AI Scripting Encyclopedia (airef.github.io, data/ai_reference.json) adds what the game's scripts don't
show: commands they never use, each parameter's type (so operators are checked: compareOp, mathOp, typeOp), the
named values of parameter types (castle-age, find-closest...), and each strategic number's valid range and
whether DE uses it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources

from .reference import reference

_TOKEN = re.compile(r'"[^"]*"|\(|\)|[^\s()]+')
LOGIC = {"not", "or", "and", "nand", "nor"}
COMPARISON = {"<", "<=", ">", ">=", "==", "!=", "less-than", "less-or-equal", "greater-than",
              "greater-or-equal", "equal", "not-equal"}
RULE_LIMIT = 10000
OPERATOR_TYPES = ("compareOp", "mathOp", "typeOp")
SN_SETTERS = {"set-strategic-number": 1}                # command -> position of the value, after the SN
MAX_GOAL, MAX_TIMER = 16000, 100                       # the game's own scripts also use goal 0 and -1
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
    out = {k: set(v[k]) if isinstance(v[k], list) else v[k] for k in v}
    out["arity"] = {k: set(n) for k, n in v.get("arity", {}).items()}
    ref = reference()
    out["ref_commands"] = ref["commands"]
    out["ref_sns"] = ref["strategic_numbers"]
    out["ref_symbols"] = {name for p in ref["parameters"].values() for name in p.get("values", {})}
    out["operators"] = {t: set(ref["parameters"][t]["operators"]) for t in OPERATOR_TYPES}
    out["any_operator"] = set().union(*out["operators"].values())
    return out


def constants(forms: list[Node]) -> dict[str, str]:
    return {f.items[1]: f.items[2] for f in forms if _head(f) == "defconst" and len(f.items) >= 3}


def _number(tok: str) -> bool:
    return bool(re.fullmatch(r"-?\d+", tok))


def _signature(cmd: str, ref: dict) -> str:
    return "(" + " ".join([cmd, *(p.get("type") or p["name"] for p in ref["parameters"])]) + ")"


def _check_args(node: Node, cmd: str, ref: dict | None, v: dict, defined: set[str]) -> list[Diagnostic]:
    """Argument checks from airef's parameter types: an operator where a compareOp/mathOp/typeOp goes, goal and
    timer ids in range, and strategic numbers DE ignores or that are set outside their range."""
    out = []
    args = node.items[1:]
    if ref and len(args) == len(ref["parameters"]):
        for arg, p in zip(args, ref["parameters"], strict=True):
            ptype = p.get("type", "")
            if not isinstance(arg, str) or arg in defined:
                continue
            # Operators are plain numbers to the engine, and the game's own scripts pass a typeOp where airef says
            # compareOp (c: for "c:<" ...), so only a token that is no operator at all is an error.
            if ptype in OPERATOR_TYPES and arg not in v["any_operator"] and not _number(arg):
                sample = ", ".join(sorted(v["operators"][ptype], key=len)[:8])
                out.append(Diagnostic("error", node.line, f"({cmd} ...) expects a {ptype} where '{arg}' is "
                                                          f"({sample}, ...): {_signature(cmd, ref)}"))
            elif ptype in ("GoalId", "OutputGoalId", "OptionGoalId") and _number(arg) and int(arg) > MAX_GOAL:
                out.append(Diagnostic("error", node.line, f"goal {arg} is out of range (DE has 1 to {MAX_GOAL})"))
            elif ptype == "TimerId" and _number(arg) and int(arg) > MAX_TIMER:
                out.append(Diagnostic("error", node.line, f"timer {arg} is out of range (DE has 1 to {MAX_TIMER})"))
    for i, arg in enumerate(args):
        sn = v["ref_sns"].get(arg) if isinstance(arg, str) else None
        if sn is None:
            continue
        if not sn["de"]:
            out.append(Diagnostic("warning", node.line, f"'{arg}' has no effect in DE ({sn['link']})"))
        at = SN_SETTERS.get(cmd)
        if at is not None and i == at - 1 and len(args) > at and isinstance(args[at], str) and _number(args[at]):
            value, lo, hi = int(args[at]), sn["min"], sn["max"]
            if lo is not None and hi is not None and not lo <= value <= hi:
                out.append(Diagnostic("warning", node.line, f"{arg} {value} is outside its range {lo} to {hi}"))
    return out


def check(text: str) -> list[Diagnostic]:
    """Errors (the game would reject the script) and warnings (names the game's own scripts never use)."""
    forms, problems = parse(text)
    v = vocab()
    defined = set(constants(forms))
    known = v["symbols"] | v["strategic_numbers"] | defined | COMPARISON | v["ref_symbols"] | set(v["ref_sns"])
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
                ref = v["ref_commands"].get(cmd)
                if ref and ref["kind"] in ("fact", "action") and ref["kind"] != kind:
                    problems.append(Diagnostic("error", node.line, f"'{cmd}' is a {ref['kind']}, used as a {kind}"))
                elif cmd not in names and not ref:
                    problems.append(Diagnostic("warning", node.line, f"unknown {kind} '{cmd}'"))
                elif cmd in v["arity"] and len(node.items) - 1 not in v["arity"][cmd]:
                    seen = "/".join(map(str, sorted(v["arity"][cmd])))
                    problems.append(Diagnostic("error", node.line, f"({cmd} ...) takes {seen} arguments in the game's "
                                                                   f"own scripts, not {len(node.items) - 1}"))
                elif cmd not in v["arity"] and ref and len(node.items) - 1 != len(ref["parameters"]):
                    problems.append(Diagnostic("warning", node.line, f"({cmd} ...) takes {len(ref['parameters'])} "
                                                                     f"arguments per airef, not {len(node.items) - 1}: "
                                                                     f"{_signature(cmd, ref)}"))
                problems += _check_args(node, cmd, ref, v, defined)
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
