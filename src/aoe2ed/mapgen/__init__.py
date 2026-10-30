"""Spec-driven map generator: terrain, elevation, forests, resources and named areas.

    from aoe2ed.mapgen import MapSpec, generate
    m = generate(MapSpec(size=120, seed=7, players=2))
    m.save("out/land.aoe2scenario"); m.render("out/land.png")
    m.areas["player1_base"]  # (x1, y1, x2, y2)
"""
from .canvas import Canvas
from .generate import GeneratedMap, build_canvas, generate, write_canvas
from .spec import (BIOMES, Biome, CliffSpec, ElevationSpec, ForestSpec, Hill, MapSpec, PlayerStart,
                   ResourceSpec, RoadSpec, UnitPlacement, WaterSpec, ZoneSpec)
from .steps import DEFAULT_PIPELINE, STEPS, GenContext

__all__ = ["BIOMES", "Biome", "Canvas", "CliffSpec", "DEFAULT_PIPELINE", "ElevationSpec", "ForestSpec",
           "GenContext", "GeneratedMap", "Hill", "MapSpec", "PlayerStart", "ResourceSpec", "RoadSpec",
           "STEPS", "UnitPlacement", "WaterSpec", "ZoneSpec", "build_canvas", "generate", "write_canvas"]
