---
name: aoe2-playtest
description: Playtest generated Age of Empires II DE scenarios and campaigns and verify they behave as designed, using test-mode builds, the telemetry harness (.xsdat), the campaign bank (Player.nfp) and game logs. Use after building, when something "doesn't work in game", or before calling a campaign done.
---

# AoE2 playtest

The agent can't see the game by default. It observes through **telemetry**: XS injected by
the compiler writes state to an `.xsdat` file (resources, population, kills, military
population and tracked variables every N seconds, plus event markers when key triggers fire).
Someone has to actually play the scenario: the person, or you through desktop automation if
they have granted it. Ask them which.

## Loop
1. **Build a test version:** `compile_campaign(spec, test_mode=true, install=true)`. Timers run ×0.1.
2. **Prepare the bank** for campaign tests (optional). `bank_show("<campaign>")` shows the state. `bank_set("<campaign>", {"meta_points": 500})` jumps ahead, for example to test the shop without grinding. It needs the game to be closed, and it backs up Player.nfp.
3. **Give the player a checklist:** where to open it (Single Player → Campaigns → name, or → Scenario for a single file), what should happen and at what (scaled) times, and what to note. Remind them to answer YES to "save your choices?" when replaying a mission.
4. **Read the evidence:**
   - `telemetry_read(build_report="out/<name>/build_report.json")` gives the events with times, the final state, and variables by name.
     Inside a campaign the file is `<campaign name>.xsdat` and holds **only the latest mission played**, so read it right after each mission. A standalone scenario writes `<scenario>.xsdat`.
   - `bank_show("<campaign>")` shows what was persisted.
   - `game_log(grep="error")` shows engine-level problems. XS chat output is not in the log.
5. **Compare** the evidence with the design and the person's report. Each mismatch is a bug in the spec, a block or an assumption. Fix it in the toolkit or spec, never by hand-editing output, then rebuild.
6. **Record what you learned:** new verified engine behaviour goes into `src/aoe2ed/docs/engine-facts.md` (see `guide("engine-facts")`), with how it was verified.

## Reading telemetry
- No `.xsdat` at all: the XS didn't run (a compile error in game?). Check `xs_ok` and whether the mission started.
- Header but no samples: the game ended within the first interval, for example an instant win from a missing `anchor`.
- Event times show when objectives, waves and run ends fired. Check them against the scaled design times.
- `vars` track currency, flags and picks. `players[p].military` / `units_killed` show whether waves spawned and fought.

## Done means
Every mission is won once in test mode with the expected events, the bank values are right after a full loop (for a hub/run design: earn, spend, replay, effect applied), and a full-length build compiles cleanly.
