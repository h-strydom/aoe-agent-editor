"""XS linting via xs-check (github.com/Divy1211/xs-check), bundled with AoE2ScenarioParser."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import AoE2ScenarioParser

from .config import paths

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_HEAD = re.compile(r"^(?:\[\d+\]\s*)?(Error|Warning|Warn):\s*(\S.*)$")
_LOC = re.compile(r"╭─\[(.+):(\d+):(\d+)\]")
_MSG = re.compile(r"╰─+\s*(.+)$")


def binary() -> Path:
    env = os.environ.get("XS_CHECK_PATH")
    if env:
        return Path(env)
    base = Path(AoE2ScenarioParser.__file__).parent / "dependencies" / "xs-check"
    return base / ("xs-check.exe" if sys.platform == "win32" else "xs-check")


def parse_output(text: str) -> list[dict]:
    diags: list[dict] = []
    cur: dict | None = None
    for raw in _ANSI.sub("", text).splitlines():
        line = raw.strip()
        if m := _HEAD.match(line):
            cur = {"severity": "error" if m.group(1) == "Error" else "warning", "code": m.group(2).strip(),
                   "file": None, "line": None, "col": None, "message": ""}
            diags.append(cur)
        elif cur is not None and (m := _LOC.search(line)):
            cur["file"], cur["line"], cur["col"] = m.group(1), int(m.group(2)), int(m.group(3))
        elif cur is not None and (m := _MSG.search(line)):
            cur["message"] = (cur["message"] + "; " if cur["message"] else "") + m.group(1).strip()
    return diags


def check(code: str | None = None, path: Path | None = None, include_dirs: list[Path] | None = None) -> dict:
    tmp = None
    if code is not None:
        fd, tmp = tempfile.mkstemp(suffix=".xs")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)
        path = Path(tmp)
    assert path is not None
    incs = [str(d) for d in (include_dirs or [])]
    p = paths()
    if p.profile:
        incs.append(str(p.user_dir("xs")))
    args = [str(binary()), str(path)]
    if incs:
        args += ["-I", ",".join(incs)]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, "NO_COLOR": "1"}, timeout=60)
        out = proc.stdout + proc.stderr
    finally:
        if tmp:
            os.unlink(tmp)
    diags = parse_output(out)
    if tmp:
        for d in diags:
            d["file"] = "<code>"
    return {"ok": not any(d["severity"] == "error" for d in diags), "diagnostics": diags}


# ---------------------------------------------------------------- API reference

_PRELUDE_CACHE: str | None = None


def prelude() -> str:
    """The documented XS API (every function and constant) embedded in the xs-check binary by
    its authors. Extracted at runtime, never redistributed."""
    global _PRELUDE_CACHE
    if _PRELUDE_CACHE is None:
        b = binary().read_bytes()
        start = b.find(b"prelude.xs// +")
        if start < 0:
            raise RuntimeError("Could not find the XS prelude inside xs-check")
        start += len(b"prelude.xs")
        end = b.find(b"Prelude can't produce parse errors", start)
        _PRELUDE_CACHE = b[start:end].decode("utf-8", errors="replace").replace("\r", "")
    return _PRELUDE_CACHE


_DECL = re.compile(r"/\*\*(?P<doc>.*?)\*/\s*(?P<sig>(?:extern\s+)?(?:const\s+)?\w+\s+(?P<name>\w+)\s*(?:\([^)]*\))?)",
                   re.S)


def api_entries() -> list[dict]:
    out = []
    for m in _DECL.finditer(prelude()):
        doc = re.sub(r"^\s*\*\s?", "", m.group("doc"), flags=re.M).strip()
        out.append({"name": m.group("name"), "signature": m.group("sig").replace("extern ", "").strip(),
                    "doc": doc})
    return out


def api_search(query: str, limit: int = 20, with_docs: bool = True) -> list[dict]:
    q = query.lower()
    hits = []
    for e in api_entries():
        name = e["name"].lower()
        if q in name:
            score = 0 if name == q else 1 if name.startswith(q) else 2
        elif q in e["doc"].lower():
            score = 3
        else:
            continue
        hits.append((score, len(name), e))
    hits.sort(key=lambda h: (h[0], h[1]))
    return [e if with_docs else {k: e[k] for k in ("name", "signature")} for *_, e in hits[:limit]]
