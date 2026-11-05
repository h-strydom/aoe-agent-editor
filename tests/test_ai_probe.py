"""AI probes: the instrumented copy, decoding its record, and the checks that read it."""
from __future__ import annotations

import json
import struct

from aoe2ed import games, xs
from aoe2ed.ai import checks
from aoe2ed.ai.probe import MAGIC, STATS, TAG_END, TAG_SAMPLE, decode, tracked_objects, tracked_techs, xs_code
from aoe2ed.session import SESSIONS
from aoe2ed.tools.ai import ai_lint, ai_probe, ai_probe_report
from aoe2ed.tools.scenario import scenario_new

SPEC = {"villagers": 20, "build_order": [{"build": "BARRACKS"}, {"build": "ACADEMY"}, {"train": "HOPLITE", "count": 5}],
        "attack": {"first": 300, "min_group": 5}}


def test_probe_xs_checks_clean():
    result = xs.check(xs_code([1, 2], [83, 103], 15, 600))
    assert result["ok"], result


def test_tracked_objects_include_where_things_are_made():
    with games.use("ror"):
        objs = tracked_objects({2: {"build_order": [{"train": "HOPLITE"}]}}, "ror")
    assert {"HOPLITE", "ACADEMY", "VILLAGER_MALE"} <= set(objs.values())


def test_lint_catches_missing_and_age_look_buildings():
    found = ai_lint({"build_order": [{"build": "ACADEMY_AGE3"}]})["findings"]
    assert [f["check"] for f in found] == ["age_variant"] and "build ACADEMY" in found[0]["fix"]
    found = ai_lint({"build_order": [{"train": "HOPLITE"}]})["findings"]
    assert [f["check"] for f in found] == ["made_where"] and "ACADEMY" in found[0]["message"]
    assert not ai_lint({"build_order": [{"train": "HOPLITE"}]}, have=["ACADEMY"])["findings"]
    assert not ai_lint(SPEC)["findings"]


def _record(players, tracked, rows, ended=None):
    """Encode a probe record: rows = [(t, {player: (stats dict, {oid: (total, done)})})]."""
    vals = [MAGIC, 1, len(players), *players, len(tracked), *tracked, 15, 900]
    for t, per in rows:
        vals += [TAG_SAMPLE, t]
        for p in players:
            stats, objs = per[p]
            vals += [stats.get(k, 0) for k in STATS]
            for o in tracked:
                vals += list(objs.get(o, (0, 0)))
    if ended is not None:
        vals += [TAG_END, ended]
    return struct.pack(f"<{len(vals)}i", *vals)


def test_checks_on_a_stuck_ai(tmp_path):
    with games.use("ror"):
        names = tracked_objects({2: SPEC}, "ror")
    ids = {v: k for k, v in names.items()}
    tracked = sorted(names)
    rows = []
    for t in range(0, 961, 60):            # barracks built, academy never, 10 villagers, gold piling up, no kills
        rows.append((t, {1: ({"villagers": 3}, {}),
                         2: ({"villagers": 10, "gold": 100 + t, "population": 12, "population_cap": 20,
                              "food_total": t * 2, "gold_total": t, "military": 2},
                             {ids["BARRACKS"]: (1, 1), ids["VILLAGER_MALE"]: (10, 10)})}))
    manifest = {"game": "ror", "objects": {str(k): v for k, v in names.items()}, "specs": {"2": SPEC},
                "start_objects": {}}
    record = decode(_record([1, 2], tracked, rows, ended=960), manifest)
    assert record["ended"] == 960 and len(record["samples"]) == 17
    with games.use("ror"):
        report = checks.run(record, manifest)
    found = {f["check"] for f in report["players"][2]["findings"]}
    assert {"never_made", "stalled_build_order", "hoarding", "villagers", "no_attack"} <= found
    assert report["players"][1]["has_spec"] is False and report["players"][2]["summary"]["villagers"] == 10

    path = tmp_path / "p.xsdat"
    path.write_bytes(_record([1, 2], tracked, rows))
    mpath = tmp_path / "p.probe.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = ai_probe_report(str(mpath), str(path))
    assert out["note"] and out["samples"] == 17


def _record_v2(players, tracked, techs, rows):
    """rows = [(t, {player: (stats, {oid: (total, done)}, {tech: state})})]."""
    vals = [MAGIC, 2, len(players), *players, len(tracked), *tracked, len(techs), *techs, 15, 900]
    for t, per in rows:
        vals += [TAG_SAMPLE, t]
        for p in players:
            stats, objs, states = per[p]
            vals += [stats.get(k, 0) for k in STATS]
            for o in tracked:
                vals += list(objs.get(o, (0, 0)))
            vals += [states.get(k, 0) for k in techs]
    return struct.pack(f"<{len(vals)}i", *vals)


def test_v2_research_steps_and_army_only_players():
    spec = {"build_order": [{"build": "BARRACKS"}, {"research": "TOOL_AGE"}, {"train": "CLUBMAN", "count": 3}]}
    with games.use("ror"):
        names = tracked_objects({2: spec, 3: spec}, "ror")
        techs = tracked_techs({2: spec}, "ror")
    ids = {v: k for k, v in names.items()}
    tool = next(iter(techs))
    rows = [(t, {2: ({"villagers": 12, "headroom": 8, "food_total": t, "wood_total": t},
                     {ids["BARRACKS"]: (1, 1)}, {tool: 1}),
                 3: ({"military": 20, "headroom": -20}, {}, {})}) for t in range(0, 601, 60)]
    manifest = {"game": "ror", "objects": {str(k): v for k, v in names.items()},
                "techs": {str(k): v for k, v in techs.items()}, "specs": {"2": spec, "3": spec},
                "start_objects": {"2": [109], "3": [109]}}
    record = decode(_record_v2([2, 3], sorted(names), [tool], rows), manifest)
    assert record["version"] == 2 and record["samples"][0]["players"][2]["techs"] == {"TOOL_AGE": 1}
    with games.use("ror"):
        report = checks.run(record, manifest)
    stalled = [f for f in report["players"][2]["findings"] if f["check"] == "stalled_build_order"]
    assert len(stalled) == 1 and "step 2 (research TOOL_AGE)" in stalled[0]["message"]
    assert [f["check"] for f in report["players"][3]["findings"]] == ["no_builders"]
    assert report["players"][2]["summary"]["gathered_per_minute"]["food"] == 60


def test_ai_probe_writes_copy_and_manifest(tmp_path):
    h = scenario_new(map_size=60, game="ror")["handle"]
    res = ai_probe(h, str(tmp_path / "probe.aoe2scenario"), specs={"2": SPEC}, stop_after=600, install=False)
    m = json.loads((tmp_path / "probe.probe.json").read_text(encoding="utf-8"))
    assert m["record"] == "probe.xsdat" and m["stop_after"] == 600 and "HOPLITE" in m["objects"].values()
    assert res["real_minutes_at_8x"] == 1.2
    scenario = SESSIONS.get(h).scenario
    assert any(t.name == "aoe2ed probe: stop" for t in scenario.trigger_manager.triggers)
