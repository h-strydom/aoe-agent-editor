"""Campaign screens: the map, mission flags and intro slideshows the game shows for a campaign.

Verified in game (Return of Rome, 2026-11-01):
  - A campaign's screen comes from `<name>_layout.json` (background, title, one button per mission)
    and its intros from `<name>.json`, next to `<name>.aoe2campaign`.
  - The game only reads them from a mod: `<profile>/mods/local/<Mod>/[modes/Pompeii/]resources/_common/
    campaign/`. Next to a campaign in the profile's own campaign folder they are ignored.
  - The campaign's internal name must equal `<name>` (the official files do this: acam1 -> "acam1").
  - Text can be literal (TitleLabel, labels); the game's own materials (backgrounds, CampaignIcon*)
    work from a mod's layout. Without a layout the game shows its default book with up to 9 flags.
Community reference for every layout key: the "JSON Kungfu" guide,
https://steamcommunity.com/sharedfiles/filedetails/?id=2363743236 (custom images: `UserMaterials`,
files in the same folder; backgrounds 5120x2160 .dds; ZPlane removed or icons and labels vanish).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .campaign import Campaign
from .config import paths

GAME_CAMPAIGN_DIRS = {"aoe2": Path("resources") / "_common" / "campaign",
                      "ror": Path("modes") / "Pompeii" / "resources" / "_common" / "campaign"}
_LEADING_ZERO = re.compile(r"(:\s*)0+(\d)")   # official files have numbers like 09.21; strict JSON rejects them
STATES = ("Normal", "Hover", "Pressed", "Disabled")


def read_json(path: str | Path) -> dict:
    """Read a game JSON file, tolerating what the game tolerates (BOM, leading zeros)."""
    return json.loads(_LEADING_ZERO.sub(r"\1\2", Path(path).read_text(encoding="utf-8-sig")))


def game_campaign_dir(game: str = "aoe2", game_dir: Path | None = None) -> Path:
    root = game_dir or paths().game
    if root is None:
        raise RuntimeError("AoE2 DE install not found; set AOE2DE_PATH")
    return Path(root) / GAME_CAMPAIGN_DIRS[game]


def official_screens(game: str = "aoe2", game_dir: Path | None = None) -> list[dict]:
    """The game's own campaign layouts: name, title string, background, mission buttons, intro file."""
    folder = game_campaign_dir(game, game_dir)
    out = []
    for f in sorted(folder.glob("*_layout.json")):
        name = f.name[: -len("_layout.json")]
        try:
            lay = read_json(f)
        except ValueError as e:
            out.append({"name": name, "error": str(e)})
            continue
        widgets = _widgets(lay)
        out.append({"name": name, "title": widgets.get("TitleLabel", {}).get("Text"),
                    "background": lay.get("BackgroundMaterial"),
                    "missions": sum(1 for n in widgets if n.startswith("ScenarioButton")),
                    "icons": [_material(widgets[n]) for n in sorted(widgets, key=_button_no) if n.startswith("ScenarioButton")],
                    "intro": (folder / f"{name}.json").is_file()})
    return out


def _widgets(lay: dict) -> dict[str, dict]:
    return {w["Widget"].get("Name", ""): w["Widget"] for w in lay.get("Widgets", [])}


def _button_no(name: str) -> int:
    return int(name[len("ScenarioButton"):]) if name.startswith("ScenarioButton") else 0


def _material(widget: dict) -> str | None:
    m = widget.get("StateMaterials", {}).get("StateNormal", {}).get("Material")
    return m[: -len("Normal")] if m and m.endswith("Normal") else m


def strip_zplane(node) -> None:
    """Remove every ZPlane key: with it set, a mod campaign's icons and labels disappear."""
    if isinstance(node, dict):
        node.pop("ZPlane", None)
        for v in node.values():
            strip_zplane(v)
    elif isinstance(node, list):
        for v in node:
            strip_zplane(v)


def layout_from_official(name: str, *, title: str | None = None, labels: list[str] | None = None,
                         game: str = "aoe2", game_dir: Path | None = None) -> dict:
    """An official campaign's layout (background, icons, positions) with your title and mission labels.
    labels must match its number of mission buttons."""
    lay = read_json(game_campaign_dir(game, game_dir) / f"{name}_layout.json")
    widgets = _widgets(lay)
    buttons = sorted((n for n in widgets if n.startswith("ScenarioButton")), key=_button_no)
    if labels is not None:
        if len(labels) != len(buttons):
            raise ValueError(f"{name} has {len(buttons)} mission buttons, got {len(labels)} labels")
        for n, label in zip(buttons, labels, strict=True):
            for child in widgets[n].get("ChildWidgets", []):
                if child["Widget"].get("Type") == "CampaignTitle":
                    child["Widget"]["Text"] = label
    if title is not None:
        widgets["TitleLabel"]["Text"] = title
    strip_zplane(lay)
    return lay


def intro_from_official(name: str, *, missions: int | None = None, game: str = "aoe2",
                        game_dir: Path | None = None) -> dict:
    """An official campaign's intro file (slideshows with narration), optionally checked against a mission count."""
    intro = read_json(game_campaign_dir(game, game_dir) / f"{name}.json")
    if missions is not None and len(intro.get("Scenarios", [])) != missions:
        raise ValueError(f"{name}.json has {len(intro.get('Scenarios', []))} intros, the campaign has {missions} missions")
    return intro


def _font(size: int, rgba: tuple[int, int, int, int]) -> dict:
    r, g, b, a = rgba
    return {"Font": {"FontIndex": 0, "PointSize": size, "Style": "Normal", "TextColor": {"r": r, "g": g, "b": b, "a": a}}}


def build_layout(*, title: str, background: str, buttons: list[dict], user_materials: list[dict] | None = None) -> dict:
    """A layout from scratch. background: a material name (the game's, or one in user_materials).
    buttons, one per mission in order: {x, y, size=250, icon: "CampaignIconChariot" (material prefix;
    Normal/Hover/Pressed/Disabled are appended), label, label_x=0, label_y=160, level=0}.
    user_materials: [{"Material": name, "FileName": "file.dds|png", "Blend": "None"}] for your own images,
    which go next to the layout in the mod."""
    widgets = [{"Widget": {
        "Type": "Label", "Name": "TitleLabel",
        "ViewPort": {"xorigin": 1920, "yorigin": 110, "width": 1000, "height": 100, "alignment": "CentreCentre"},
        "StateMaterials": {"StateNormal": _font(70, (57, 28, 27, 255))},
        "Text": title, "TextAnchor": "CentreCentre", "ChildWidgets": []}}]
    for i, b in enumerate(buttons, start=1):
        size = b.get("size", 250)
        states = {}
        for s in STATES:
            st = _font(34, (42, 10, 82, 128 if s == "Disabled" else 255))
            if b.get("icon"):
                st["Material"] = f"{b['icon']}{s}"
            states[f"State{s}"] = st
        widgets.append({"Widget": {
            "Type": "Button", "Name": f"ScenarioButton{i}",
            "ViewPort": {"xorigin": b["x"], "yorigin": b["y"], "width": size, "height": size, "alignment": "TopLeft"},
            "Image": {"xorigin": 0, "yorigin": 0, "width": size, "height": size, "alignment": "TopLeft"},
            "StateMaterials": states,
            "ChildWidgets": [{"Widget": {
                "Type": "CampaignTitle", "Name": f"CampaignButton{i}Label",
                "ViewPort": {"xorigin": b.get("label_x", 0), "yorigin": b.get("label_y", 160), "width": 700,
                             "height": 100, "alignment": "TopLeft"},
                "ClippingOverride": "Background", "Level": b.get("level", 0),
                "StateMaterials": {"StateNormal": _font(45, (255, 255, 255, 255))},
                "Text": b.get("label", f"{i}"), "TextAnchor": "TopLeft", "ChildWidgets": []}}]}})
    lay: dict = {"BackgroundMaterial": background, "Widgets": widgets}
    if user_materials:
        lay = {"UserMaterials": user_materials, **lay}
    return lay


def mod_dir(mod: str, game: str = "aoe2", profile: Path | None = None) -> Path:
    base = profile or paths().profile
    if base is None:
        raise RuntimeError("AoE2 DE profile folder not found; set AOE2DE_PROFILE")
    return Path(base) / "mods" / "local" / mod


def mod_enabled(mod: str, profile: Path | None = None) -> bool | None:
    """Whether the game lists the local mod as enabled (None: the game hasn't seen it yet)."""
    status = mod_dir(mod, profile=profile).parents[1] / "mod-status.json"
    if not status.is_file():
        return None
    for m in json.loads(status.read_text(encoding="utf-8")).get("Mods", []):
        if m.get("Path") == f"local//{mod}":
            return bool(m.get("Enabled"))
    return None


def install_campaign_mod(campaign: str | Path, mod: str, *, layout: dict | None = None, intro: dict | None = None,
                         files: list[str | Path] | None = None, game: str | None = None, description: str = "",
                         author: str = "", profile: Path | None = None) -> dict:
    """Install a campaign with its screen as a local mod, the only place the game reads layouts from.

    Copies the campaign into the mod's campaign folder with its internal name set to the file stem
    (required for the layout to be found), writes `<stem>_layout.json` / `<stem>.json`, copies `files`
    (custom images named in the layout's UserMaterials) beside them, and writes the mod's info.json.
    The mod must be enabled once in the game (Mods > Installed Mods), then the game restarted."""
    from .game import detect_game
    src = Path(campaign)
    game = game or detect_game(src)
    camp = Campaign.read(src)
    stem = src.stem
    camp.name = stem
    root = mod_dir(mod, game, profile)
    folder = root / GAME_CAMPAIGN_DIRS[game]
    folder.mkdir(parents=True, exist_ok=True)
    written = [camp.write(folder / f"{stem}.aoe2campaign")]
    for suffix, data in (("_layout.json", layout), (".json", intro)):
        dest = folder / f"{stem}{suffix}"
        if data is not None:
            dest.write_text(json.dumps(data, indent=3, ensure_ascii=False), encoding="utf-8")
            written.append(dest)
    for f in files or []:
        dest = folder / Path(f).name
        dest.write_bytes(Path(f).read_bytes())
        written.append(dest)
    info = root / "info.json"
    info.write_text(json.dumps({"Author": author, "CacheStatus": 0, "Description": description, "Title": mod}),
                    encoding="utf-8")
    enabled = mod_enabled(mod, profile)
    return {"mod": str(root), "game": game, "campaign_name": stem, "written": [str(p) for p in written],
            "enabled": enabled,
            "next": None if enabled else "enable the mod in Mods > Installed Mods, then restart the game"}
