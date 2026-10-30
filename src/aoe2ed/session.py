"""Open scenarios keyed by short handles, with safe saving.

Agents refer to scenarios by handle ("s1") across tool calls. Saving never silently
overwrites: writing over an existing file first copies it to <name>.bak-<timestamp>.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from ._parser import AoE2DEScenario


@dataclass
class OpenScenario:
    handle: str
    scenario: AoE2DEScenario
    source: Path | None
    opened_at: float = field(default_factory=time.time)

    def info(self) -> dict:
        s = self.scenario
        return {
            "handle": self.handle,
            "source": str(self.source) if self.source else None,
            "scenario_version": s.scenario_version,
            "map_size": s.map_manager.map_size,
            "triggers": len(s.trigger_manager.triggers),
            "variables": len(s.trigger_manager.variables),
            "units": sum(len(u) for u in s.unit_manager.units),
            "active_players": s.player_manager.active_players,
        }


class Sessions:
    def __init__(self) -> None:
        self._open: dict[str, OpenScenario] = {}
        self._counter = 0

    def _new_handle(self) -> str:
        self._counter += 1
        return f"s{self._counter}"

    def open(self, path: str | Path) -> OpenScenario:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        scenario = AoE2DEScenario.from_file(str(path))
        return self._register(scenario, path)

    def new(self, map_size: int | None = None) -> OpenScenario:
        scenario = AoE2DEScenario.from_default()
        if map_size:
            scenario.map_manager.map_size = map_size
        return self._register(scenario, None)

    def adopt(self, scenario: AoE2DEScenario, source: Path | None = None) -> OpenScenario:
        return self._register(scenario, source)

    def _register(self, scenario: AoE2DEScenario, source: Path | None) -> OpenScenario:
        h = self._new_handle()
        self._open[h] = OpenScenario(h, scenario, source)
        return self._open[h]

    def get(self, handle: str) -> OpenScenario:
        try:
            return self._open[handle]
        except KeyError:
            raise KeyError(f"No open scenario '{handle}'. Open: {sorted(self._open)}") from None

    def close(self, handle: str) -> None:
        o = self._open.pop(handle)
        o.scenario.remove_store_reference()

    def list(self) -> list[dict]:
        return [o.info() for o in self._open.values()]

    def save(self, handle: str, path: str | Path | None = None, *, overwrite: bool = False) -> dict:
        o = self.get(handle)
        target = Path(path) if path else o.source
        if target is None:
            raise ValueError("New scenario has no path yet; pass a path")
        if target.suffix != ".aoe2scenario":
            target = target.with_suffix(".aoe2scenario")
        backup = None
        if target.exists():
            if not overwrite and target != o.source:
                raise FileExistsError(f"{target} exists; pass overwrite=True (a backup is kept)")
            backup = backup_file(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        o.scenario.write_to_file(str(target))
        o.source = target
        return {"saved": str(target), "backup": str(backup) if backup else None}


def backup_file(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, dest)
    return dest


SESSIONS = Sessions()
