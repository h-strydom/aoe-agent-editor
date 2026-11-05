"""AI probes: watch what computer players actually do in a scenario, without playing it.

probe(scenario) writes an instrumented copy: injected XS records, every `interval` game seconds and for every
player, the stockpile, everything gathered so far, population and its cap, villagers, military, kills, villager
idle time, and how many of each tracked object the player has (counting ones still being built or trained, and
finished ones). At `stop_after` it writes an end marker and ends the game, so a probe never has to run to the
end: 10-15 game minutes is enough to see whether an AI builds, trains and attacks (about 2 real minutes at 8x
with the DEBUGSPEEDS launch option).

The human slot needs nobody at the keyboard: by default player 1's units are left alone, which is also the
cleanest test of whether the enemies attack. Next to the copy goes a manifest (<copy>.probe.json): players, tracked
objects and the AI specs the checks compare against (aoe2ed.ai.checks). report() decodes the record file the
game writes (<copy name>.xsdat in the profile folder) and runs the checks.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

from .. import tables

MAGIC = 412320003                      # XS int literals are limited to 9 digits
VERSION = 2
# cAttributePopulationCap (4) is the room left under the cap, not the cap: population + it stays constant
# (Trojan War probe, 2026-11-05).
STATS = ("food", "wood", "gold", "stone", "food_total", "wood_total", "gold_total", "stone_total",
         "population", "headroom", "villagers", "military", "kills", "idle_seconds")
ATTRIBUTES = ("cAttributeFood", "cAttributeWood", "cAttributeGold", "cAttributeStone",
              "cAttributeFoodTotal", "cAttributeWoodTotal", "cAttributeGoldTotal", "cAttributeStoneTotal",
              "cAttributePopulation", "cAttributePopulationCap", "cAttributeCivilianPopulation",
              "cAttributeMilitaryPopulation", "cAttributeKills", "cAttributeVillagersIdleSecondsTotal")
TAG_SAMPLE, TAG_END = 1, 9
TECH_DONE = 3                          # cTechStateDone; also 0 not ready, 1 ready, 2 researching, 4 queued, -1 disabled


def xs_code(players: list[int], tracked: list[int], interval: int = 15, stop_after: int = 900,
            techs: list[int] = ()) -> str:
    """The recorder: a header, a sample every `interval` seconds, an end marker at `stop_after`."""
    header = "".join(f"    xsWriteInt({v});\n" for v in [MAGIC, VERSION, len(players), *players, len(tracked),
                                                           *tracked, len(techs), *techs, interval, stop_after])
    stats = "".join(f"        aoe2edProbeAttr(p, {a});\n" for a in ATTRIBUTES)
    objects = "".join(f"        xsWriteInt(xsGetObjectCountTotal(p, {o}));\n"
                      f"        xsWriteInt(xsGetObjectCount(p, {o}));\n" for o in tracked)
    objects += "".join(f"        xsWriteInt(xsGetTechState({tech}, p));\n" for tech in techs)
    plist = ", ".join(map(str, players))
    return f"""// ---- aoe2ed AI probe v{VERSION} ----
int aoe2edProbePlayers = -1;
bool aoe2edProbeDone = false;

void aoe2edProbeAttr(int p = 0, int attr = 0) {{
    int v = xsPlayerAttribute(p, attr);
    xsWriteInt(v);
}}

void aoe2edProbeSample() {{
    xsCreateFile(true);
    xsWriteInt({TAG_SAMPLE});
    xsWriteInt(xsGetGameTime());
    for (i = 0; < {len(players)}) {{
        int p = xsArrayGetInt(aoe2edProbePlayers, i);
{stats}{objects}    }}
    xsCloseFile();
}}

rule aoe2edProbeInit
    active
    highFrequency
{{
    aoe2edProbePlayers = xsArrayCreateInt({len(players)}, 0, "aoe2edProbePlayers");
    {"".join(f"xsArraySetInt(aoe2edProbePlayers, {i}, {p}); " for i, p in enumerate(players))}// {plist}
    xsCreateFile(false);
{header}    xsCloseFile();
    xsDisableSelf();
}}

rule aoe2edProbeSampler
    active
    minInterval {interval}
{{
    if (aoe2edProbeDone == false) {{
        aoe2edProbeSample();
    }}
}}

rule aoe2edProbeStop
    active
    minInterval 1
{{
    if (xsGetGameTime() >= {stop_after}) {{
        aoe2edProbeSample();
        xsCreateFile(true);
        xsWriteInt({TAG_END});
        xsWriteInt(xsGetGameTime());
        xsCloseFile();
        aoe2edProbeDone = true;
        xsDisableSelf();
    }}
}}
"""


def tracked_objects(specs: dict[int, dict], game: str, extra: list[str] = ()) -> dict[int, str]:
    """Object ids worth counting for these AI specs: everything they build or train, where it's made, villagers,
    transports; id -> name."""
    from .spec import _step, resolve
    t = tables.load(game)
    out: dict[int, str] = {}

    def add(name: str) -> None:
        try:
            oid = resolve(name, "object", game)
        except (KeyError, ValueError):
            return
        out.setdefault(oid, t["objects"].get(str(oid), {}).get("name", str(name)))

    add("VILLAGER")
    for spec in specs.values():
        for item in [*(spec.get("build_order") or []), *(spec.get("keep") or [])]:
            kind, name, _ = _step(item)
            if kind == "research":
                for at in t["techs"].get(str(resolve(name, "tech", game)), {}).get("researched_at", []):
                    out.setdefault(at, t["objects"][str(at)]["name"])
                continue
            add(name)
            for at in t["objects"].get(str(resolve(name, "object", game)), {}).get("made_at", []):
                out.setdefault(at, t["objects"][str(at)]["name"])
        if spec.get("transports"):
            add(spec.get("transport_unit") or ("LIGHT_TRANSPORT" if game == "ror" else "TRANSPORT_SHIP"))
    for name in extra:
        add(name)
    return out


def tracked_techs(specs: dict[int, dict], game: str) -> dict[int, str]:
    """Tech ids the AI specs research; id -> name."""
    from .spec import _step, resolve
    t = tables.load(game)
    out: dict[int, str] = {}
    for spec in specs.values():
        for item in [*(spec.get("build_order") or []), *(spec.get("keep") or [])]:
            kind, name, _ = _step(item)
            if kind != "research":
                continue
            try:
                tid = resolve(name, "tech", game)
            except (KeyError, ValueError):
                continue
            out.setdefault(tid, t["techs"].get(str(tid), {}).get("name", str(name)))
    return out


def probe(scenario, out: Path, *, specs: dict[int, dict] | None = None, game: str = "ror", stop_after: int = 900,
          interval: int = 15, human: str = "idle", track: list[str] = (), end_game: bool = True) -> dict:
    """Instrument an open scenario (AoE2ScenarioParser object) as a probe and save it to `out` with its manifest.

    specs: {player: AI spec} for the computer players being investigated (from ai_build / a converter), used to
    choose what to count and by the checks. human: "idle" leaves player 1 to whoever starts the game (do nothing,
    or watch); "computer" makes every slot a computer player (needs the lobby to allow an all-AI start).
    end_game: declare a victory at stop_after so the game stops on its own."""
    from ..blocks.base import Ctx
    specs = {int(k): v for k, v in (specs or {}).items()}
    players = [int(p.player_id) for p in scenario.player_manager.players[1:] if p.active]
    objects = tracked_objects(specs, game, list(track))
    tracked = sorted(objects)
    techs = tracked_techs(specs, game)
    if human == "computer":
        for p in scenario.sections["DataHeader"].player_data_1:
            p.human = 0
    elif human != "idle":
        raise ValueError("human is 'idle' or 'computer'")
    ctx = Ctx(scenario)
    ctx.xs(xs_code(players, tracked, interval, stop_after, sorted(techs)))
    if end_game:
        ctx.trigger("aoe2ed probe: stop", [{"type": "timer", "timer": stop_after + 2}],
                    [{"type": "declare_victory", "source_player": players[0], "enabled": True}])
    ctx.flush_xs()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    scenario.write_to_file(str(out))
    start: dict[str, set[int]] = {}
    for u in scenario.unit_manager.get_all_units():
        start.setdefault(str(int(u.player)), set()).add(int(u.unit_const))
    manifest = {"scenario": out.name, "record": out.stem + ".xsdat", "game": game, "players": players,
                "objects": {str(k): v for k, v in objects.items()},
                "techs": {str(k): v for k, v in techs.items()}, "specs": {str(k): v for k, v in specs.items()},
                "start_objects": {p: sorted(ids) for p, ids in start.items()},
                "stop_after": stop_after, "interval": interval, "human": human,
                "tables_build": tables.load(game)["build"]}
    path = out.with_suffix(".probe.json")
    path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return {"scenario": str(out), "manifest": str(path), "record": manifest["record"], "players": players,
            "tracked": list(objects.values()), "real_minutes_at_8x": round(stop_after / 60 / 8, 1)}


def decode(data: bytes, manifest: dict | None = None) -> dict:
    """A probe record -> {"players", "objects", "techs", "samples": [{"t", "players": {p: {stat: v, "objects":
    {name: [total, done]}, "techs": {name: state}}}}], "ended"}. Reads version 1 records too (no techs, and
    "population_cap" for what is really the headroom)."""
    vals = list(struct.unpack_from(f"<{len(data) // 4}i", data))
    if len(vals) < 3 or vals[0] != MAGIC:
        raise ValueError("not an aoe2ed AI probe record")
    version = vals[1]
    i = 2
    np_ = vals[i]
    players = vals[i + 1:i + 1 + np_]
    i += 1 + np_
    nt = vals[i]
    tracked = vals[i + 1:i + 1 + nt]
    i += 1 + nt
    techs: list[int] = []
    if version >= 2:
        nk = vals[i]
        techs = vals[i + 1:i + 1 + nk]
        i += 1 + nk
    interval, stop_after = vals[i:i + 2]
    i += 2
    names = {int(k): v for k, v in (manifest or {}).get("objects", {}).items()}
    tech_names = {int(k): v for k, v in (manifest or {}).get("techs", {}).items()}
    width = len(STATS) + 2 * nt + len(techs)
    samples, ended = [], None
    while i < len(vals):
        tag = vals[i]
        if tag == TAG_SAMPLE and i + 2 + width * np_ <= len(vals):
            s = {"t": vals[i + 1], "players": {}}
            j = i + 2
            for p in players:
                row = vals[j:j + width]
                entry = dict(zip(STATS, row[:len(STATS)]))
                counts = row[len(STATS):len(STATS) + 2 * nt]
                entry["objects"] = {names.get(o, str(o)): [counts[2 * k], counts[2 * k + 1]]
                                    for k, o in enumerate(tracked)}
                states = row[len(STATS) + 2 * nt:]
                entry["techs"] = {tech_names.get(k, str(k)): v for k, v in zip(techs, states, strict=True)}
                s["players"][p] = entry
                j += width
            samples.append(s)
            i = j
        elif tag == TAG_END and i + 2 <= len(vals):
            ended = vals[i + 1]
            i += 2
        else:
            raise ValueError(f"probe record damaged at value {i} (tag {tag})")
    return {"version": version, "players": players, "objects": [names.get(o, str(o)) for o in tracked],
            "techs": [tech_names.get(k, str(k)) for k in techs], "interval": interval, "stop_after": stop_after,
            "samples": samples, "ended": ended}


def timeline(record: dict, player: int, stat: str) -> list[tuple[int, int]]:
    """(time, value) for one player's stat, an object name (its total count, counting ones being made) or a tech
    name (its research state; TECH_DONE once researched)."""
    out = []
    for s in record["samples"]:
        e = s["players"].get(player)
        if e is None:
            continue
        if stat in e:
            v = e[stat]
        elif stat in e.get("techs", {}):
            v = e["techs"][stat]
        else:
            v = e["objects"].get(stat, [0, 0])[0]
        out.append((s["t"], v))
    return out
