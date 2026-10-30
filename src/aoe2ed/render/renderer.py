"""Render a scenario's map to a PNG so an agent can look at what it built."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Mapping

from PIL import Image, ImageDraw, ImageFont

from ..mapgen.compass import corner_names
from . import colors as C

Rect = tuple[int, int, int, int]
AREA_COLORS = [(255, 255, 255), (255, 80, 80), (80, 200, 255), (255, 200, 40), (190, 120, 255),
               (120, 255, 140), (255, 140, 0), (255, 100, 220)]
TRIGGER_AREA_COLOR = (0, 255, 255)


@dataclass
class _View:
    """Maps world coordinates (tile units, floats) to output pixels."""
    size: int
    scale: float
    orientation: str
    margin: int

    @property
    def image_size(self) -> tuple[int, int]:
        m2 = 2 * self.margin
        if self.orientation == "diamond":
            return int(2 * self.size * self.scale) + m2, int(self.size * self.scale) + m2
        return int(self.size * self.scale) + m2, int(self.size * self.scale) + m2

    def px(self, x: float, y: float) -> tuple[float, float]:
        s, m, n = self.scale, self.margin, self.size
        if self.orientation == "diamond":
            return m + (x + y) * s, m + (y - x + n) * s / 2
        return m + x * s, m + y * s

    def quad(self, x1: float, y1: float, x2: float, y2: float) -> list[tuple[float, float]]:
        """Polygon of the world rectangle [x1,x2] x [y1,y2] (continuous coordinates)."""
        return [self.px(x1, y1), self.px(x2, y1), self.px(x2, y2), self.px(x1, y2)]


def _font(px: int):
    try:
        return ImageFont.load_default(size=px)
    except TypeError:  # Pillow without FreeType
        return ImageFont.load_default()


def _shade(rgb: C.RGB, factor: float) -> C.RGB:
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def _base_raster(size: int, terrain: list[int], elevation: list[int], show_elevation: bool) -> Image.Image:
    """One pixel per tile: column = x, row = y."""
    data = []
    for y in range(size):
        for x in range(size):
            i = x + y * size
            rgb = C.TERRAIN_COLORS.get(terrain[i], C.UNKNOWN_TERRAIN)
            if show_elevation:
                e = elevation[i]
                # Light comes from the north corner: (x+1, y-1).
                nx, ny = min(size - 1, x + 1), max(0, y - 1)
                facing = e - elevation[nx + ny * size]
                rgb = _shade(rgb, 0.84 + 0.06 * e + 0.14 * facing)
            data.append(rgb)
    img = Image.new("RGB", (size, size))
    img.putdata(data)
    return img


def _place_raster(base: Image.Image, view: _View) -> Image.Image:
    out = Image.new("RGB", view.image_size, (24, 24, 28))
    n, s, m = view.size, view.scale, view.margin
    if view.orientation == "diamond":
        w, h = int(2 * n * s), int(n * s)
        # Inverse of px(): x = u/2s - v/s + n/2, y = u/2s + v/s - n/2.
        coeffs = (1 / (2 * s), -1 / s, n / 2, 1 / (2 * s), 1 / s, -n / 2)
        tile = base.transform((w, h), Image.Transform.AFFINE, coeffs, Image.Resampling.NEAREST,
                              fillcolor=(24, 24, 28))
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon([(0, h / 2), (w / 2, 0), (w, h / 2), (w / 2, h)], fill=255)
        out.paste(tile, (m, m), mask)
    else:
        out.paste(base.resize((int(n * s), int(n * s)), Image.Resampling.NEAREST), (m, m))
    return out


def _player_colors(scenario) -> dict[int, C.RGB]:
    out = {}
    for p in scenario.player_manager.players:
        color = getattr(p, "color", None)
        out[p.player_id] = C.player_color(getattr(color, "value", color), p.player_id)
    return out


def _draw_units(draw: ImageDraw.ImageDraw, view: _View, scenario) -> None:
    pcolors = _player_colors(scenario)
    outline = view.scale >= 5
    layers: dict[str, list] = {"tree": [], "res": [], "building": [], "unit": []}
    for player, units in enumerate(scenario.unit_manager.units):
        for u in units:
            cls = C.object_class(u.unit_const)
            key = {"tree": "tree", "gold": "res", "stone": "res", "food": "res", "cliff": "res",
                   "building": "building"}.get(cls, "unit")
            layers[key].append((player, u, cls))

    for _, u, _ in layers["tree"]:
        tx, ty = int(u.x), int(u.y)
        draw.polygon(view.quad(tx, ty, tx + 1, ty + 1), fill=C.TREE_COLOR)
    for _, u, cls in layers["res"]:
        tx, ty = int(u.x), int(u.y)
        if cls == "cliff":
            draw.polygon(view.quad(tx - 0.5, ty - 0.5, tx + 1.5, ty + 1.5), fill=C.CLIFF_COLOR)
            continue
        fill = {"gold": C.GOLD_COLOR, "stone": C.STONE_COLOR, "food": C.FOOD_COLOR}[cls]
        draw.polygon(view.quad(tx + 0.1, ty + 0.1, tx + 0.9, ty + 0.9), fill=fill,
                     outline=(40, 30, 0) if outline else None)
    for player, u, _ in layers["building"]:
        half = C.building_size(u.unit_const) / 2
        draw.polygon(view.quad(u.x - half, u.y - half, u.x + half, u.y + half),
                     fill=pcolors.get(player, C.GAIA_COLOR), outline=(0, 0, 0))
    r = max(1.5, view.scale * 0.42)
    for player, u, cls in layers["unit"]:
        cx, cy = view.px(u.x, u.y)
        if cls == "food_animal":
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=C.FOOD_COLOR)
        elif player == 0:  # decorations, rocks, wolves...: small and faint
            rr = max(0.8, r * 0.45)
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=C.OTHER_GAIA_COLOR + (110,))
        else:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pcolors.get(player, C.GAIA_COLOR),
                         outline=(0, 0, 0) if outline else None)


def trigger_areas(scenario) -> dict[str, Rect]:
    """Areas used by trigger conditions/effects, keyed '<trigger id>:<trigger name>'."""
    out: dict[str, Rect] = {}
    for t in scenario.trigger_manager.triggers:
        items = list(getattr(t, "conditions", [])) + list(getattr(t, "effects", []))
        for k, item in enumerate(items):
            a = tuple(getattr(item, f, None) for f in ("area_x1", "area_y1", "area_x2", "area_y2"))
            if None in a or -1 in a:
                continue
            key = f"{t.trigger_id}:{t.name}"
            if key in out and out[key] != a:
                key = f"{key}#{k}"
            out[key] = a
    return out


def _draw_areas(draw: ImageDraw.ImageDraw, view: _View, areas: Mapping[str, Rect],
                color_for: Callable[[int], C.RGB], font) -> None:
    for idx, (name, (x1, y1, x2, y2)) in enumerate(areas.items()):
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        col = color_for(idx)
        poly = view.quad(x1, y1, x2 + 1, y2 + 1)
        draw.polygon(poly, fill=col + (40,), outline=col + (255,), width=2)
        # Label at the top-most corner of the shape.
        lx, ly = min(poly, key=lambda p: (p[1], p[0]))
        tb = draw.textbbox((lx + 3, ly + 2), name, font=font)
        draw.rectangle([tb[0] - 2, tb[1] - 1, tb[2] + 2, tb[3] + 1], fill=(0, 0, 0, 170))
        draw.text((lx + 3, ly + 2), name, fill=col + (255,), font=font)


def _draw_frame(draw: ImageDraw.ImageDraw, view: _View, font, grid: bool) -> None:
    n = view.size
    if grid and view.orientation == "square":
        step = 10 if n <= 120 else 20 if n <= 260 else 40
        for v in range(0, n + 1, step):
            draw.line([view.px(v, 0), view.px(v, n)], fill=(255, 255, 255, 38))
            draw.line([view.px(0, v), view.px(n, v)], fill=(255, 255, 255, 38))
            bx, by = view.px(v, 0)
            draw.text((bx, by - 3), str(v), fill=(200, 200, 200, 255), font=font, anchor="mb")
            lx, ly = view.px(0, v)
            draw.text((lx - 4, ly), str(v), fill=(200, 200, 200, 255), font=font, anchor="rm")
    for d, (x, y) in corner_names(n).items():
        cx, cy = view.px(x + 0.5, y + 0.5)
        mx, my = view.px(n / 2, n / 2)
        ox, oy = cx - mx, cy - my
        norm = max(1.0, (ox * ox + oy * oy) ** 0.5)
        off = 14 if view.orientation == "diamond" else 24
        tx, ty = cx + ox / norm * off, cy + oy / norm * off
        draw.text((tx, ty), d.upper(), fill=(255, 255, 255, 255), font=font, anchor="mm")


def render_scenario(scenario, out_png: str | os.PathLike | None = None, *, scale: float | None = None,
                    show_units: bool = True, show_areas: Mapping[str, Rect] | None = None,
                    show_elevation: bool = True, show_trigger_areas: bool = False,
                    orientation: str = "square", grid: bool = True,
                    title: str | None = None) -> Image.Image:
    """Draw the scenario's map: terrain colors, elevation shading, units, labelled areas.

    `scenario` is an AoE2DEScenario or a path to one. `scale` is pixels per tile (default:
    about 720 px across). `show_areas` maps names to inclusive tile rectangles (x1,y1,x2,y2),
    e.g. GeneratedMap.areas. `orientation`: "square" (x right, y down, north at the
    top-right, axis ticks every 10/20 tiles) or "diamond" (as the in-game minimap, north at the top). Corners are labelled with
    their compass direction. Returns the image and writes it to `out_png` when given.
    """
    if isinstance(scenario, (str, os.PathLike)):
        from .._parser import AoE2DEScenario
        scenario = AoE2DEScenario.from_file(str(scenario))
    if orientation not in ("square", "diamond"):
        raise ValueError("orientation must be 'square' or 'diamond'")
    mm = scenario.map_manager
    n = mm.map_size
    if scale is None:
        scale = max(2, round(720 / n))
    if orientation == "diamond":
        scale = scale * 0.71
    view = _View(n, float(scale), orientation, margin=40)
    tiles = mm.terrain
    base = _base_raster(n, [t.terrain_id for t in tiles], [t.elevation for t in tiles], show_elevation)
    img = _place_raster(base, view)
    draw = ImageDraw.Draw(img, "RGBA")
    font = _font(12)
    if show_units:
        _draw_units(draw, view, scenario)
    _draw_frame(draw, view, font, grid)
    if show_areas:
        _draw_areas(draw, view, show_areas, lambda i: AREA_COLORS[i % len(AREA_COLORS)], font)
    if show_trigger_areas:
        _draw_areas(draw, view, trigger_areas(scenario), lambda i: TRIGGER_AREA_COLOR, font)
    if title:
        draw.text((view.margin, 8), title, fill=(255, 255, 255, 255), font=_font(14))
    if out_png is not None:
        os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
        img.save(out_png)
    return img

