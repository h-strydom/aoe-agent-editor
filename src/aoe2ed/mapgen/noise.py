"""Deterministic value noise (no dependency on Python's randomized hash)."""
from __future__ import annotations

_M64 = 0xFFFFFFFFFFFFFFFF


class ValueNoise:
    """Fractal value noise in [0, 1]. `period` is the feature size in tiles."""

    def __init__(self, seed: int, period: float = 12.0, octaves: int = 3):
        self.seed = seed & _M64
        self.period = period
        self.octaves = octaves

    def _lattice(self, ix: int, iy: int, octave: int) -> float:
        n = (ix * 0x9E3779B1 + iy * 0x85EBCA77 + (self.seed + octave * 0x27D4EB2F) * 0xC2B2AE3D) & _M64
        n ^= n >> 29
        n = (n * 0xBF58476D1CE4E5B9) & _M64
        n ^= n >> 32
        return (n & 0xFFFFFF) / 0xFFFFFF

    def _smooth(self, x: float, y: float, octave: int) -> float:
        ix, iy = int(x // 1), int(y // 1)
        fx, fy = x - ix, y - iy
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = self._lattice(ix, iy, octave), self._lattice(ix + 1, iy, octave)
        c, d = self._lattice(ix, iy + 1, octave), self._lattice(ix + 1, iy + 1, octave)
        return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy

    def __call__(self, x: float, y: float) -> float:
        total, amp, norm, freq = 0.0, 1.0, 0.0, 1.0 / self.period
        for o in range(self.octaves):
            total += amp * self._smooth(x * freq, y * freq, o)
            norm += amp
            amp *= 0.5
            freq *= 2
        return total / norm
