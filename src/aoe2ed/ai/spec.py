"""AI specs: a readable description of a computer player, compiled to an AoE2 DE / Return of Rome .per script.

Spec (YAML/JSON; every key optional):

  name: Troy                         # shown in the editor's player AI box
  gatherers: auto                    # villager split: auto (default) follows what the build order and keep list
                                     #   cost, blended with AIBuilder's 45/30/15/10; or {food, wood, gold, stone} %
  villagers: 25                      # keep training villagers up to this many (default: off)
  houses: true                       # build a house whenever housing is nearly full (default true)
  build_order:                       # worked through in order; a step is done when its count is reached
    - {build: BARRACKS}              #   count = how many in total (built or being built), default 1
    - {train: CLUBMAN, count: 5}     #   count = how many alive in total
    - {research: TOOL_AGE}           #   techs and ages
  step_timeout: 180                  # seconds before a step that can't happen is checked: skipped if it's affordable
                                     #   (so it's disabled or impossible); waited for up to 4 times while it isn't
  keep: [{train: BOWMAN, count: 10}, {build: BARRACKS}]   # after the build order: keep these topped up / rebuilt
  transports: 2                      # water maps: keep this many transport ships from the start, so attacks can
  transport_unit: LIGHT_TRANSPORT    #   cross water (the engine ferries attack groups); default per game
  attack:                            # omit or null = never attacks
    first: 600                       #   seconds into the game
    every: 240                       #   seconds between attacks
    min_group: 4                     #   idle soldiers needed before it attacks
    max_group: 12
    percent: 80                      #   share of idle soldiers that go (default 80)
    naval: false                     #   warships also attack on the same timing (default false)
  strategic_numbers: {sn-number-explore-groups: 1}     # raw engine settings (names checked)
  rules: "(defrule ...)"             # extra raw .per appended as is
  debug: false                       # announce each build step and attack in chat (for playtests)

Unit, building and tech names are the game's (RoR names for game: ror; see lookup). Scripted AIs never
resign: the engine only resigns when a script says (resign).

Attacks follow DE's AIBuilder (shipped with RoR, the designers' scenario AI): target the closest enemy, set
the share of soldiers that go, attack-now; warships separately. The setup enables DE's building system and full
response to sighted enemies, as AIBuilder does.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

TOP_KEYS = {"name", "gatherers", "villagers", "houses", "build_order", "step_timeout", "keep", "attack",
            "strategic_numbers", "rules", "transports", "transport_unit", "debug", "report"}
TRANSPORT_UNITS = {"ror": "LIGHT_TRANSPORT", "aoe2": "TRANSPORT_SHIP"}
ATTACK_KEYS = {"first", "every", "min_group", "max_group", "percent", "naval"}
STEP_KINDS = ("build", "train", "research")
STEP_GOAL, STEP_TIMER, ATTACK_TIMER, TARGET_GOAL, NAVAL_TIMER = 1, 1, 2, 2, 3
# AIBuilder's constants for (up-find-player enemy find-closest goal): the engine's stance and search ids.
ENEMY_STANCE, FIND_CLOSEST = 3, 2
# Always set, as AIBuilder's setup does: DE's building placement, answer every sighted enemy.
BASE_SNS = {"sn-enable-new-building-system": 1, "sn-percent-enemy-sighted-response": 100}
DEFAULT_GATHERERS = {"food": 45, "wood": 30, "gold": 15, "stone": 10}   # DE's AIBuilder
RESOURCES = ("food", "wood", "gold", "stone")
WAIT_GOAL, MAX_WAITS = 3, 4
ATTACKS_GOAL = 4                     # attacks launched so far (land and naval)
# report: true publishes the AI's state on AI signals, which scenario XS reads with xsGetAiSignal (scenario XS
# can't read an AI's goals: xsGetGoal is AI-only). Signal ids per player p (1-8): step 192+p, waits 200+p,
# attacks 208+p, villager split 216+4p .. 219+4p (food, wood, gold, stone). Goals 10-16 hold those ids.
STEP_SIGNAL, WAIT_SIGNAL, ATTACK_SIGNAL, SPLIT_SIGNAL = 192, 200, 208, 216
REPORT_GOALS = range(10, 17)
HOUSE_HEADROOM = 4
SETUP_CHUNK = 15                     # setup actions per rule (+ disable-self): well inside the engine's limit


class SpecError(ValueError):
    pass


@dataclass
class Names:
    """Game names used in a script -> their defconst name and id."""
    game: str
    ids: dict[str, tuple[str, int]] = field(default_factory=dict)

    def const(self, name: str, kind: str) -> str:
        key = f"{kind}:{name}"
        if key not in self.ids:
            self.ids[key] = (f"my-{kind[0]}-{name.lower().replace('_', '-')}", resolve(name, kind, self.game))
        return self.ids[key][0]


def resolve(name: str, kind: str, game: str) -> int:
    """A unit/building ("object") or tech id by name, for the game."""
    from .. import games
    if isinstance(name, int):
        return name
    key = str(name).upper().replace(" ", "_").replace("-", "_")
    if game == "ror":
        table = games.ror_data()["techs" if kind == "tech" else "objects"]
        if key in table:
            return table[key]
    else:
        from ..datasets import resolve_dataset_value
        for ds in (("TechInfo",) if kind == "tech" else ("UnitInfo", "BuildingInfo")):
            try:
                return int(resolve_dataset_value(ds, key))
            except (KeyError, ValueError):
                continue
    raise SpecError(f"unknown {kind} '{name}' for {game} (find names with lookup)")


@cache
def _costs() -> dict:
    data = resources.files("aoe2ed").joinpath("data/costs.json").read_text(encoding="utf-8")
    return json.loads(data)


def cost(kind: str, oid: int, game: str) -> dict[str, int]:
    """What an object (kind "object") or tech costs in the game: {food: .., gold: ..}; {} if free or unknown."""
    return _costs().get(game, {}).get("techs" if kind == "tech" else "objects", {}).get(str(oid), {})


def auto_gatherers(items: list[tuple[str, int, int]], game: str) -> dict[str, int]:
    """A villager split from what (kind, id, count) items cost, blended half and half with AIBuilder's split."""
    need = dict.fromkeys(RESOURCES, 0.0)
    for kind, oid, count in items:
        for res, amount in cost(kind, oid, game).items():
            need[res] += amount * max(count, 1)
    total = sum(need.values())
    share = {r: (need[r] / total if total else DEFAULT_GATHERERS[r] / 100) for r in RESOURCES}
    raw = {r: 50 * share[r] + DEFAULT_GATHERERS[r] / 2 for r in RESOURCES}
    out = {r: int(raw[r]) for r in RESOURCES}
    for r in sorted(RESOURCES, key=lambda r: raw[r] - out[r], reverse=True)[:100 - sum(out.values())]:
        out[r] += 1
    return out


def _step(step: dict) -> tuple[str, str, int]:
    kinds = [k for k in STEP_KINDS if k in step]
    if len(kinds) != 1 or set(step) - {*STEP_KINDS, "count"}:
        raise SpecError(f"a build_order step is one of {STEP_KINDS} with an optional count, got {step}")
    return kinds[0], step[kinds[0]], int(step.get("count", 1))


def _rule(facts: list[str], actions: list[str], comment: str = "") -> str:
    head = f"(defrule{f' ; {comment}' if comment else ''}\n"
    return head + "".join(f"\t{f}\n" for f in facts) + "=>\n" + "".join(f"\t{a}\n" for a in actions) + ")\n"


def _do(kind: str, const: str, count: int) -> tuple[list[str], list[str], str]:
    """(facts that it still needs doing, actions doing it, fact that it's done)."""
    if kind == "build":
        return ([f"(building-type-count-total {const} < {count})", f"(can-build {const})"],
                [f"(build {const})"], f"(building-type-count-total {const} >= {count})")
    if kind == "train":
        return ([f"(unit-type-count-total {const} < {count})", f"(can-train {const})"],
                [f"(train {const})"], f"(unit-type-count-total {const} >= {count})")
    return [f"(can-research {const})"], [f"(research {const})"], f"(research-completed {const})"


def build_script(spec: dict, game: str = "ror") -> str:
    """The .per script for an AI spec."""
    unknown = set(spec) - TOP_KEYS
    if unknown:
        raise SpecError(f"unknown AI spec keys {sorted(unknown)}; allowed {sorted(TOP_KEYS)}")
    names = Names(game)
    steps = [_step(s) for s in spec.get("build_order") or []]
    timeout = int(spec.get("step_timeout", 180))
    keep = [_step(s) for s in spec.get("keep") or []]

    def item(kind: str, name: str, count: int) -> tuple[str, int, int]:
        k = "tech" if kind == "research" else "object"
        return k, resolve(name, k, game), count

    if spec.get("gatherers", "auto") == "auto":
        demand = [item(*s) for s in steps + keep]
        if spec.get("villagers"):
            demand.append(item("train", "VILLAGER", int(spec["villagers"])))
        gatherers = auto_gatherers(demand, game)
    else:
        gatherers = {**DEFAULT_GATHERERS, **spec["gatherers"]}
    if set(gatherers) != set(DEFAULT_GATHERERS) or sum(gatherers.values()) != 100:
        raise SpecError(f"gatherers needs food, wood, gold and stone summing to 100, got {gatherers}")
    attack = spec.get("attack")
    if attack is not None and set(attack) - ATTACK_KEYS:
        raise SpecError(f"unknown attack keys {sorted(set(attack) - ATTACK_KEYS)}")

    body = []
    init = [f"(set-strategic-number sn-{k}-gatherer-percentage {v})" for k, v in gatherers.items()]
    sns = {**BASE_SNS, **(spec.get("strategic_numbers") or {})}
    init += [f"(set-strategic-number {k} {int(v)})" for k, v in sns.items()]
    if attack:
        init += [f"(set-strategic-number sn-minimum-attack-group-size {int(attack.get('min_group', 4))})",
                 f"(set-strategic-number sn-maximum-attack-group-size {int(attack.get('max_group', 12))})",
                 f"(enable-timer {ATTACK_TIMER} {int(attack.get('first', 600))})"]
        if attack.get("naval"):
            init.append(f"(enable-timer {NAVAL_TIMER} {int(attack.get('first', 600))})")
    init += ["(set-goal my-step 1)", f"(set-goal {ATTACKS_GOAL} 0)"]
    if steps and timeout:
        init.append(f"(enable-timer {STEP_TIMER} {timeout})")
    report = bool(spec.get("report"))
    if report:                                   # this player's signal ids, from my-player-number
        g = list(REPORT_GOALS)
        for goal, base in zip(g[:3], (STEP_SIGNAL, WAIT_SIGNAL, ATTACK_SIGNAL), strict=True):
            init += [f"(up-modify-goal {goal} c:= my-player-number)", f"(up-modify-goal {goal} c:+ {base})"]
        init += [f"(up-modify-goal {g[3]} c:= my-player-number)", f"(up-modify-goal {g[3]} c:* 4)",
                 f"(up-modify-goal {g[3]} c:+ {SPLIT_SIGNAL})"]
        for k in range(1, 4):
            init += [f"(up-modify-goal {g[3] + k} g:= {g[3]})", f"(up-modify-goal {g[3] + k} c:+ {k})"]
    for n, start in enumerate(range(0, len(init), SETUP_CHUNK), start=1):   # the engine limits rule length
        body.append(_rule(["(true)"], [*init[start:start + SETUP_CHUNK], "(disable-self)"], f"setup {n}"))
    if report:
        g = list(REPORT_GOALS)
        body.append(_rule(["(true)"], [
            f"(fe-set-signal g: {g[0]} g: my-step)", f"(fe-set-signal g: {g[1]} g: {WAIT_GOAL})",
            f"(fe-set-signal g: {g[2]} g: {ATTACKS_GOAL})",
            *(f"(fe-set-signal g: {g[3] + k} s: sn-{r}-gatherer-percentage)" for k, r in enumerate(RESOURCES))],
            "report state on AI signals (read by probes)"))

    debug = bool(spec.get("debug"))
    who = str(spec.get("name", "AI")).replace('"', "'")

    def say(text: str) -> list[str]:
        return [f'(chat-to-all "{who}: {text}")'] if debug else []

    restart = [f"(disable-timer {STEP_TIMER})", f"(enable-timer {STEP_TIMER} {timeout})"] if timeout else []
    advance = [*restart, f"(set-goal {WAIT_GOAL} 0)"]
    for i, (kind, name, count) in enumerate(steps, start=1):
        const = names.const(name, "tech" if kind == "research" else "object")
        todo, actions, done = _do(kind, const, count)
        label = f"step {i}: {kind} {name}" + (f" x{count}" if kind != "research" else "")
        body.append(_rule([f"(goal my-step {i})", *todo], actions, label))
        body.append(_rule([f"(goal my-step {i})", done],
                          [f"(set-goal my-step {i + 1})", *advance, *say(f"{label} done")]))
        if timeout:
            k, oid, _ = item(kind, name, count)
            afford = [f"({r}-amount >= {a})" for r, a in cost(k, oid, game).items()]
            body.append(_rule([f"(goal my-step {i})", f"(timer-triggered {STEP_TIMER})", *afford],
                              [f"(set-goal my-step {i + 1})", *advance, *say(f"{label} skipped (can't be made)")],
                              f"step {i}: affordable but still not made, so it can't be: skip it"))
    if steps and timeout:                                 # not affordable yet: wait, up to MAX_WAITS timeouts
        body.append(_rule([f"(timer-triggered {STEP_TIMER})", f"(up-compare-goal {WAIT_GOAL} < {MAX_WAITS})"],
                          [f"(up-modify-goal {WAIT_GOAL} c:+ 1)", *restart, *say("waiting for resources")],
                          "step waiting for resources"))
        body.append(_rule([f"(timer-triggered {STEP_TIMER})", f"(up-compare-goal {WAIT_GOAL} >= {MAX_WAITS})"],
                          ["(up-modify-goal my-step c:+ 1)", *advance, *say("gave up on a step")],
                          "step waited too long: skip it"))

    if spec.get("villagers"):
        v = names.const("VILLAGER", "object")
        body.append(_rule([f"(civilian-population < {int(spec['villagers'])})", f"(can-train {v})"],
                          [f"(train {v})"], "villagers"))
    if spec.get("transports"):
        tr = names.const(spec.get("transport_unit") or TRANSPORT_UNITS.get(game, "TRANSPORT_SHIP"), "object")
        body.append(_rule([f"(unit-type-count-total {tr} < {int(spec['transports'])})", f"(can-train {tr})"],
                          [f"(train {tr})"], f"transports x{int(spec['transports'])}"))
    if spec.get("houses", True):
        h = names.const("HOUSE", "object")
        body.append(_rule([f"(housing-headroom < {HOUSE_HEADROOM})", "(population-headroom > 0)", f"(can-build {h})"],
                          [f"(build {h})"], "houses"))
    for kind, name, count in keep:
        const = names.const(name, "tech" if kind == "research" else "object")
        todo, actions, _ = _do(kind, const, count)
        body.append(_rule([f"(goal my-step {len(steps) + 1})", *todo], actions, f"keep {name} x{count}"))
    if attack:
        every, percent = int(attack.get("every", 240)), int(attack.get("percent", 80))
        target = [f"(up-find-player my-enemy my-find-closest {TARGET_GOAL})",
                  f"(up-modify-sn sn-target-player-number g:= {TARGET_GOAL})"]
        body.append(_rule([f"(timer-triggered {ATTACK_TIMER})", "(players-building-count any-enemy >= 1)",
                           f"(defend-soldier-count >= {int(attack.get('min_group', 4))})"],
                          [*target, f"(set-strategic-number sn-percent-attack-soldiers {percent})",
                           "(set-strategic-number sn-percent-attack-boats 0)", "(attack-now)", f"(up-modify-goal {ATTACKS_GOAL} c:+ 1)",
                           f"(disable-timer {ATTACK_TIMER})", f"(enable-timer {ATTACK_TIMER} {every})",
                           *say("attacking")], "attack"))
        if attack.get("naval"):
            body.append(_rule([f"(timer-triggered {NAVAL_TIMER})", "(players-building-count any-enemy >= 1)",
                               "(warboat-count > 0)"],
                              [*target, f"(set-strategic-number sn-percent-attack-boats {percent})",
                               "(set-strategic-number sn-percent-attack-soldiers 0)", "(attack-now)", f"(up-modify-goal {ATTACKS_GOAL} c:+ 1)",
                               f"(disable-timer {NAVAL_TIMER})", f"(enable-timer {NAVAL_TIMER} {every})",
                               *say("naval attack")], "naval attack"))

    head = [f"; {spec.get('name', 'AI')}: generated by aoe-agent-editor from an AI spec ({game})",
            f"(defconst my-step {STEP_GOAL})", f"(defconst my-enemy {ENEMY_STANCE})",
            f"(defconst my-find-closest {FIND_CLOSEST})"]
    head += [f"(defconst {c} {i})" for c, i in names.ids.values()]
    extra = spec.get("rules") or ""
    return "\n".join(head) + "\n\n" + "\n".join(body) + (f"\n{extra.strip()}\n" if extra else "")
