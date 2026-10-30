"""Read and edit the AoE2 DE campaign key-value bank in the profile's Player.nfp.

The scenario effects STORE_KEY_VALUE / LOAD_KEY_VALUE / DELETE_KEY persist int64 values per
campaign in this file. See FORMAT.md for the layout.

    bank = load(path)               # or load() for the most recently used profile
    bank.keys("kv_persist")         # {"kvp_key": 1234}
    bank.set("kv_persist", "kvp_key", 5)
    bank.save()                     # timestamped backup first; refuses while the game runs

The game keeps the profile in memory and rewrites Player.nfp when it exits, so edits made while
AoE2DE_s.exe is running would be lost (and could clobber the game's own writes).
"""
from __future__ import annotations

import os
import struct
import time
import zlib
from pathlib import Path

PREFIX = b"PKEY:"
# u64 that precedes the bank's record count in every profile seen so far; used to find the
# section when the bank is empty (no PKEY: string to anchor on).
_SECTION_MARKER = struct.pack("<Q", 123456)
_MAX_RECORDS = 1_000_000
_MAX_NAME = 4096
_I64 = (-(1 << 63), (1 << 63) - 1)


class BankFormatError(ValueError):
    pass


class GameRunningError(RuntimeError):
    pass


def find_profiles() -> list[Path]:
    """Player.nfp of every profile (one per Steam/MS account), most recently used first.

    Honours AOE2DE_PROFILE like the rest of aoe2ed."""
    from ..config import find_profile_dirs

    return [p / "profile" / "Player.nfp" for p in find_profile_dirs()
            if (p / "profile" / "Player.nfp").is_file()]


def default_path() -> Path:
    profiles = find_profiles()
    if not profiles:
        raise FileNotFoundError("no Player.nfp found; set AOE2DE_PROFILE or pass a path")
    return profiles[0]


def _parse_records(raw: bytes, start: int) -> tuple[list[list], int] | None:
    """Parse the section whose u32 count is at `start`; None if it doesn't parse cleanly."""
    if start < 0 or start + 4 > len(raw):
        return None
    (n,) = struct.unpack_from("<I", raw, start)
    if n > _MAX_RECORDS:
        return None
    p = start + 4
    records = []
    for _ in range(n):
        if p + 8 > len(raw):
            return None
        (length,) = struct.unpack_from("<Q", raw, p)
        if length > _MAX_NAME or p + 16 + length > len(raw):
            return None
        name = raw[p + 8:p + 8 + length]
        (value,) = struct.unpack_from("<q", raw, p + 8 + length)
        records.append([name, value])
        p += 16 + length
    return records, p


def _find_section(raw: bytes) -> tuple[int, int, list[list]]:
    first = raw.find(PREFIX)
    if first >= 0:
        parsed = _parse_records(raw, first - 12)  # u32 count + u64 length precede the name
        if parsed and parsed[0] and all(name.startswith(PREFIX) for name, _ in parsed[0]):
            return first - 12, parsed[1], parsed[0]
    # Empty bank: fall back to the marker that precedes the count.
    i = raw.rfind(_SECTION_MARKER)
    while i >= 0:
        parsed = _parse_records(raw, i + 8)
        if parsed and not parsed[0]:
            return i + 8, parsed[1], parsed[0]
        i = raw.rfind(_SECTION_MARKER, 0, i)
    raise BankFormatError("campaign bank section not found in Player.nfp")


def _split(name: bytes) -> tuple[str, str] | None:
    if not name.startswith(PREFIX):
        return None
    campaign, sep, key = name[len(PREFIX):].partition(b":")
    if not sep:
        return None
    return (campaign.decode("utf-8", "surrogateescape"), key.decode("utf-8", "surrogateescape"))


def _name(campaign: str, key: str) -> bytes:
    if not campaign or ":" in campaign:
        raise ValueError(f"invalid campaign name {campaign!r} (must be non-empty, no ':')")
    if not key:
        raise ValueError("key must be non-empty")
    name = PREFIX + f"{campaign}:{key}".encode("utf-8", "surrogateescape")
    if len(name) > _MAX_NAME:
        raise ValueError("campaign + key too long")
    return name


class Bank:
    """A parsed Player.nfp. Everything outside the bank section is kept as opaque bytes."""

    def __init__(self, data: bytes, path: Path | None = None):
        self.path = path
        self._original = data
        try:
            raw = zlib.decompress(data, -15)
        except zlib.error as e:
            raise BankFormatError(f"not a raw-deflate Player.nfp: {e}") from None
        start, end, self._records = _find_section(raw)
        self._head, self._tail = raw[:start], raw[end:]
        self._dirty = False

    # --- reading -----------------------------------------------------------------------
    def campaigns(self) -> list[str]:
        seen: dict[str, None] = {}
        for name, _ in self._records:
            split = _split(name)
            if split:
                seen.setdefault(split[0])
        return sorted(seen, key=str.casefold)

    def keys(self, campaign: str) -> dict[str, int]:
        out = {}
        for name, value in self._records:
            split = _split(name)
            if split and split[0] == campaign:
                out[split[1]] = value
        return out

    def get(self, campaign: str, key: str, default: int | None = None) -> int | None:
        name = _name(campaign, key)
        return next((v for n, v in self._records if n == name), default)

    def items(self) -> list[tuple[str, str, int]]:
        return [(*s, v) for n, v in self._records if (s := _split(n))]

    def __len__(self) -> int:
        return len(self._records)

    @property
    def changed(self) -> bool:
        """True if the bank differs from what was loaded or last saved."""
        return self._dirty

    # --- editing -----------------------------------------------------------------------
    def set(self, campaign: str, key: str, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("bank values are integers")
        if not _I64[0] <= value <= _I64[1]:
            raise ValueError("value out of int64 range")
        name = _name(campaign, key)
        for rec in self._records:
            if rec[0] == name:
                if rec[1] != value:
                    rec[1] = value
                    self._dirty = True
                return
        self._records.append([name, value])  # the game appends new keys too
        self._dirty = True

    def delete(self, campaign: str, key: str) -> bool:
        """Remove a key; returns False if it wasn't there."""
        name = _name(campaign, key)
        before = len(self._records)
        self._records = [r for r in self._records if r[0] != name]
        removed = len(self._records) != before
        self._dirty |= removed
        return removed

    def delete_campaign(self, campaign: str) -> int:
        doomed = list(self.keys(campaign))
        for key in doomed:
            self.delete(campaign, key)
        return len(doomed)

    # --- writing -----------------------------------------------------------------------
    def raw(self) -> bytes:
        """The decompressed file as it would be written."""
        body = b"".join(struct.pack("<Q", len(n)) + n + struct.pack("<q", v)
                        for n, v in self._records)
        return self._head + struct.pack("<I", len(self._records)) + body + self._tail

    def to_bytes(self) -> bytes:
        # Unchanged banks are written back verbatim: the game's deflate encoder isn't zlib's,
        # so recompressing would change the bytes even though the content is identical.
        if not self._dirty:
            return self._original
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        return c.compress(self.raw()) + c.flush()

    def save(self, path: str | os.PathLike | None = None, *, check_game: bool = True) -> Path | None:
        """Write the bank. Backs up an existing target to `<name>.<YYYYmmdd-HHMMSS>.bak` first.

        Returns the backup path (None if the target didn't exist)."""
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError("no path to save to")
        if check_game:
            from ..game import GAME_EXE, is_running

            if is_running():
                raise GameRunningError(f"{GAME_EXE} is running; it would overwrite Player.nfp "
                                       "on exit. Close the game first.")
        data = self.to_bytes()
        Bank(data)  # never write something we can't read back
        backup = None
        if target.exists():
            stamp = time.strftime("%Y%m%d-%H%M%S")
            backup = target.with_name(f"{target.name}.{stamp}.bak")
            n = 1
            while backup.exists():
                backup = target.with_name(f"{target.name}.{stamp}-{n}.bak")
                n += 1
            backup.write_bytes(target.read_bytes())
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)
        self.path, self._original, self._dirty = target, data, False
        return backup


def load(path: str | os.PathLike | None = None) -> Bank:
    p = Path(path) if path is not None else default_path()
    return Bank(p.read_bytes(), p)


def save(bank: Bank, path: str | os.PathLike | None = None, **kw) -> Path | None:
    return bank.save(path, **kw)


__all__ = ["Bank", "BankFormatError", "GameRunningError", "default_path", "find_profiles",
           "load", "save"]
