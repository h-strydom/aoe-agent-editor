# AI specs (computer players)

A computer player's behaviour comes from an AI script (`.per`) embedded in the scenario. aoe2ed writes
the script from a readable **AI spec**, checks it, and embeds it:

- `ai_build(spec, game)`: the script for a spec, with its check
- `ai_set(handle, player, spec | .per path | script text | "none" | "immobile" | "default")`: embed it
- `ai_check(script)`: check a hand-written script
- `ai_lookup("attack", "strategic_numbers")`: search the script vocabulary
- in campaign specs and `player_set`: `ai: {name: Raiders, spec: {...}}`

## Spec

```yaml
name: Raiders                       # shown in the editor's player AI box
gatherers: {food: 45, wood: 35, gold: 15, stone: 5}   # villager split in percent, sums to 100 (default 50/30/15/5)
villagers: 25                       # keep training villagers up to this many (default: off)
houses: true                        # build a house when housing is nearly full (default: true)
build_order:                        # done in order; a step is done once its count is reached
  - {build: BARRACKS}               # count: how many in total, built or being built (default 1)
  - {train: CLUBMAN, count: 5}      # count: how many alive in total
  - {research: TOOL_AGE}            # techs and ages
step_timeout: 180                   # seconds before a step that can't happen (no resources, disabled) is skipped; 0 = never
keep: [{train: BOWMAN, count: 10}, {build: BARRACKS}]   # after the build order, keep these topped up / rebuilt
transports: 2                       # water maps: keep this many transport ships from the start (needs a dock)
transport_unit: LIGHT_TRANSPORT     # default: LIGHT_TRANSPORT (ror), TRANSPORT_SHIP (aoe2)
attack:                             # leave out to never attack
  first: 600                        # seconds into the game
  every: 240                        # seconds between attacks
  min_group: 4                      # soldiers it needs before it goes
  max_group: 12
strategic_numbers: {sn-number-explore-groups: 1}     # raw engine settings
rules: "(defrule ...)"              # extra raw .per, appended
```

Names are the game's own: RoR names for `game: ror` (`lookup("bowman", game="ror")`). Build orders run as a
step counter (goal 1), with timer 1 skipping stuck steps and timer 2 timing attacks; extra `rules` can read
`(goal my-step N)` but should use other goal and timer numbers.

## The checker

Bracket and rule-shape mistakes, and rules longer than the engine allows (16 facts, 32 facts and actions), are errors, which `ai_set` refuses. Facts, actions, strategic numbers and names
that the game's own scripts never use are warnings: the vocabulary is extracted from the 87 `.per` files
shipped with AoE2 DE and Return of Rome (`scripts/gen_ai_vocab.py`), and every one of those files checks
clean. A warning isn't always wrong, but nothing proves the engine accepts it.

## Behaviour

- Scripted AIs never resign; only `(resign)` in a script does that. The game's standard AI ("default") does
  resign when it judges the game lost, so use a spec, "none" or "immobile" for scenario enemies.
- Attacks across water: `attack-now` sends attack groups, and the engine ferries them in the AI's transport ships, as
  RoR's own AI relies on (it only checks that it owns transports). So water maps need `transports`; without
  ships an AI can't reach an enemy on another island. *Unverified in game for generated scripts.*
- "none": no script, the player does nothing on its own (trigger-driven enemies). "immobile": units hold position.
- Return of Rome runs the same script engine; its own AIs give RoR units by id with `defconst`, which is
  what generated scripts do.
