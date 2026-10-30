"""Locate the AoE2 DE install and the user's profile folder.

Resolution order for each path: explicit env var, then auto-discovery.
  AOE2DE_PATH     game install (contains AoE2DE_s.exe and resources/)
  AOE2DE_PROFILE  user profile (contains resources/_common/scenario and profile/)
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

STEAM_APP_ID = 813780
GAME_DIR_NAME = "AoE2DE"


def _steam_roots() -> list[Path]:
    roots: list[Path] = []
    if sys.platform == "win32":
        try:
            import winreg

            for hive, key in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
            ):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        for name in ("SteamPath", "InstallPath"):
                            try:
                                roots.append(Path(winreg.QueryValueEx(k, name)[0]))
                            except OSError:
                                pass
                except OSError:
                    pass
        except ImportError:
            pass
        roots.append(Path(r"C:\Program Files (x86)\Steam"))
    else:
        home = Path.home()
        roots += [home / ".steam/steam", home / ".local/share/Steam",
                  home / ".var/app/com.valvesoftware.Steam/.local/share/Steam"]
    return roots


def _steam_libraries() -> list[Path]:
    libs: list[Path] = []
    for root in _steam_roots():
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="ignore")):
                libs.append(Path(m.group(1).replace("\\\\", "\\")))
        libs.append(root)
    seen, out = set(), []
    for p in libs:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def find_game_dir() -> Path | None:
    env = os.environ.get("AOE2DE_PATH")
    if env:
        return Path(env)
    for lib in _steam_libraries():
        cand = lib / "steamapps" / "common" / GAME_DIR_NAME
        if (cand / "resources").is_dir():
            return cand
    return None


def _profile_bases() -> list[Path]:
    bases = [Path.home() / "Games" / "Age of Empires 2 DE"]
    if sys.platform != "win32":
        # Proton prefix
        for lib in _steam_libraries():
            bases.append(lib / "steamapps/compatdata" / str(STEAM_APP_ID) /
                         "pfx/drive_c/users/steamuser/Games/Age of Empires 2 DE")
    return bases


def find_profile_dirs() -> list[Path]:
    """All profile folders (one per Steam/MS account), most recently used first."""
    env = os.environ.get("AOE2DE_PROFILE")
    if env:
        return [Path(env)]
    found = []
    for base in _profile_bases():
        if base.is_dir():
            for child in base.iterdir():
                if child.is_dir() and child.name.isdigit() and (child / "resources").is_dir():
                    found.append(child)
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


@dataclass(frozen=True)
class Paths:
    game: Path | None
    profile: Path | None

    @property
    def game_logs(self) -> Path | None:
        return self.profile.parent / "logs" if self.profile else None

    def user_dir(self, kind: str) -> Path:
        """kind: scenario | campaign | xs | ai"""
        if not self.profile:
            raise RuntimeError("AoE2 DE profile folder not found; set AOE2DE_PROFILE")
        return self.profile / "resources" / "_common" / kind

    @property
    def player_nfp(self) -> Path | None:
        return self.profile / "profile" / "Player.nfp" if self.profile else None

    @property
    def game_xs_dir(self) -> Path | None:
        return self.game / "resources" / "_common" / "xs" if self.game else None

    def as_dict(self) -> dict:
        return {
            "game": str(self.game) if self.game else None,
            "profile": str(self.profile) if self.profile else None,
            "scenario_dir": str(self.user_dir("scenario")) if self.profile else None,
            "campaign_dir": str(self.user_dir("campaign")) if self.profile else None,
            "xs_dir": str(self.user_dir("xs")) if self.profile else None,
            "logs": str(self.game_logs) if self.game_logs else None,
        }


@lru_cache(maxsize=1)
def paths() -> Paths:
    profiles = find_profile_dirs()
    return Paths(game=find_game_dir(), profile=profiles[0] if profiles else None)
