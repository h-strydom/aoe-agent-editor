"""generate(spec) -> GeneratedMap: run the step pipeline and write the result into a scenario."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .canvas import Canvas
from .spec import MapSpec, Rect
from .steps import DEFAULT_PIPELINE, STEPS, GenContext


@dataclass
class GeneratedMap:
    scenario: object                    # AoE2DEScenario
    areas: dict[str, Rect]              # inclusive tile rectangles (x1, y1, x2, y2)
    spec: MapSpec
    canvas: Canvas
    starts: list[tuple[int, int]] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def save(self, path: str | os.PathLike) -> str:
        path = str(path)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.scenario.write_to_file(path)
        return path

    def render(self, out_png: str | os.PathLike | None = None, **kwargs):
        from ..render import render_scenario
        kwargs.setdefault("show_areas", self.areas)
        return render_scenario(self.scenario, out_png, **kwargs)


def build_canvas(spec: MapSpec, pipeline: list[str] | None = None) -> GenContext:
    """Run the steps on an empty canvas (no scenario involved)."""
    ctx = GenContext(spec, Canvas(spec.size))
    for name in pipeline or spec.steps or DEFAULT_PIPELINE:
        try:
            step = STEPS[name]
        except KeyError:
            raise ValueError(f"Unknown step {name!r}; steps: {list(STEPS)}") from None
        step(ctx)
    return ctx


def write_canvas(ctx: GenContext, scenario) -> None:
    """Replace the scenario's map, units and player count with the canvas contents."""
    c, spec = ctx.canvas, ctx.spec
    mm, um, pm = scenario.map_manager, scenario.unit_manager, scenario.player_manager
    mm.map_size = c.size
    for tile in mm.terrain:
        i = tile.x + tile.y * c.size
        tile.terrain_id = c.terrain[i]
        tile.elevation = c.elevation[i]
        tile.layer = -1
    for player_units in um.units:
        for u in list(player_units):
            um.remove_unit(unit=u)
    for u in c.units:
        um.add_unit(u.player, u.unit_const, x=u.x, y=u.y, rotation=u.rotation)
    pm.active_players = len(spec.players) + spec.extra_players
    for k, (x, y) in enumerate(ctx.data.get("starts", []), start=1):
        p = pm.players[k]
        p.initial_player_view_x, p.initial_player_view_y = x, y


def generate(spec: MapSpec | dict, *, scenario=None, pipeline: list[str] | None = None) -> GeneratedMap:
    """Generate a map from `spec` (a MapSpec or a dict for MapSpec.from_dict).

    Writes terrain, elevation and units into `scenario` (default: a new default DE scenario),
    replacing its existing map and units, and returns the scenario with the named areas.
    The same spec (including seed) always produces the same map.
    """
    if isinstance(spec, dict):
        spec = MapSpec.from_dict(spec)
    ctx = build_canvas(spec, pipeline)
    if scenario is None:
        from .._parser import AoE2DEScenario
        scenario = AoE2DEScenario.from_default()
    write_canvas(ctx, scenario)
    stats = {"units": len(ctx.canvas.units), "forest_tiles": ctx.data.get("forest_tiles", 0)}
    return GeneratedMap(scenario, dict(ctx.areas), spec, ctx.canvas, list(ctx.data.get("starts", [])), stats)
