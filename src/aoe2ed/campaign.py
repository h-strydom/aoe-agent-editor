""".aoe2campaign read/write.

Layout (little endian), as used by the game's own campaigns:
  char[4]   version            b"2.00"
  int32     dependency_count, then int32 * count   DLC/data dependencies (2..7 in all files seen)
  char[256] name               NUL-terminated; the campaign bank (Store/Load Key Value) is scoped by it
  int32     scenario_count
  per scenario:
    int32   size, int32 offset (absolute, into this file)
    str     name, str filename  where str = u16 0x0A60 marker, u16 length, bytes
  scenario blobs (raw .aoe2scenario bytes) at their offsets
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

VERSION = b"2.00"
DEFAULT_DEPENDENCIES = [2, 3, 4, 5, 6, 7]
NAME_LEN = 256
STR_MARKER = 0x0A60


@dataclass
class CampaignScenario:
    name: str
    filename: str
    data: bytes


@dataclass
class Campaign:
    name: str
    scenarios: list[CampaignScenario] = field(default_factory=list)
    dependencies: list[int] = field(default_factory=lambda: list(DEFAULT_DEPENDENCIES))
    version: bytes = VERSION

    # ------------------------------------------------------------ io
    @classmethod
    def from_bytes(cls, b: bytes) -> "Campaign":
        pos = 0

        def take(fmt):
            nonlocal pos
            vals = struct.unpack_from(fmt, b, pos)
            pos += struct.calcsize(fmt)
            return vals

        def take_str():
            nonlocal pos
            marker, n = take("<HH")
            if marker != STR_MARKER:
                raise ValueError(f"Bad string marker {marker:#x} at {pos - 4}")
            s = b[pos:pos + n].decode("utf-8", errors="replace")
            pos += n
            return s

        version = b[:4]
        pos = 4
        (dep_count,) = take("<i")
        deps = list(take(f"<{dep_count}i"))
        name = b[pos:pos + NAME_LEN].split(b"\0", 1)[0].decode("utf-8", errors="replace")
        pos += NAME_LEN
        (count,) = take("<i")
        entries = []
        for _ in range(count):
            size, offset = take("<ii")
            entries.append((size, offset, take_str(), take_str()))
        scenarios = [CampaignScenario(n, fn, b[off:off + size]) for size, off, n, fn in entries]
        return cls(name, scenarios, deps, version)

    @classmethod
    def read(cls, path: str | Path) -> "Campaign":
        return cls.from_bytes(Path(path).read_bytes())

    def to_bytes(self) -> bytes:
        name = self.name.encode("utf-8")
        if len(name) >= NAME_LEN:
            raise ValueError("Campaign name too long")

        def enc_str(s: str) -> bytes:
            raw = s.encode("utf-8")
            return struct.pack("<HH", STR_MARKER, len(raw)) + raw

        head = bytearray(self.version)
        head += struct.pack(f"<i{len(self.dependencies)}i", len(self.dependencies), *self.dependencies)
        head += name.ljust(NAME_LEN, b"\0")
        head += struct.pack("<i", len(self.scenarios))
        table_size = sum(8 + len(enc_str(s.name)) + len(enc_str(s.filename)) for s in self.scenarios)
        offset = len(head) + table_size
        table = bytearray()
        for s in self.scenarios:
            table += struct.pack("<ii", len(s.data), offset) + enc_str(s.name) + enc_str(s.filename)
            offset += len(s.data)
        return bytes(head + table + b"".join(s.data for s in self.scenarios))

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        if path.suffix != ".aoe2campaign":
            path = path.with_suffix(".aoe2campaign")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_bytes())
        return path

    # ------------------------------------------------------------ helpers
    def add_scenario_file(self, path: str | Path, name: str | None = None) -> None:
        path = Path(path)
        self.scenarios.append(CampaignScenario(name or path.name, path.name, path.read_bytes()))

    def summary(self) -> dict:
        return {"name": self.name, "dependencies": self.dependencies,
                "scenarios": [{"index": i, "name": s.name, "filename": s.filename, "bytes": len(s.data)}
                              for i, s in enumerate(self.scenarios)]}
