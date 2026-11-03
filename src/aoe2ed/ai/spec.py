"""AI specs: a readable description of a computer player, compiled to an AoE2 DE / Return of Rome .per script.

Spec (YAML/JSON; every key optional):

  name: Troy                         # shown in the editor's player AI box
  gatherers: {food: 45, wood: 35, gold: 15, stone: 5}   # villager split, percent (sums to 100)
  villagers: 25                      # keep training villagers up to this many (default: off)
  houses: true                       # build a house whenever housing is nearly full (default true)
  build_order:                       # worked through in order; a step is done when its count is reached
    - {build: BARRACKS}              #   count = how many in total (built or being built), default 1
    - {train: CLUBMAN, count: 5}     #   count = how many alive in total
    - {research: TOOL_AGE}           #   techs and ages
  step_timeout: 180                  # seconds before a stuck step (can't afford, disabled) is skipped; 0 = never
  keep: [{train: BOWMAN, count: 10}] # after the build order: keep these topped up
  attack:                            # omit or null = never attacks
    first: 600                       #   seconds into the game
    every: 240                       #   seconds between attacks
    min_group: 4                     #   soldiers needed before it attacks
    max_group: 12
  strategic_numbers: {sn-number-explore-groups: 1}     # raw engine settings (names checked)
  rules: "(defrule ...)"             # extra raw .per appended as is

Unit, building and tech names are the game's (RoR names for game: ror; see lookup). Scripted AIs never
resign: the engine only resigns when a script says (resign).
"""
from __future__ import annotations

from dataclasses import dataclass, field

TOP_KEYS = {"name", "gatherers", "villagers", "houses", "build_order", "step_timeout", "keep", "attack",
            "strategic_numbers", "rules"}
ATTACK_KEYS = {"first", "every", "min_group", "max_group"}
STEP_KINDS = ("build", "train", "research")
STEP_GOAL, STEP_TIMER, ATTACK_TIMER = 1, 1, 2
DEFAULT_GATHERERS = {"food": 50, "wood": 30, "gold": 15, "stone": 5}
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
    gatherers = {**DEFAULT_GATHERERS, **(spec.get("gatherers") or {})}
    if set(gatherers) != set(DEFAULT_GATHERERS) or sum(gatherers.values()) != 100:
        raise SpecError(f"gatherers needs food, wood, gold and stone summing to 100, got {gatherers}")
    attack = spec.get("attack")
    if attack is not None and set(attack) - ATTACK_KEYS:
        raise SpecError(f"unknown attack keys {sorted(set(attack) - ATTACK_KEYS)}")

    body = []
    init = [f"(set-strategic-number sn-{k}-gatherer-percentage {v})" for k, v in gatherers.items()]
    init += [f"(set-strategic-number {k} {int(v)})" for k, v in (spec.get("strategic_numbers") or {}).items()]
    if attack:
        init += [f"(set-strategic-number sn-minimum-attack-group-size {int(attack.get('min_group', 4))})",
                 f"(set-strategic-number sn-maximum-attack-group-size {int(attack.get('max_group', 12))})",
                 f"(enable-timer {ATTACK_TIMER} {int(attack.get('first', 600))})"]
    init += ["(set-goal my-step 1)"]
    if steps and timeout:
        init.append(f"(enable-timer {STEP_TIMER} {timeout})")
    for n, start in enumerate(range(0, len(init), SETUP_CHUNK), start=1):   # the engine limits rule length
        body.append(_rule(["(true)"], [*init[start:start + SETUP_CHUNK], "(disable-self)"], f"setup {n}"))

    restart = [f"(disable-timer {STEP_TIMER})", f"(enable-timer {STEP_TIMER} {timeout})"] if timeout else []
    for i, (kind, name, count) in enumerate(steps, start=1):
        const = names.const(name, "tech" if kind == "research" else "object")
        todo, actions, done = _do(kind, const, count)
        label = f"step {i}: {kind} {name}" + (f" x{count}" if kind != "research" else "")
        body.append(_rule([f"(goal my-step {i})", *todo], actions, label))
        body.append(_rule([f"(goal my-step {i})", done], [f"(set-goal my-step {i + 1})", *restart]))
        if timeout:
            body.append(_rule([f"(goal my-step {i})", f"(timer-triggered {STEP_TIMER})"],
                              [f"(set-goal my-step {i + 1})", *restart], f"step {i} stuck: skip it"))

    if spec.get("villagers"):
        v = names.const("VILLAGER", "object")
        body.append(_rule([f"(civilian-population < {int(spec['villagers'])})", f"(can-train {v})"],
                          [f"(train {v})"], "villagers"))
    if spec.get("houses", True):
        h = names.const("HOUSE", "object")
        body.append(_rule([f"(housing-headroom < {HOUSE_HEADROOM})", "(population-headroom > 0)", f"(can-build {h})"],
                          [f"(build {h})"], "houses"))
    for item in spec.get("keep") or []:
        kind, name, count = _step(item)
        const = names.const(name, "tech" if kind == "research" else "object")
        todo, actions, _ = _do(kind, const, count)
        body.append(_rule([f"(goal my-step {len(steps) + 1})", *todo], actions, f"keep {name} x{count}"))
    if attack:
        body.append(_rule([f"(timer-triggered {ATTACK_TIMER})",
                           f"(military-population >= {int(attack.get('min_group', 4))})"],
                          ["(attack-now)", f"(disable-timer {ATTACK_TIMER})",
                           f"(enable-timer {ATTACK_TIMER} {int(attack.get('every', 240))})"], "attack"))

    head = [f"; {spec.get('name', 'AI')}: generated by aoe-agent-editor from an AI spec ({game})",
            f"(defconst my-step {STEP_GOAL})"]
    head += [f"(defconst {c} {i})" for c, i in names.ids.values()]
    extra = spec.get("rules") or ""
    return "\n".join(head) + "\n\n" + "\n".join(body) + (f"\n{extra.strip()}\n" if extra else "")
