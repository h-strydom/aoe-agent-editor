"""airef (the AI Scripting Encyclopedia) as data, and the checks it adds to the AI script checker."""
from __future__ import annotations

import pytest

from aoe2ed.ai import per
from aoe2ed.ai.reference import parse, reference, signature
from aoe2ed.config import find_game_dir
from aoe2ed.tools.ai import ai_lookup

JS = '''
var cGoal = new Command("goal","Fact","AoC");
var cUpCompareGoal = new Command("up-compare-goal","Fact","UP");
var pGoalId = new Parameter("GoalId","AoC");
var pCompareOp = new Parameter("compareOp","AoC","&#60;rel-op&#62;");
var snFoo = new StrategicNumber("sn-foo");
cGoal.shortDescription = "Checks a goal.";
cGoal.description = "Use " + cUpCompareGoal.getLink() + " for &lt; and &gt;.</p><p>Second.";
cGoal.commandParameters = [ {
	nameLink: pGoalId.getLink(),
	name: "GoalId",
	range: "1 to 16000."
} ];
pCompareOp.operatorTypes = [ {
	operator: ["c:&#60;", "&#60;", "less-than"],
	id: 0
} ];
snFoo.id = 7;
snFoo.default = 5;
snFoo.rmin = 0;
snFoo.rmax = 100;
snFoo.de = 1;
'''


def test_parse_reads_structure_and_prose_as_text():
    ref = parse(JS, descriptions=True)
    goal = ref["commands"]["goal"]
    assert goal["kind"] == "fact" and goal["version"] == "AoC"
    assert goal["parameters"] == [{"name": "GoalId", "type": "GoalId", "range": "1 to 16000."}]
    assert goal["description"] == "Use up-compare-goal for < and >.\n\nSecond."
    assert ref["parameters"]["compareOp"]["operators"] == ["c:<", "<", "less-than"]
    assert ref["strategic_numbers"]["sn-foo"] == {"id": 7, "default": 5, "min": 0, "max": 100, "de": True,
                                                  "category": "", "link": ref["strategic_numbers"]["sn-foo"]["link"],
                                                  "summary": "", "description": ""}
    assert "summary" not in parse(JS)["commands"]["goal"]        # the shipped data carries no prose


def test_shipped_reference_has_no_prose():
    ref = reference()
    assert len(ref["commands"]) > 300 and len(ref["strategic_numbers"]) > 300
    assert not any("description" in c or "summary" in c for c in ref["commands"].values())
    assert signature("up-compare-goal") == "(up-compare-goal GoalId compareOp Value)"


def _messages(script: str, severity: str) -> list[str]:
    return [d.message for d in per.check(script) if d.severity == severity]


def test_commands_only_airef_knows_are_accepted():
    v = per.vocab()
    name = next(n for n, c in v["ref_commands"].items() if c["kind"] == "action" and n not in v["actions"]
                and not c["parameters"])
    assert not _messages(f"(defrule (true) => ({name}))", "warning")


def test_fact_used_as_action_is_an_error():
    assert any("is a fact, used as a action" in m for m in _messages("(defrule (true) => (goal 1 1))", "error"))


def test_operator_parameters_must_be_operators():
    errors = _messages("(defrule (up-compare-goal 5 maybe 3) => (do-nothing))", "error")
    assert any("expects a compareOp where 'maybe'" in m for m in errors)
    assert not _messages("(defrule (up-compare-goal 5 g:>= 6) => (up-modify-goal 5 c:+ 1))", "error")


def test_goal_and_strategic_number_ranges():
    assert any("goal 20000 is out of range" in m for m in _messages("(defrule (goal 20000 1) => (do-nothing))", "error"))
    warnings = _messages("(defrule (true) => (set-strategic-number sn-percent-attack-soldiers 150))", "warning")
    assert any("outside its range 0 to 100" in m for m in warnings)


@pytest.mark.skipif(find_game_dir() is None, reason="AoE2 DE not installed")
def test_game_scripts_have_no_errors():
    game = find_game_dir()
    folders = ("resources/_common/ai", "modes/Pompeii/resources/_common/ai")
    for path in sorted(p for f in folders for p in (game / f).rglob("*.per")):
        errors = [d for d in per.check(path.read_text(encoding="utf-8", errors="replace")) if d.severity == "error"]
        assert not errors, f"{path.name}: {errors[:3]}"


def test_ai_lookup_gives_signatures_and_ranges():
    fact = ai_lookup("up-compare-goal", "facts", 1)["facts"][0]
    assert fact["signature"] == "(up-compare-goal GoalId compareOp Value)" and fact["used_by_game"]
    sn = ai_lookup("sn-percent-attack-soldiers", "strategic_numbers", 1)["strategic_numbers"][0]
    assert (sn["min"], sn["max"], sn["de"]) == (0, 100, True)
