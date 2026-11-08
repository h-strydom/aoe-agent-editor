"""AI scripts: the .per checker, AI specs compiled to scripts, embedding them in a scenario."""
from __future__ import annotations

import pytest

from aoe2ed import games
from aoe2ed.ai import per
from aoe2ed.ai.spec import SpecError, build_script
from aoe2ed.config import find_game_dir
from aoe2ed.session import SESSIONS
from aoe2ed.tools.ai import ai_build, ai_check, ai_lookup, ai_set

SPEC = {"name": "Raiders", "villagers": 20,
        "build_order": [{"build": "BARRACKS"}, {"train": "CLUBMAN", "count": 5}, {"research": "TOOL_AGE"}],
        "attack": {"first": 300, "every": 200, "min_group": 5}, "strategic_numbers": {"sn-number-explore-groups": 1}}


def _severities(text):
    return [(d.severity, d.message) for d in per.check(text)]


def test_checker_finds_structure_errors_and_unknown_names():
    assert _severities("(defrule (true) => (disable-self))") == []
    assert ("error", "'(' is never closed") in _severities("(defrule (true) => (disable-self)")
    assert ("error", "defrule has no '=>'") in _severities("(defrule (true) (disable-self))")
    found = _severities("(defrule (true) => (launch-rockets) (set-strategic-number sn-moon-base 1))")
    assert ("warning", "unknown action 'launch-rockets'") in found
    assert ("warning", "unknown strategic number 'sn-moon-base'") in found
    assert _severities("(defconst my-x 5)\n(defrule (goal my-x 1) => (set-goal my-x 2))") == []


def test_spec_compiles_to_a_clean_ror_script():
    with games.use("ror"):
        script = build_script(SPEC, "ror")
    assert "(defconst my-o-barracks 12)" in script and "(defconst my-o-clubman 281)" in script
    assert "(defconst my-t-tool-age 101)" in script and "(attack-now)" in script
    assert per.check(script) == []
    # setup, 3 steps, 2 waiting, villagers + houses, attack, rebalance (3 pile sizes x 3 sources for each resource
    # the plan spends: food and wood here, + an idle tick)
    assert script.count("(defrule") == 1 + 3 * 3 + 2 + 2 + 1 + 3 * 2 * 3 + 1
    assert "(set-strategic-number sn-percent-attack-soldiers 80)" in script     # AIBuilder's attack
    assert "(up-find-player my-enemy my-find-closest 2)" in script


def test_many_strategic_numbers_split_the_setup():
    sns = {s: 1 for s in sorted(per.vocab()["strategic_numbers"])[:60]}
    with games.use("ror"):
        script = build_script({"strategic_numbers": sns}, "ror")
    assert script.count("; setup ") == 5                             # 4 gatherer + 60 settings + goal = 65 actions
    assert not [d for d in per.check(script) if d.severity == "error"]


def test_spec_errors_are_clear():
    with games.use("ror"), pytest.raises(SpecError, match="unknown object 'TANK'"):
        build_script({"build_order": [{"build": "TANK"}]}, "ror")
    with pytest.raises(SpecError, match="summing to 100"):
        build_script({"gatherers": {"food": 90, "wood": 30, "gold": 0, "stone": 0}}, "ror")
    with pytest.raises(SpecError, match="unknown AI spec keys"):
        build_script({"build_ordr": []}, "ror")


def test_no_attack_means_no_attack_rule():
    with games.use("ror"):
        assert "(attack-now)" not in build_script({"build_order": []}, "ror")


def test_tools_build_check_lookup():
    res = ai_build(SPEC, game="ror")
    assert res["problems"] == [] and res["rules"] > 5
    assert ai_check("(defrule (true) => (disable-self)")["ok"] is False
    assert "sn-minimum-attack-group-size" in [s["name"] for s in ai_lookup("attack-group", "strategic_numbers")["strategic_numbers"]]


def test_ai_set_embeds_the_script():
    o = SESSIONS.new(48, game="ror")
    try:
        res = ai_set(o.handle, 2, SPEC)
        p = o.scenario.player_manager.players[2]
        assert res["ai"] == "Raiders" and p.personality == "Raiders" and "(attack-now)" in p.ai_script
        assert ai_set(o.handle, 3, "immobile")["ai"] == "immobile"
        with pytest.raises(ValueError, match="errors"):
            ai_set(o.handle, 4, "(defrule (true) =>")
    finally:
        SESSIONS.close(o.handle)


@pytest.mark.skipif(find_game_dir() is None, reason="needs the game's own AI scripts")
def test_the_games_own_scripts_have_no_errors():
    root = find_game_dir()
    for folder in ("resources/_common/ai", "modes/Pompeii/resources/_common/ai"):
        for path in (root / folder).rglob("*.per"):
            errors = [d for d in per.check(path.read_text(encoding="utf-8", errors="replace")) if d.severity == "error"]
            assert not errors, (path.name, errors[:3])


def test_player_set_takes_an_ai_spec():
    from aoe2ed.tools.world import player_set
    o = SESSIONS.new(48, game="ror")
    try:
        with games.use("ror"):
            player_set(o.handle, 2, {"ai": {"name": "Raiders", "spec": SPEC}})
        assert o.scenario.player_manager.players[2].personality == "Raiders"
    finally:
        SESSIONS.close(o.handle)


def test_transports_are_kept_from_the_start():
    with games.use("ror"):
        script = build_script({"transports": 2, "keep": [{"build": "DOCK"}], "build_order": [{"build": "HOUSE"}]}, "ror")
    assert "(defconst my-o-light-transport" in script
    assert "(unit-type-count-total my-o-light-transport < 2)" in script
    rule = script[script.index("; transports x2"):]
    assert "goal my-step" not in rule.split(")\n", 3)[0]                 # not gated on the build order
    assert "(build my-o-dock)" in script and per.check(script) == []


def test_naval_attacks_and_debug_chat():
    with games.use("ror"):
        script = build_script({"name": "Troy", "debug": True, "build_order": [{"build": "DOCK"}],
                               "attack": {"first": 60, "naval": True}}, "ror")
    assert "; naval attack" in script and "(warboat-count > 0)" in script
    assert '(chat-to-all "Troy: step 1: build DOCK x1 done")' in script and '"Troy: attacking"' in script
    assert per.check(script) == []


def test_gatherers_follow_what_the_ai_builds():
    from aoe2ed.ai.spec import auto_gatherers, cost
    assert cost("object", 93, "ror") == {"food": 60, "gold": 40}            # hoplite, from RoR's data
    army = auto_gatherers([("object", 38, 20)], "ror")                     # cavalry: 70 food, 80 gold
    assert sum(army.values()) == 100 and army["gold"] > 25 and army["stone"] >= 5
    with games.use("ror"):
        script = build_script({"build_order": [{"train": "CAVALRY", "count": 20}]}, "ror")
    assert f"sn-gold-gatherer-percentage {army['gold']})" in script


def test_steps_wait_for_resources_and_skip_only_the_impossible():
    with games.use("ror"):
        script = build_script({"build_order": [{"build": "ACADEMY"}, {"train": "HOPLITE", "count": 5}]}, "ror")
    skip = script[script.index("; step 1: affordable"):]
    assert "(wood-amount >= 150)" in skip.split("=>")[0]                    # only skipped when it could be paid for
    # a train step counts living units, which attacks keep killing: it moves on after one timeout, paid or not
    train = script[script.index("; step 2: training doesn't block"):].split("=>")[0]
    assert "(timer-triggered 1)" in train and "-amount" not in train
    assert "; step waiting for resources" in script and "(up-modify-goal 3 c:+ 1)" in script
    assert "; step waited too long: skip it" in script and per.check(script) == []


def test_argument_counts_follow_the_games_own_scripts():
    # (goal id value) has no comparison form: RoR refused (goal 3 < 4) with "ERR2011: Missing closing parenthesis"
    assert ("error", "(goal ...) takes 2 arguments in the game's own scripts, not 3") in _severities(
        "(defrule (goal 3 < 4) => (disable-self))")
    assert _severities("(defrule (up-compare-goal 3 < 4) => (disable-self))") == []


def test_window_keep_rebalance_and_scout():
    spec = {"build_order": [{"build": "BARRACKS"}, {"train": "CLUBMAN", "count": 5}, {"build": "DOCK"}],
            "keep": [{"train": "CLUBMAN", "count": 8}], "attack": {"first": 300, "naval": True}}
    with games.use("ror"):
        script = build_script(spec, "ror")
        serial = build_script({**spec, "window": 1, "keep_from": "end", "rebalance": False, "scout": False}, "ror")
    assert per.check(script) == [] and per.check(serial) == []
    # step 3 is worked on from step 1 with the default window of 3; serially only on its own turn
    assert "(up-compare-goal my-step <= 3)\n\t(up-compare-goal my-step > 0)" in script
    assert "(goal my-step 3)\n\t(building-type-count-total" in serial
    keep = script[script.index("; keep CLUBMAN"):]
    assert "my-step" not in keep.split("=>")[0]                    # keep list from the start
    assert "(goal my-step 4)" in serial[serial.index("; keep CLUBMAN"):]
    assert "rebalance" not in serial
    # a shortage of something the plan spends takes from the biggest pile first; nothing feeds stone it never uses
    rules = script.split("(defrule")
    first = next(i for i, r in enumerate(rules) if "rebalance: food runs out, wood over 1600" in r)
    assert first < next(i for i, r in enumerate(rules) if "rebalance: food runs out, wood over 400" in r)
    assert "rebalance: stone runs out" not in script and "rebalance: food runs out, stone over 800" in script
    assert "(train my-o-scout-ship)" in script and "sn-number-boat-explore-groups 1" in script
    assert "scout-ship" not in serial


def test_levels_follow_the_difficulty_and_start_waits_for_the_scenario():
    from aoe2ed.ai.spec import level_specs
    spec = {**SPEC, "keep": [{"train": "CLUBMAN", "count": 10}], "levels": "auto", "start": {"trigger": 3}}
    lv = level_specs(spec)
    assert lv["normal"]["villagers"] == 20 and lv["easy"]["villagers"] == 14 and lv["hard"]["villagers"] == 26
    # easy barely attacks, hard keeps up the pressure
    assert lv["easy"]["attack"]["first"] == 750 and lv["easy"]["attack"]["every"] == 800
    assert lv["hard"]["attack"]["first"] == 180 and lv["hard"]["attack"]["every"] == 80
    assert lv["easy"]["keep"][0]["count"] == 6 and lv["hard"]["keep"][0]["count"] == 15
    with games.use("ror"):
        script = build_script(spec, "ror")
        plain = build_script({k: v for k, v in spec.items() if k not in ("levels", "start")}, "ror")
    assert per.check(script) == []
    assert "(or (difficulty == easiest) (difficulty == easy))" in script and "(difficulty == moderate)" in script
    assert "(event-detected trigger 3)" in script and "(acknowledge-event trigger 3)" in script
    # every generated rule after the level and start rules is gated on both
    rules = script.split("(defrule")[1:]
    gated = [r for r in rules if "(goal 5 " in r.split("=>")[0]]
    assert len(gated) == len(rules) - 5 == 3 * plain.count("(defrule")
    assert all("(goal 6 1)" in r.split("=>")[0] for r in gated)
    override = level_specs({**SPEC, "levels": {"easy": {"attack": {"first": 900}}}})
    assert override["easy"]["attack"] == {**SPEC["attack"], "first": 900} and override["hard"] == override["normal"]
    with pytest.raises(SpecError, match="levels is auto"):
        level_specs({"levels": {"brutal": {}}})
    with games.use("ror"), pytest.raises(SpecError, match="start is"):
        build_script({"start": 5}, "ror")


def test_civ_army_favours_the_civs_bonus_units():
    from aoe2ed import civs
    from aoe2ed.ai.spec import civ_army
    greek = [f["unit"] for f in civs.favoured("GREEK")]
    assert greek[0] == "HOPLITE" and "SCOUT_SHIP" not in greek                       # land only by default
    assert [f["unit"] for f in civs.favoured("EGYPTIAN", max_age=2)] == []            # chariots need Bronze
    spec = {"build_order": [{"research": "TOOL_AGE"}, {"research": "BRONZE_AGE"}],
            "keep": [{"train": "CLUBMAN", "count": 10}, {"train": "BOWMAN", "count": 6},
                     {"train": "FISHING_BOAT", "count": 3}], "attack": {"first": 300}, "army": {"civ": "GREEK"}}
    with games.use("ror"):
        out, notes = civ_army(spec, "ror")
        script = build_script(spec, "ror")
        stone_age, _ = civ_army({**spec, "build_order": []}, "ror")
    keep = {k.get("train") or k.get("build"): k.get("count") for k in out["keep"]}
    assert keep["HOPLITE"] == 8 and "ACADEMY" in keep and keep["FISHING_BOAT"] == 3    # boats untouched
    assert keep["CLUBMAN"] + keep["BOWMAN"] + keep["HOPLITE"] == 16                    # same army size
    assert notes[0].startswith("keep HOPLITE x8 (speed +0.27") and per.check(script) == []
    assert stone_age["keep"] == spec["keep"]                                           # no academy in the Stone Age
    with games.use("ror"), pytest.raises(SpecError, match="unknown RoR civ"):
        build_script({"army": {"civ": "ATLANTEAN"}, "keep": [{"train": "CLUBMAN"}]}, "ror")


def test_rebalancing_never_takes_a_share_below_its_floor():
    from aoe2ed.ai.spec import MIN_SHARE, REBALANCE_STEP
    with games.use("ror"):
        script = build_script({"build_order": [{"train": "CAVALRY", "count": 5}]}, "ror")
    # a share must hold floor + step before 5% leaves it (Trojan War probe: gold went 9% -> 4% with "> 5")
    assert f"gatherer-percentage >= {MIN_SHARE + REBALANCE_STEP})" in script
    assert f"gatherer-percentage > {MIN_SHARE})" not in script


def test_grow_macros_toward_the_population_over_time():
    from aoe2ed.ai.spec import level_specs
    spec = {**SPEC, "keep": [{"train": "BOWMAN", "count": 6}, {"train": "CLUBMAN", "count": 4}, {"build": "BARRACKS"}],
            "grow": {"to": 200, "minutes": 40}}
    with games.use("ror"):
        script = build_script(spec, "ror")
    assert per.check(script) == []
    assert "(enable-timer 5 300)" in script                              # 8 stages over 40 minutes
    stage = lambda k: [r for r in script.split("(defrule")[1:] if f"(goal 7 {k})" in r.split("=>")[0]]
    first, last = "".join(stage(1)), "".join(stage(8))
    assert "(civilian-population < 28)" in first and "(civilian-population < 80)" in last   # 20 -> 40% of 200
    # 10 soldiers grow to 200 - 80 - 10 spare = 110, kept in proportion; their buildings along (up to 4)
    assert "(unit-type-count-total my-o-bowman < 66)" in last and "(unit-type-count-total my-o-clubman < 44)" in last
    assert "(building-type-count-total my-o-archery-range < 4)" in last
    assert "(building-type-count-total my-o-barracks < 4)" in last
    assert "(building-type-count-total my-o-town-center < 3)" in last    # expansion
    assert "(building-type-count-total my-o-storage-pit < 3)" in last and "my-o-granary" in last
    assert "(goal 7 9)" not in script
    lv = level_specs({**spec, "levels": "auto"})
    assert [lv[k]["grow"]["minutes"] for k in ("easy", "normal", "hard")] == [120, 40, 20]
    with pytest.raises(SpecError, match="grow is"):
        build_script({**SPEC, "grow": {"speed": 2}}, "ror")


def test_raids_keep_their_party_and_lifetime_keeps_never_replace():
    spec = {"keep": [{"train": "FISHING_BOAT", "count": 5, "lifetime": True},
                     {"research": "TOOLWORKING", "when": {"soldiers": 8}}],
            "raids": [{"units": ["SLINGER", "AXEMAN"], "count": 3, "min": 1, "start": {"trigger": 7},
                       "near": {"x": 47, "y": 20, "radius": 5}},
                      {"units": ["BOWMAN"], "count": 5, "first": 300, "every": 150, "target": "villagers"}]}
    with games.use("ror"):
        script = build_script(spec, "ror")
    assert per.check(script) == []
    assert "(up-compare-goal 50 < 5)" in script and "(up-modify-goal 50 c:+ 1)" in script     # 5 boats, ever
    assert "(defend-soldier-count >= 8)" in script
    assert "(event-detected trigger 7)" in script and "(up-filter-distance c: -1 c: 5)" in script
    assert "(enable-timer 11 300)" in script and "(enable-timer 11 150)" in script            # raid 2's timing
    assert script.count("(up-add-object-by-id my-search-local g: 10") == 3                     # raid 1's party
    assert "(up-find-remote c: 904 c: 40)" in script and "(up-find-remote c: -1 c: 40)" in script
    assert "(up-target-objects 1 my-action-default -1 my-stance-aggressive)" in script
    assert "(defconst my-search-local 1)" in script
    with games.use("ror"):
        assert "my-search-local" not in build_script({"keep": []}, "ror")
        with pytest.raises(SpecError, match="a raid is"):
            build_script({"raids": [{"count": 3}]}, "ror")
        with pytest.raises(SpecError, match="raid target"):
            build_script({"raids": [{"units": ["BOWMAN"], "target": "cows"}]}, "ror")
        with pytest.raises(SpecError, match="keep entries"):
            build_script({"build_order": [{"build": "HOUSE", "lifetime": True}]}, "ror")
