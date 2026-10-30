"""Regenerate fixtures/Player.nfp: a synthetic profile with the same layout as a real one.

The bytes outside the bank are made up (shaped like the real header and trailer); the bank
holds an official-campaign-style key, a non-ASCII key and two test campaigns. Compressed with
zlib level 1 so a save that recompresses would NOT reproduce the file byte-for-byte.

    python tests/bank/make_fixture.py
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "Player.nfp"

RECORDS = [
    ("3kcam1", "LuBuExecuted(1)orSpared(2)", 2),
    ("3kcam2", "LüBuRecruited(1)Yes(2)No", 0),
    ("kv_persist", "kvp_key", 1234),
    ("crucible", "meta_gold", 250),
    ("crucible", "perk_armor", 1),
    ("3kcam1", "VillagersFound", -1),
    ("crucible", "best_wave", (1 << 40) + 7),
]


def head() -> bytes:
    out = struct.pack("<ff", 7.8, 1123.0) + struct.pack("<I", 2) + bytes(8)
    out += struct.pack("<I", 1) + b"Hotkeys.hkp".ljust(256, b"\0")
    out += b"`\n\x0b\x00Arabia.rms" + bytes(40)
    out += struct.pack("<Q", 123456)  # the marker that sits right before the bank count
    return out


def tail() -> bytes:
    return (struct.pack("<iI", -1, 2) + bytes(8) + b"`\n\x06\x00Player" + bytes(16)
            + struct.pack("<i", 100) + b"\xff" * 4)


def bank(records) -> bytes:
    out = struct.pack("<I", len(records))
    for campaign, key, value in records:
        name = f"PKEY:{campaign}:{key}".encode()
        out += struct.pack("<Q", len(name)) + name + struct.pack("<q", value)
    return out


def build(records=RECORDS, level: int = 1) -> bytes:
    c = zlib.compressobj(level, zlib.DEFLATED, -15)
    return c.compress(head() + bank(records) + tail()) + c.flush()


if __name__ == "__main__":
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_bytes(build())
    print(f"wrote {FIXTURE} ({FIXTURE.stat().st_size} bytes)")
