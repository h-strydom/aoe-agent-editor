"""The AI Scripting Encyclopedia (airef.github.io) as data: command signatures, parameter types and ranges, and
strategic numbers.

data/ai_reference.json holds the structural facts (scripts/gen_ai_reference.py). airef publishes no license, so
its prose isn't shipped: describe() downloads airef's data file into the user's cache on first use and reads the
descriptions from there. The file is only ever read as text, never run.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from functools import cache
from importlib import resources
from pathlib import Path

COMMANDS_URL = "https://raw.githubusercontent.com/airef/airef.github.io/master/js/commands.js"
SITE = "https://airef.github.io"
KINDS = {"Fact": "fact", "Action": "action", "Fact/Action": "fact/action", "Other": "other"}

_STRING = r'"((?:[^"\\]|\\.)*)"'
_LINK = re.compile(r'"\s*\+\s*(\w+)\.getLink\(\s*(?:"((?:[^"\\]|\\.)*)")?[^)]*\)\s*\+\s*"')
_TAG = re.compile(r"<[^>]+>")


def _text(js: str, names: dict[str, str]) -> str:
    """A JS string expression ("a " + cX.getLink() + " b") as plain text."""
    js = _LINK.sub(lambda m: m.group(2) or names.get(m.group(1), m.group(1)), js)
    js = re.sub(r'"\s*\+\s*urlPrefix\s*\+\s*"', SITE, js)
    parts = re.findall(_STRING, js)
    s = "".join(parts).replace('\\"', '"').replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    s = s.replace("</p><p>", "\n\n")
    return html.unescape(_TAG.sub("", s)).strip()


def _blocks(body: str) -> list[str]:
    """The top-level { ... } items of a JS array literal body."""
    out, depth, start, quoted, esc = [], 0, 0, False, False
    for i, ch in enumerate(body):
        if quoted:
            esc = ch == "\\" and not esc
            if ch == '"' and not esc:
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                out.append(body[start:i + 1])
    return out


def _field(block: str, name: str) -> str | None:
    m = re.search(rf"\b{name}:\s*({_STRING}(?:\s*\+\s*[^,\n]+)*|-?\d+|\[[^\]]*\])", block)
    return m.group(1) if m else None


def _array(text: str, var: str, attr: str) -> str | None:
    m = re.search(rf"^{re.escape(var)}\.{attr}\s*=\s*\[(.*?)^\s*\}}?\s*\];", text, re.S | re.M)
    if m:
        return m.group(1) + "}"
    m = re.search(rf"^{re.escape(var)}\.{attr}\s*=\s*\[(.*?)\];", text, re.S | re.M)
    return m.group(1) if m else None


def parse(text: str, descriptions: bool = False) -> dict:
    """airef's commands.js (as text) -> {"commands", "parameters", "strategic_numbers"}. With descriptions, each
    entry also gets "summary" and "description"."""
    commands_v = {m.group(1): (m.group(2), m.group(3), m.group(4)) for m in re.finditer(
        r'^var (c\w+) = new Command\("([^"]+)","([^"]+)","([^"]*)"\)', text, re.M)}
    params_v = {m.group(1): m.group(2) for m in re.finditer(r'^var (p\w+) = new Parameter\("([^"]+)"', text, re.M)}
    sns_v = {m.group(1): m.group(2) for m in re.finditer(r'^var (sn\w+) = new StrategicNumber\("([^"]+)"\)', text, re.M)}
    names = {**{v: c[0] for v, c in commands_v.items()}, **params_v, **sns_v}
    assigns: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"^(\w+)\.(\w+)\s*=\s*(.+?);?\s*$", text, re.M):
        assigns.setdefault(m.group(1), {}).setdefault(m.group(2), m.group(3))

    def prose(var: str, out: dict) -> None:
        if descriptions:
            a = assigns.get(var, {})
            out["summary"] = _text(a.get("shortDescription", '""'), names)
            out["description"] = _text(a.get("description", '""'), names)

    commands = {}
    for var, (name, kind, version) in commands_v.items():
        entry = {"kind": KINDS.get(kind, kind.lower()), "version": version,
                 "link": f"{SITE}/commands/commands-details.html#{name}"}
        body = _array(text, var, "commandParameters")
        params = []
        for b in _blocks(body or ""):
            link = re.search(r"nameLink:\s*(p\w+)\.getLink", b)
            p = {"name": _text(_field(b, "name") or '""', names)}
            if link and link.group(1) in params_v:
                p["type"] = params_v[link.group(1)]
            rng = _text(_field(b, "range") or '""', names)
            if rng:
                p["range"] = rng
            params.append(p)
        entry["parameters"] = params
        prose(var, entry)
        commands[name] = entry

    parameters = {}
    for var, name in params_v.items():
        a = assigns.get(var, {})
        entry = {"link": f"{SITE}/parameters/parameters-details.html#{name}"}
        if "range" in a and (rng := _text(a["range"], names)):
            entry["range"] = rng
        values = {}
        for b in _blocks(_array(text, var, "valueList") or ""):
            n, i = _field(b, "name"), _field(b, "id")
            if n and i and re.fullmatch(r"-?\d+", i):
                values[_text(n, names)] = int(i)
        if values:
            entry["values"] = values
        ops = []
        for b in _blocks(_array(text, var, "operatorTypes") or ""):
            ops += [html.unescape(o) for o in re.findall(_STRING, _field(b, "operator") or "") if o]
        if ops:
            entry["operators"] = ops
        prose(var, entry)
        parameters[name] = entry

    sns = {}
    for var, name in sns_v.items():
        a = assigns.get(var, {})

        def num(key: str, a=a) -> int | None:
            v = a.get(key, "").strip()
            return int(v) if re.fullmatch(r"-?\d+", v) else None

        entry = {"id": num("id"), "default": num("default"), "min": num("rmin"), "max": num("rmax"),
                 "de": num("de") == 1, "category": _text(a.get("category", '""'), names),
                 "link": f"{SITE}/strategic-numbers/sn-details.html#{name}"}
        prose(var, entry)
        sns[name] = entry
    return {"commands": dict(sorted(commands.items())), "parameters": dict(sorted(parameters.items())),
            "strategic_numbers": dict(sorted(sns.items()))}


@cache
def reference() -> dict:
    data = resources.files("aoe2ed").joinpath("data/ai_reference.json").read_text(encoding="utf-8")
    return json.loads(data)


def cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "aoe2ed"


@cache
def _descriptions() -> dict:
    path = cache_dir() / "airef-commands.js"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(COMMANDS_URL, timeout=60) as r:
            path.write_bytes(r.read())
    return parse(path.read_text(encoding="utf-8", errors="replace"), descriptions=True)


def describe(name: str) -> dict | None:
    """airef's summary and description of a command, parameter type or strategic number (downloaded into the user's
    cache on first use), or None if airef doesn't know it."""
    d = _descriptions()
    for kind in ("commands", "strategic_numbers", "parameters"):
        if name in d[kind]:
            e = d[kind][name]
            return {"kind": kind, "summary": e.get("summary", ""), "description": e.get("description", ""),
                    "link": e["link"]}
    return None


def signature(name: str) -> str | None:
    """"(up-compare-goal GoalId compareOp Value)" for a command airef knows."""
    c = reference()["commands"].get(name)
    if c is None:
        return None
    return "(" + " ".join([name, *(p.get("type") or p["name"] for p in c["parameters"])]) + ")"
