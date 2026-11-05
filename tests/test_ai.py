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
        script = build_script({"build_order": [{"train": "HOPLITE", "count": 5}]}, "ror")
    skip = script[script.index("; step 1: affordable"):]
    assert "(food-amount >= 60)" in skip and "(gold-amount >= 40)" in skip    # only skipped when it could be paid for
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
