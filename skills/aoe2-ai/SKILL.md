---
name: aoe2-ai
description: Give Age of Empires II DE and Return of Rome computer players a scripted AI, from a readable spec (build order, economy, attack timing, strategic numbers) compiled to a checked .per script embedded in the scenario. Use when a scenario's enemies or allies should build, train, research or attack on their own, or when a .per script needs writing or checking.
---

# AoE2 AI scripts

Computer players run AI scripts (`.per`). aoe2ed writes them from an **AI spec**, checks them against the
vocabulary of the game's own scripts, and embeds them in the scenario, so nothing has to be installed.

## Workflow
1. Decide the player's job: build up and attack, defend in place, or stay passive and let triggers drive it.
   - Trigger-driven or decorative: `ai_set(handle, p, "none")`. Units that must hold position: `"immobile"`.
   - Avoid `"default"` (the game's standard AI) for scenario enemies: it resigns when it judges the game lost.
2. Write a spec (`guide("ai-spec")`): `build_order` of `{build|train|research: NAME, count}` steps, `villagers`,
   `gatherers`, `attack: {first, every, min_group, max_group}`, raw `strategic_numbers`.
   Names are the game's: for Return of Rome use RoR names (`lookup("clubman", game="ror")`).
3. `ai_build(spec, game)` and read `problems`: errors must be fixed; warnings name things the game's own
   scripts never use (`ai_lookup` finds the right name). For raw `rules`, `ai_lookup(name, describe=True)` gives a
   command's signature, parameter types and airef's description; the checker flags wrong operators,
   argument counts, facts used as actions, out-of-range goals and strategic numbers DE ignores.
4. `ai_set(handle, player, spec)` embeds it (or `ai: {name, spec}` under the player in a campaign spec).
5. Playtest: does it build in order, attack when expected? Adjust `step_timeout` if steps stall.

## When an AI misbehaves
Don't guess: measure. `guide("ai-behaviour")` has the full method and everything learned so far.
1. `ai_lint(spec, game, have=[what the scenario gives the player])`.
2. `ai_probe(handle, out, specs={player: spec}, stop_after=900)`: a copy that records every player's economy,
   army and buildings, and stops itself. Ask the user to start it (Skirmish > Scenario, + to 8x with
   DEBUGSPEEDS) and leave player 1 idle. 15 game minutes take about 2 real minutes.
3. `ai_probe_report(manifest)`: findings per player (stalled step, never built, hoarding, no attack...).
   Fix the spec, probe again.
4. New failure mode? Tell the user, so it gets added to the ai-behaviour guide and, if detectable, a check.

## Hand-written scripts
`ai_check(script_or_path)` checks any `.per`. Generated scripts use goal 1 and timers 1-2; extra `rules` should
use other numbers.
