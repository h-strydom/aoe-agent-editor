"""Shared context for building blocks.

A block is a function `block(ctx, **params) -> dict` that adds triggers/variables/units/XS to
ctx.scenario and returns what it created (trigger names, variables, areas). Blocks compose
through names: variables and areas are referenced by name, never by raw id.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .. import triggers as T

Area = tuple[int, int, int, int]


@dataclass
class Ctx:
    scenario: object
    areas: dict[str, Area] = field(default_factory=dict)
    points: dict[str, tuple[int, int]] = field(default_factory=dict)
    time_scale: float = 1.0          # test mode: 0.1 turns a 45 min survive into 4.5 min
    test_mode: bool = False
    xs_chunks: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    # ---------------------------------------------------------- naming & time
    def secs(self, seconds: float) -> int:
        return max(1, int(round(seconds * self.time_scale)))

    def area(self, ref) -> Area:
        if isinstance(ref, str):
            try:
                return self.areas[ref]
            except KeyError:
                raise KeyError(f"Unknown area '{ref}'. Known: {sorted(self.areas)}") from None
        x1, y1, x2, y2 = ref
        return (int(x1), int(y1), int(x2), int(y2))

    def point(self, ref) -> tuple[int, int]:
        if isinstance(ref, str):
            if ref in self.points:
                return self.points[ref]
            x1, y1, x2, y2 = self.area(ref)
            return ((x1 + x2) // 2, (y1 + y2) // 2)
        return (int(ref[0]), int(ref[1]))

    # ---------------------------------------------------------- scenario edits
    def var(self, name: str) -> str:
        """Ensure a trigger variable exists; returns its name (usable in trigger dicts)."""
        T.Resolver(self.scenario).variable(name)
        return name

    def triggers(self, *specs: dict) -> list[str]:
        T.add_triggers(self.scenario, list(specs))
        return [s["name"] for s in specs]

    def trigger(self, name: str, conditions=(), effects=(), **flags) -> str:
        return self.triggers({"name": name, "conditions": list(conditions), "effects": list(effects), **flags})[0]

    def xs(self, code: str) -> None:
        """Queue XS; the compiler embeds all chunks once at the end."""
        self.xs_chunks.append(code)

    def flush_xs(self) -> None:
        if self.xs_chunks:
            xm = self.scenario.xs_manager
            if not xm._initialized:
                # Script Call messages compile in trigger order and XS needs definitions before
                # use, so the shared library trigger must come first.
                xm.initialise_xs_trigger(insert_index=0)
            xm.add_script(xs_string="\n\n".join(self.xs_chunks))
            self.xs_chunks.clear()


def area_kw(a: Area) -> dict:
    return {"area": list(a)}


def spread(area: Area, n: int) -> list[tuple[float, float]]:
    """n deterministic, roughly even positions inside an area (tile centres)."""
    x1, y1, x2, y2 = area
    w, h = x2 - x1 + 1, y2 - y1 + 1
    cols = max(1, min(w, int((n * w / max(h, 1)) ** 0.5 + 0.999)))
    rows = max(1, -(-n // cols))
    out = []
    for i in range(n):
        cx = x1 + (i % cols + 0.5) * w / cols
        cy = y1 + ((i // cols) % rows + 0.5) * h / rows
        out.append((int(cx), int(cy)))
    return out
