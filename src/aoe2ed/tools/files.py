"""Campaign files and the installed game."""
from __future__ import annotations

from pathlib import Path

from .. import game
from ..campaign import Campaign
from ..config import paths
from ..session import SESSIONS, backup_file
from . import tool


def _resolve(path: str, kind: str, suffix: str) -> Path:
    """A path as given, else a bare name in the AoE2 then the Return of Rome profile folder."""
    p = Path(path)
    if p.is_absolute() or p.exists():
        return p
    first = None
    for which in ("aoe2", "ror"):
        cand = paths().user_dir(kind, which) / p
        cand = cand if cand.suffix else cand.with_suffix(suffix)
        first = first or cand
        if cand.exists():
            return cand
    return first


@tool
def campaign_read(path: str) -> dict:
    """List a .aoe2campaign's name and scenarios. A bare name is looked up in the profile."""
    return Campaign.read(_resolve(path, "campaign", ".aoe2campaign")).summary()


@tool
def campaign_build(name: str, scenarios: list[str], out: str | None = None, install: bool = True,
                   overwrite: bool = True) -> dict:
    """Bundle scenario files (paths, or open handles like 's2' which are serialized as-is) into a
    campaign, in play order. `name` is the internal campaign name; the campaign bank
    (Store/Load Key Value) is scoped by it, so keep it stable across rebuilds.
    install=True writes to the profile's campaign folder."""
    camp = Campaign(name)
    for ref in scenarios:
        if ref in [o["handle"] for o in SESSIONS.list()]:
            o = SESSIONS.get(ref)
            if o.source is None:
                raise ValueError(f"Save {ref} to a file first")
            camp.add_scenario_file(o.source)
        else:
            camp.add_scenario_file(_resolve(ref, "scenario", ".aoe2scenario"))
    from .. import games
    which = games.file_game(camp.scenarios[0].data) if camp.scenarios else "aoe2"
    dest = Path(out) if out else (paths().user_dir("campaign", which) / name if install else Path(name))
    dest = dest.with_suffix(".aoe2campaign")
    backup = None
    if dest.exists():
        if not overwrite:
            raise FileExistsError(dest)
        backup = backup_file(dest)
    written = camp.write(dest)
    return {"written": str(written), "backup": str(backup) if backup else None, **camp.summary()}


@tool
def campaign_screens(game: str = "aoe2") -> list[dict]:
    """The game's own campaign screens (layouts) you can reuse: name, background, number of mission
    buttons, the icon of each, whether an intro file exists. game: aoe2 | ror."""
    from .. import screens
    return screens.official_screens(game)


@tool
def campaign_install_mod(campaign: str, mod: str, official: str | None = None, title: str | None = None,
                         labels: list[str] | None = None, intro: bool = True, layout_path: str | None = None,
                         intro_path: str | None = None, files: list[str] | None = None,
                         widget_files: dict[str, str] | None = None) -> dict:
    """Install a campaign with a campaign screen (map background, mission flags/icons, intro slideshows) as
    a local mod: the game only reads screens from mods, and only when the campaign's internal name equals
    its file name (done for you). Either reuse an official screen (`official`, from campaign_screens, with
    your `title` and one label per mission; intro=True also copies its narrated intros when the mission
    count matches) or pass your own `layout_path` / `intro_path` JSON (custom images in `files`, named in
    the layout's UserMaterials). Without a screen, the game's default book shows at most 9 missions.
    Intro slide images: widget_files {"textures/campaign/<name>/<mission>/intro/1.png": source path, ...},
    referenced in the intro JSON as "SlideImageSequence": "textures/campaign/<name>/<mission>/intro/%d.png"
    (one image per slide, counting from 1). Custom sounds don't play; "Sound" takes only the game's events.
    The user must enable the mod once (Mods > Installed Mods) and restart the game."""
    from .. import screens
    src = _resolve(campaign, "campaign", ".aoe2campaign")
    which = game.detect_game(src)
    n = len(Campaign.read(src).scenarios)
    layout = screens.read_json(layout_path) if layout_path else None
    intro_data = screens.read_json(intro_path) if intro_path else None
    if official:
        layout = screens.layout_from_official(official, title=title, labels=labels, game=which)
        buttons = sum(1 for w in layout["Widgets"] if w["Widget"].get("Name", "").startswith("ScenarioButton"))
        if buttons != n:
            raise ValueError(f"{official} has {buttons} mission buttons, the campaign has {n} missions")
        if intro and intro_data is None:
            intro_data = screens.intro_from_official(official, missions=n, game=which)
    return screens.install_campaign_mod(src, mod, layout=layout, intro=intro_data, files=files,
                                        widget_files=widget_files, game=which)


@tool
def campaign_extract(path: str, out_dir: str) -> dict:
    """Write each scenario inside a campaign out as its own .aoe2scenario file."""
    camp = Campaign.read(_resolve(path, "campaign", ".aoe2campaign"))
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    files = []
    for s in camp.scenarios:
        p = d / s.filename
        p.write_bytes(s.data)
        files.append(str(p))
    return {"name": camp.name, "files": files}


@tool
def game_status() -> dict:
    """Is the game running, plus profile paths and the newest XS data files."""
    return {"running": game.is_running(), "paths": paths().as_dict(), "xsdat": game.xsdat_files()[:10]}


@tool
def game_launch() -> dict:
    """Start AoE2 DE via Steam. There is no command-line switch to open a scenario: use desktop
    automation to go Single Player -> Scenario (or Campaigns) and pick the file."""
    return game.launch()


@tool
def game_install(path: str, kind: str | None = None) -> dict:
    """Copy a scenario/campaign/xs/ai file into the profile folder the game reads from."""
    return game.install(path, kind)


@tool
def game_log(session: int = 0, grep: str | None = None, tail: int = 200) -> dict:
    """Engine log lines (MainLog.txt) of a game session, 0 = latest. Network noise is filtered.
    Note: XS chat/print output does not appear here; use telemetry (xsdat) instead."""
    return game.read_log(session, grep, tail)


@tool
def xsdat_list() -> list[dict]:
    """XS data files in the profile (written by xsCreateFile), newest first."""
    return game.xsdat_files()


@tool
def xsdat_read(name: str, as_type: str = "int") -> dict:
    """Decode an .xsdat file as int32 (default) or float32 values."""
    return game.read_xsdat(name, as_type)
