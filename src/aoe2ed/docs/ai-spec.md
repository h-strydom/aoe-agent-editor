# AI specs (computer players)

A computer player's behaviour comes from an AI script (`.per`) embedded in the scenario. aoe2ed writes
the script from a readable **AI spec**, checks it, and embeds it:

- `ai_build(spec, game)`: the script for a spec, with its check
- `ai_set(handle, player, spec | .per path | script text | "none" | "immobile" | "default")`: embed it
- `ai_check(script)`: check a hand-written script
- `ai_lookup("attack", "strategic_numbers")`: search the script language: what the game's own scripts use plus
  the AI Scripting Encyclopedia ([airef.github.io](https://airef.github.io)): command signatures, the version
  that added each (AoC, UP and DE commands all work in DE and RoR), strategic number ranges and defaults, and a
  link to airef's page; `describe=True` on an exact name adds airef's description
- in campaign specs and `player_set`: `ai: {name: Raiders, spec: {...}}`

## Spec

```yaml
name: Raiders                       # shown in the editor's player AI box
gatherers: auto                     # villager split: auto (default) follows what the build order and keep list
                                    # cost (data/costs.json, from the game data), blended with AIBuilder's
                                    # 45/30/15/10; or {food: 45, wood: 35, gold: 15, stone: 5} in percent
villagers: 25                       # keep training villagers up to this many (default: off)
houses: true                        # build a house when housing is nearly full (default: true)
build_order:                        # done in order; a step is done once its count is reached
  - {build: BARRACKS}               # count: how many in total, built or being built (default 1)
  - {train: CLUBMAN, count: 5}      # count: how many alive in total
  - {research: TOOL_AGE}            # techs and ages
window: 3                           # steps worked on at once, from the current one (default 3; 1 = strictly one
                                    # at a time, which trains one unit at a time behind everything else)
step_timeout: 180                   # seconds before a stalled step is checked. A train step moves on (its count is
                                    # living units, which attacks keep killing; the keep list tops the army up).
                                    # Build and research steps are skipped if affordable (so disabled or
                                    # impossible), else waited for, up to 4 times. 0 = never skip
keep: [{train: BOWMAN, count: 10}, {build: BARRACKS}]   # keep these topped up / rebuilt
                                    # lifetime: true = count is all it ever makes (never replaced: no farming
                                    # its fishing boats); when: {soldiers: 8} = only while 8 soldiers stand at
                                    # home (upgrades once a defence stands)
keep_from: start                    # start (default) or end: only once the build order is done
rebalance: true                     # every minute, move 5% of villagers to a resource the plan spends that's running
                                    # out (under 200), from the biggest pile over 400; a share stops at 5%; default true
transports: 2                       # water maps: keep this many transport ships from the start (needs a dock)
transport_unit: LIGHT_TRANSPORT     # default: LIGHT_TRANSPORT (ror), TRANSPORT_SHIP (aoe2)
scout: auto                         # an exploring ship, so attacks across water find a target: auto (with naval
                                    # attacks or transports), false, or a unit name (SCOUT_SHIP ror, GALLEY aoe2)
levels: auto                        # follow the game's difficulty: auto scales this spec (played as normal) to an
                                    # easy and a hard version; or {easy: {...}, normal: {...}, hard: {...}} to
                                    # override keys per level (a level left out plays as normal)
army: {civ: GREEK, share: 50}       # lean the keep list's soldiers toward the civ's bonus units (see below)
start: {trigger: 1}                 # do nothing until the scenario's AI Script Goal effect sends 1 (blocks
                                    # start_ai, claim_base); timers such as attack.first count from then
grow: {to: 200, minutes: 60}        # macro toward a population over time (see Growing below)
attack:                             # leave out to never attack
  first: 600                        # seconds into the game
  every: 240                        # seconds between attacks
  min_group: 4                      # soldiers it needs before it goes
  max_group: 12
raids:                              # small parties at the closest enemy units, apart from attacks (see Raids)
  - {units: [BOWMAN, SLINGER], count: 5, first: 300, every: 150, target: villagers}
  - {units: [SLINGER, AXEMAN], count: 3, min: 1, start: {trigger: 7}, near: {x: 47, y: 20, radius: 5}}
strategic_numbers: {sn-number-explore-groups: 1}     # raw engine settings
rules: "(defrule ...)"              # extra raw .per, appended
```

## Raids

A raid takes up to `count` of its `units` (in the order listed; only those within `radius` of `near`, if given),
and sends them at the closest object of the `target` kind (`villagers`, `buildings`, `any`) the AI knows of
belonging to the closest enemy; with none of that kind known, at anything. It goes at `first` seconds (then every
`every`), or when the scenario's AI Script Goal effect sends `start.trigger`, and only with at least `min` units
(default `count`). The party's ids are kept, and its orders renewed every `resend` seconds (default 10) while
any of it lives: sent once, the engine's own tasking takes such units back (a trigger-ordered landing party
"moved left a bit and gave up", RoR-RI playtest 2026-11-08). Timers 10-14 launch raids and 20-24 renew orders;
goals 20-34 track them, 41-46 hold search state and a point, 50-99 keep's lifetime counts, 100-299 party ids.
Unverified in game.

Names are the game's own: RoR names for `game: ror` (`lookup("bowman", game="ror")`). Build orders run as a
step counter (goal 1). Timer 1 skips stuck steps, timers 2-3 time land and naval attacks, and timer 4 times
rebalancing, timer 5 the growth stages. Goals 3-4 count waits and attacks, goal 5 holds the difficulty level, goal 6
whether the AI has started, goal 7 the growth stage, and goals 10-16 hold the probe report's signal ids. Extra `rules`
can read `(goal my-step N)` but should use other goal and timer numbers.

## Difficulty levels

The game's difficulty picks the level: Easiest and Standard play easy, Moderate plays normal, and Hard, Hardest and
Extreme play hard. Campaigns only offer Standard, Moderate and Hard, one per level; scenarios and skirmishes offer
all six, and the extra three fold into the nearest level. *Verified in the Trojan War probes, 2026-11-05: Standard
attacked first at about 6:00 (easy), Hard at 1:15.* The script holds one copy of its rules per level, and its first rules test
`(difficulty == moderate)` and so on, as the game's own scripts do, and set goal 5 to 1-3. Every other rule checks
goal 5. `levels: auto` makes the easy and hard versions from the spec:

| | easy | hard |
|---|---|---|
| villagers | x0.7 | x1.3 |
| first attack | x2.5 | x0.6 |
| time between attacks | x4 (rarely attacks) | x0.4, at least 20 s (constant pressure) |
| attack group sizes | x0.5 | x1.5 |
| soldiers in the keep list | x0.6 | x1.5 |
| `grow` minutes | x3 (very slow) | x0.5 |

No level cheats: the AI gathers and pays for everything it makes, sees only what it explores, and gets no extra
resources or spawned units. A harder AI is a bigger economy and army that attacks more often.

## Growing

`grow: {to: 200, minutes: 60}` makes the AI build up toward a population of `to` over `minutes`, in `stages`
(default 8) even steps on timer 5, the stage held in goal 7. Each stage raises the targets a step further:

- villagers, from the spec's `villagers` to `villagers` here (default 40% of `to`)
- the keep list's soldiers, in proportion, to what's left: `to` less the villagers, transports and 10 spare
- the buildings that make those soldiers, along with the army, up to 4 each
- town centers to `town_centers` (default 3: expansion) and dropsites (STORAGE_PIT and GRANARY in RoR) to 3

Houses follow by themselves (the houses rule builds while there's room under the population cap), so the
scenario's population cap must allow `to`. The engine places the buildings: dropsites by resources with the new
building system, extra town centers where it finds room (unverified in game). Nothing is free: a stage's targets
are only reached as fast as the AI can gather.

## Civilization armies

`army: {civ: GREEK}` turns half the keep list's soldiers (`share`, default 50) into the units the civ's bonuses
favour, best first (`units`, default 2), and adds the buildings that make them to the keep list. The army keeps its
size, and the build order is left alone. Only units it can reach count: by `max_age`, else the highest age its
build order researches, or `age` (its starting age). `exclude` leaves out units or buildings the scenario disables.

The favoured units come from the game's data (`aoe2ed.civs`, `data/civ_bonuses.json`, `scripts/gen_civ_bonuses.py`),
Return of Rome only so far: for example Greek Hoplites (faster, 20% cheaper), Egyptian Chariots and Chariot Archers
(+33% hit points), Hittite Stone Throwers (+50% hit points) and archers (+1 attack), Shang Cavalry (fire faster).

## Starting later

With `start: {trigger: N}`, every rule waits for goal 6, which turns on when the scenario's **AI Script Goal** effect
sends N (`(event-detected trigger N)` in the script). That effect reaches every computer player, so AIs that should
start at different moments need different numbers. Blocks: `start_ai(signal, conditions)` sends it when its
conditions hold; `claim_base(area, signal)` sends it when the player's units reach their base.

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
