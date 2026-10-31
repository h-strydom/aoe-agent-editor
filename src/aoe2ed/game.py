"""Interacting with the installed game: install files, launch, read logs and XS data files.

What the game exposes for observation:
  - <profile>/profile/*.xsdat   written by XS (xsCreateFile/xsWriteInt/...). Our telemetry
                                harness writes here; official campaigns do too (nocam1.xsdat).
  - <profile>/profile/Player.nfp campaign bank (see aoe2ed.bank)
  - <logs>/<session>/MainLog.txt engine log; XS output is NOT logged there.
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

from .config import STEAM_APP_ID, paths

GAME_EXE = "AoE2DE_s.exe"
_LOG_NOISE = ("[rlink", "curl_easy", "Wwise")


def is_running() -> bool:
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {GAME_EXE}", "/NH"],
                             capture_output=True, text=True).stdout
        return GAME_EXE.lower() in out.lower()
    out = subprocess.run(["pgrep", "-f", GAME_EXE], capture_output=True, text=True).stdout
    return bool(out.strip())


def launch() -> dict:
    """Start AoE2 DE through Steam. Opening a specific scenario has no CLI switch; navigate the
    menus (Single Player > Scenario/Campaigns) with desktop automation afterwards."""
    if is_running():
        return {"launched": False, "reason": "already running"}
    url = f"steam://rungameid/{STEAM_APP_ID}"
    if sys.platform == "win32":
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", url])
    return {"launched": True, "via": url}


def install(src: str | Path, kind: str | None = None, overwrite: bool = True) -> dict:
    """Copy a .aoe2scenario/.aoe2campaign/.xs/.ai file into the matching profile folder."""
    src = Path(src)
    kind = kind or {".aoe2scenario": "scenario", ".aoe2campaign": "campaign", ".xs": "xs",
                    ".ai": "ai", ".per": "ai"}.get(src.suffix.lower())
    if not kind:
        raise ValueError(f"Can't tell where {src.name} goes; pass kind")
    dest = paths().user_dir(kind) / src.name
    if dest.exists() and not overwrite:
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.resolve() != src.resolve():
        shutil.copy2(src, dest)
    return {"installed": str(dest), "kind": kind}


def log_sessions() -> list[Path]:
    logs = paths().game_logs
    if not logs or not logs.is_dir():
        return []
    return sorted((p for p in logs.iterdir() if p.is_dir() and p.name[:4].isdigit()),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def read_log(session: int = 0, grep: str | None = None, tail: int = 200, include_noise: bool = False) -> dict:
    """Lines from a session's MainLog.txt (0 = most recent session)."""
    sessions = log_sessions()
    if not sessions:
        return {"session": None, "lines": []}
    folder = sessions[session]
    log = folder / "MainLog.txt"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.exists() else []
    if not include_noise:
        lines = [ln for ln in lines if not any(n in ln for n in _LOG_NOISE)]
    if grep:
        g = grep.lower()
        lines = [ln for ln in lines if g in ln.lower()]
    return {"session": folder.name, "lines": lines[-tail:]}


def xsdat_files() -> list[dict]:
    prof = paths().profile
    if not prof:
        return []
    return [{"name": p.name, "path": str(p), "bytes": p.stat().st_size,
             "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))}
            for p in sorted((prof / "profile").glob("*.xsdat"), key=lambda p: p.stat().st_mtime, reverse=True)]


def read_xsdat(name_or_path: str, as_type: str = "int") -> dict:
    """Decode an .xsdat file as a flat sequence of int32 or float32 values."""
    p = Path(name_or_path)
    if not p.is_absolute():
        profile = paths().profile
        if profile is None:
            raise RuntimeError("AoE2 DE profile folder not found; set AOE2DE_PROFILE or pass a full path")
        p = profile / "profile" / (p.name if p.suffix else p.name + ".xsdat")
    b = p.read_bytes()
    n = len(b) // 4
    fmt = f"<{n}{'i' if as_type == 'int' else 'f'}"
    return {"path": str(p), "values": list(struct.unpack_from(fmt, b))}
