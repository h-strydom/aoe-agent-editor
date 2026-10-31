"""Telemetry harness: injected XS records game state to <scenario name>.xsdat in the profile, so an
agent can see what happened in a playtest without watching the screen.

Stream of int32:
  header  [MAGIC, VERSION, mission_no, n_players, n_vars, player ids..., var ids...]   (v1: no mission_no)
  sample  [1, game_time_s, per player: food, wood, gold, stone, population, units_killed,
           military_count, per var: value]
  event   [2, game_time_s, event_id]          (from telemetry_event() effects in triggers)
xsCreateFile writes <scenario>.xsdat for a standalone scenario but <campaign name>.xsdat inside a
campaign (verified), so every mission of a campaign writes the same file: the latest mission played
overwrites it. mission_no in the header says which one wrote it.
"""
from __future__ import annotations

import struct
from pathlib import Path

MAGIC = 412320001  # XS int literals are limited to 9 digits
VERSION = 2
RESOURCES = ("food", "wood", "gold", "stone", "population", "units_killed", "military")


def xs_code(players: list[int], var_ids: list[int], interval_sec: int = 10, mission_no: int = 0) -> str:
    np, nv = len(players), len(var_ids)
    plist = "".join(f"    xsWriteInt({p});\n" for p in players)
    vlist = "".join(f"    xsWriteInt({v});\n" for v in var_ids)
    per_player = "".join(
        f"    aoe2edWriteAttr({p}, cAttributeFood); aoe2edWriteAttr({p}, cAttributeWood);\n"
        f"    aoe2edWriteAttr({p}, cAttributeGold); aoe2edWriteAttr({p}, cAttributeStone);\n"
        f"    aoe2edWriteAttr({p}, cAttributePopulation); aoe2edWriteAttr({p}, cAttributeKills);\n"
        f"    aoe2edWriteAttr({p}, cAttributeMilitaryPopulation);\n"
        for p in players)
    per_var = "".join(f"    xsWriteInt(xsTriggerVariable({v}));\n" for v in var_ids)
    return f"""// ---- aoe2ed telemetry v{VERSION} ----
void aoe2edWriteAttr(int p = 0, int attr = 0) {{
    int v = xsPlayerAttribute(p, attr);
    xsWriteInt(v);
}}

rule aoe2edTelemetryInit
    active
    highFrequency
{{
    xsCreateFile(false);
    xsWriteInt({MAGIC});
    xsWriteInt({VERSION});
    xsWriteInt({mission_no});
    xsWriteInt({np});
    xsWriteInt({nv});
{plist}{vlist}    xsCloseFile();
    xsDisableSelf();
}}

rule aoe2edTelemetrySample
    active
    minInterval {interval_sec}
{{
    xsCreateFile(true);
    xsWriteInt(1);
    xsWriteInt(xsGetGameTime());
{per_player}{per_var}    xsCloseFile();
}}

void aoe2edTelemetryEvent(int id = 0) {{
    xsCreateFile(true);
    xsWriteInt(2);
    xsWriteInt(xsGetGameTime());
    xsWriteInt(id);
    xsCloseFile();
}}
"""


def event_effect(event_id: int) -> dict:
    """Effect dict that logs an event (put it in any trigger you want to see fire)."""
    return {"type": "script_call", "message": f"void aoe2edEv{event_id}() {{ aoe2edTelemetryEvent({event_id}); }}"}


def decode(data: bytes, var_names: dict[int, str] | None = None, event_names: dict[int, str] | None = None) -> dict:
    vals = list(struct.unpack_from(f"<{len(data) // 4}i", data))
    if len(vals) < 4 or vals[0] != MAGIC:
        return {"error": "not an aoe2ed telemetry file", "raw": vals[:64]}
    version = vals[1]
    if version >= 2:
        mission_no, np, nv = vals[2:5]
        i = 5
    else:
        mission_no, (np, nv) = None, vals[2:4]
        i = 4
    players = vals[i:i + np]; i += np
    var_ids = vals[i:i + nv]; i += nv
    var_names = var_names or {}
    event_names = event_names or {}
    samples, events = [], []
    width = np * len(RESOURCES) + nv
    while i < len(vals):
        tag = vals[i]
        if tag == 1 and i + 2 + width <= len(vals):
            t = vals[i + 1]
            row = vals[i + 2:i + 2 + width]
            s = {"t": t, "players": {}}
            for k, p in enumerate(players):
                chunk = row[k * len(RESOURCES):(k + 1) * len(RESOURCES)]
                s["players"][p] = dict(zip(RESOURCES, chunk))
            s["vars"] = {var_names.get(v, v): x for v, x in zip(var_ids, row[np * len(RESOURCES):])}
            samples.append(s)
            i += 2 + width
        elif tag == 2 and i + 3 <= len(vals):
            events.append({"t": vals[i + 1], "event": event_names.get(vals[i + 2], vals[i + 2])})
            i += 3
        else:
            return {"error": f"bad tag {tag} at {i}", "samples": samples, "events": events}
    return {"version": version, "mission_no": mission_no, "players": players, "samples": samples, "events": events,
            "last": samples[-1] if samples else None}


def read(path: Path, **kw) -> dict:
    return decode(Path(path).read_bytes(), **kw)
