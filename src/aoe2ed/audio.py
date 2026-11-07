"""Sounds for mods: the .wem files AoE2 DE and Return of Rome play from a mod's sounds folder.

The game plays a mod's own sound by name (no extension) from <mod>/[modes/Pompeii/]resources/_common/drs/sounds
(screens.SOUND_DIRS): a campaign intro's or outro's "Sound", or a trigger's Sound (Event) Name. Only .wem files
play: MP3, WAV and OGG files are ignored. Uncompressed PCM in a RIFF/WAVE container is enough, so no Wwise
authoring tool is needed.

Verified in game (Return of Rome campaign intros, 2026-11-07): both a Wwise-style PCM .wem (format 0xFFFE with
Wwise's 6-byte extension) and a plain PCM WAV renamed .wem played as an intro's "Sound" (mono, 16-bit, 48 kHz,
with the files in both the mod's root and modes/Pompeii sounds folders).
"""
from __future__ import annotations

import struct

WWISE_EXTENSIBLE = 0xFFFE
CHANNEL_MASKS = {1: 0x4, 2: 0x3}         # mono: front centre; stereo: front left and right


def pcm_wem(samples: bytes, rate: int, channels: int = 1) -> bytes:
    """A .wem holding 16-bit little-endian PCM `samples` (interleaved if stereo), as Wwise writes PCM."""
    if channels not in CHANNEL_MASKS:
        raise ValueError(f"channels is 1 or 2, got {channels}")
    if len(samples) % (2 * channels):
        raise ValueError("samples must be whole 16-bit frames")
    block = 2 * channels
    fmt = struct.pack("<HHIIHHHHI", WWISE_EXTENSIBLE, channels, rate, rate * block, block, 16, 6, 16,
                      CHANNEL_MASKS[channels])
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt
            + b"data" + struct.pack("<I", len(samples)) + samples)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def wem_seconds(wem: bytes) -> float:
    """How long a PCM .wem from pcm_wem plays."""
    if wem[:4] != b"RIFF" or wem[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE .wem")
    channels, rate = struct.unpack_from("<HI", wem, 22)
    size = struct.unpack_from("<I", wem, wem.index(b"data") + 4)[0]
    return size / (2 * channels * rate)
