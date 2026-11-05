# AI behaviour: how computer players fail, and how to find out why

What we know about computer players in AoE2 DE and Return of Rome, written down as we learn it. Every entry
says how it was found. When a probe or playtest shows something new, add it here, and add a check for it in
`aoe2ed/ai/checks.py` if it can be detected from a spec or a probe.

## Investigating an AI

1. **Lint the spec** (`ai_lint(spec, game, have=[...])`). This catches what's visible without playing: a unit
   whose building the AI never builds, a later-age building look, an attack with no army, naval attacks with no
   ships. `have` lists what the scenario already gives the player (Troy starts with its buildings).
2. **Probe it**: `ai_probe(handle, out, specs={player: spec}, stop_after=900)`.
   - It writes a copy of the scenario that records what every player has every 15 game seconds:
     - stockpile, everything gathered so far, population and the room left under its cap;
     - villagers, military, kills, villager idle time;
     - a count of everything the AI builds or trains, plus the buildings those come from, and the research
       state of every tech it researches;
     - for players running an AI spec, what the AI itself reports: the build-order step it's on, how often it
       has waited for resources there, the attacks it has launched, and its live villager split.
       - The probe re-embeds each spec AI with `report: true`. The AI publishes those values on AI signals with
         `fe-set-signal`: step 192+p, waits 200+p, attacks 208+p, split 216+4p to 219+4p.
       - The probe's XS reads them back with `xsGetAiSignal`.
   - It stops itself after `stop_after` game seconds. There's no need to play to the end: 10-15 game minutes shows
     whether an AI builds, trains and attacks.
   - Start the copy in game: Skirmish, Game Mode: Scenario. Leave player 1 alone; an idle player 1 is also
     the cleanest test of whether enemies attack.
   - With the `DEBUGSPEEDS` launch option, press + up to 8x: 15 game minutes take about 2 real minutes.
3. **Read the report**: `ai_probe_report(manifest)`. You get a summary per player at the last sample, plus
   findings from every check below. Each finding gives the time, what was seen and what usually fixes it.
   A report taken before the stop time shows what has happened so far.
4. **Look closer when needed**:
   - Build the AI with `debug: true`: it announces each build step and attack in chat.
   - `aoe2ed.ai.probe.timeline(record, player, stat)` gives any stat, or an object's count, over time.

## Checks

| Check | Kind | What it means |
|---|---|---|
| `made_where` | lint | A unit or tech is made at a building the AI never builds, and the scenario doesn't give it. |
| `age_variant` | lint | `build` names a later-age look (ACADEMY_AGE3); villagers can only build the Age1 base. |
| `attack_without_army` | lint | `attack` is set but nothing in the build order or keep list is a soldier. |
| `naval_without_ships` | lint | `attack.naval` with no dock and no transports. |
| `no_builders` | probe | Never had a villager: the build order can't run. This is info, since army-only players are normal. |
| `stuck_step` | probe | The AI's own step goal shows where its plan stopped: the step, since when, waits, and whether it was affordable. The report's summary lists every step change. |
| `first_engagement` | probe | First kill against the first attack time; a warning when it's 5+ minutes late. |
| `never_made` | probe | Something in the build order or keep list never existed, not even under construction. |
| `stalled_build_order` | probe | The first step never completed (research counts once done), and whether it was affordable at the end. |
| `hoarding` | probe | 600+ of a resource unspent for 3+ minutes: there's nothing the AI can spend it on. |
| `villagers` | probe | Under 60% of the spec's villagers after 8 minutes. |
| `housed` | probe | No room under the population cap for 2+ minutes. |
| `no_income` | probe | A resource the plan needs wasn't gathered at all after 5 minutes. |
| `no_attack` | probe | An attack was due, but the AI has no kills 3 minutes later. |
| `idle_villagers` | probe | More than a quarter of villager time idle near the end. |

## What we know

### Scripts and the engine
- **Rule length:** a rule with more than 16 facts, or more than 32 facts and actions together, fails to load
  with "ERR6002: Rule too long". The game's own scripts never go past that.
  *Found in the Trojan War playtest, 2026-11-02. The checker reports it, and specs split their setup rules.*
- **Argument counts:** a command written with the wrong number of arguments, such as `(goal 3 < 4)`, loads as
  "ERR2011: Missing closing parenthesis". The checker knows the argument counts the game's own scripts use;
  airef gives the rest. *Trojan War playtest, 2026-11-03.*

### Buildings and units (Return of Rome)
- **Age looks:** buildings exist once per age look; for example, the Academy is 103/105/18/19 for Ages 1-4.
  An AI told to build 18 never builds an Academy, so it never trains hoplites. Build the Age1 base; `unit_info`
  shows `variant_of` and `age_looks`. *Trojan War playtest, 2026-11-03 (lint `age_variant`).*
- **Town Center:** the Town Center is 109. Its "Age1" entry, 621, is the foundation the engine places.

### Economy
- **Too few villagers:** an AI with about 10 villagers and 1 each on gold and stone trains so slowly it stalls
  once its starting army is spent. Specs now keep 25+ villagers, and `gatherers: auto` splits them by what the
  plan costs. *Trojan War playtest, 2026-11-02 (checks `villagers`, `no_income`).*
- **Stalled steps:** a step skipped because it can't be afforded loses its unit for good. Specs now wait for
  resources, and skip a step only when it's affordable but still not made. *Same playtest.*

### Attacks
- **Attack pattern:** the AI doesn't attack just because units exist. DE's AIBuilder pattern works: target the
  closest enemy, set `sn-percent-attack-soldiers`, then `attack-now`. Without the percentage, attack-now sends
  nobody. *Trojan War playtest, 2026-11-02 (check `no_attack`).*
- **Transports:** an AI that owns transport ships ferries its attack groups across water by itself.
  *Trojan War: Troy crossed with a full ship.*
- **Default AI:** the game's default AI resigns once it judges the game lost, so don't use it for scenario
  enemies (engine-facts).

### First probe: Trojan War, 2026-11-05 (15 game minutes, player 1 idle)
- **Academy fix confirmed:** Troy built an Academy at the start and had 5 hoplites by 7-9 minutes.
- **Food-starved economy:**
  - Food stayed between 10 and 50 for the first 9 minutes while wood grew to 2,000+, gold to 1,000+ and stone
    to 700 (check `hoarding`).
  - It gathered about 200 food, 220 wood, 140 gold and 35 stone a minute at the end, from a 42/34/19/5 split.
  - Everything Troy trains costs food: villagers, cavalry, hoplites. Wood had nothing to be spent on once the
    buildings were up.
  - The split from costs alone underweights a resource that's spent continuously.
- **The build order stopped at step 28** ("train CAVALRY x10"): 5 cavalry by minute 6, never more, although it
  was affordable at the end. Nothing after that step happened: more hoplites, stone throwers, short swordsmen,
  ships. The probe can't see the AI's current step; the debug chat or a step signal would (open question).
- **Attacks across water came 11 minutes late:** first kill at 13:31, with the first attack due at 2:00. That
  was with 10-20 soldiers and 2 transports from the start (check `first_engagement`).
- **Army-only players:** the Trojan Defenders start with 24 soldiers, no villagers and no Town Center, and
  their AoE1 build list can't run (check `no_builders`). Their first attack is at 7,200 s, so they defend.
- **Villagers change unit type with their task** (lumberjack, miner...), so counting the Villager type
  undercounts. Probes count villagers with the civilian population.
- **Population headroom:** `cAttributePopulationCap` (4) is the room left under the cap; population plus it
  stays constant.

### Second probe: Trojan War with step reporting, 2026-11-05
- **The signal channel works:** values set with `fe-set-signal` reach scenario XS through
  `xsGetAiSignal(id, false)` every sample.
- **The build order isn't stuck, it's slow** (the first probe's "stalled at step 28" was wrong):
  - Troy starts with its buildings, so steps 1-13 are done by 0:15.
  - Then: step 15 (5 cavalry) 1:15-5:00, step 16 (5 hoplites) 5:00-10:31, research steps 10:31-14:16.
  - It's still on step 21 of 43 at 15:00.
  - Every train step makes one unit at a time while food sits at 0-50, so 5 hoplites take 5.5 minutes.
- **The plan runs one step at a time,** and the keep list only starts once the whole build order is done.
  Military stayed flat at 20 from 11:00, with nothing reinforcing it.
- **Attacks wait for a known enemy building:**
  - The attack rule needs `(players-building-count any-enemy >= 1)`.
  - Troy's first attack came at 14:01, right after its first scout ship (step 20). That was 12 minutes after the
    attack was due, with 10+ soldiers ready the whole time.
  - On a water map the AI learns of the enemy only once a ship explores. This is inferred from the timing.
- **Army-only players publish too:** the Trojan Defenders (step 1 forever, 0 attacks).
- **Fixes in AI specs, from this probe** (all defaults, so every spec gets them):
  - `window: 3` works on the next three steps at once;
  - `keep_from: start` runs the keep list from the beginning;
  - `rebalance: true` moves villagers from a pile to a shortage every minute;
  - `scout: auto` keeps a scout ship exploring on water maps.

### Third probe: Trojan War with the fixes, 2026-11-05 (player 1 idle)
- **Attacks arrive on time now:**
  - The attack counter starts at 6:00 and the first kill comes at 6:30, against 14:01 before. Troy had scout
    ships from the start.
  - That supports the open question below: attacks wait until the AI has seen an enemy building.
  - The converted spec attacks every 45 s with groups of 4-8, so Troy launched 21 attacks by 13:00. It killed the
    idle player 1 completely by 12:46, and the game ended there, before the probe's stop time.
- **The army grows:** military rose to 25-26 by 8:00 and stayed there through the fighting, against flat at 20
  before. The keep list now reinforces from the start.
- **The build order is slower, not faster:**
  - Step 15 (5 cavalry) lasted 2:00-11:01, and it reached step 16 at 15:00 before.
  - The keep list's soldiers, the step window and the attacks all take from the same food. Cavalry kept dying
    in attacks, and the step counts living units.
  - Techs later in the plan (Metalworking and on) never came.
- **Food is still the bottleneck, and rebalancing never moved anyone:**
  - Food stayed between 0 and 200 until 11:00. The split stayed at 42/34/19/5 the whole game.
  - The rule needs a resource above 800, but with the window, wood was spent as it came in. It stayed under 200
    until 9:00, and nothing passed 800 until 12:00, by which point food was back over 200.
  - Stone climbed to 650 with nothing to spend it on, but its 5% share is already under the 10% floor, so
    rebalancing couldn't take from it anyway.
- **Report fixes from this probe:**
  - `stalled_build_order` now ignores steps the AI says it hasn't reached. It flagged step 19 while Troy was
    on step 16.
  - The report notes when a player lost everything, which explains a record that stops early.
- **Rebalancing changed after this probe:**
  - It now reacts to a shortage: when a resource the plan spends is under 200 at the minute tick, 5% of
    villagers move to it.
  - They come from the biggest other pile, checked at over 1,600, then 800, then 400.
  - A share can drop to 5% (it was 10%).
  - Resources the plan never spends aren't fed.

### Fourth probe: Trojan War with shortage rebalancing, 2026-11-05 (player 1 idle)
- **Rebalancing works, and fired once:**
  - At 11:00 it moved 5% from wood to food (42/34/19/5 became 47/29/19/5), when wood first passed 400.
  - Before then nothing qualified. Wood and gold were spent as they came in, and stone (300-590) was already
    at the 5% floor.
- **Food isn't misallocated, it's all spent:**
  - Every resource but stone stayed low the whole game: food 0-55, wood 60-580, gold 95-205.
  - Troy turns all its income into soldiers and attacks; 25 villagers is simply its capacity. A different
    split can't fix that; more villagers or fewer units could.
  - The only waste is stone, about 600 by the end, which the 5% floor keeps from moving.
- **It's stronger than before:** first kill at 5:30, and the idle player 1 was wiped out by 9:31 (12:46 in the
  third probe). The game ended at 11:16.
- **Train steps count living units:**
  - Step 15 ("5 cavalry") never got past 4 alive, because cavalry kept dying in the 45-second attacks.
  - The step timeout skipped it at 11:01, and steps 16-17 were already done through the window.
- **Wrong scenario picked:** a leftover test scenario sorted above the probe in the Scenario list and was run
  by mistake. Keep the profile's scenario folder down to the scenario under test.

### XS: scenario scripts vs AI scripts
- **AI-only calls:** `xsGetGoal`, `xsSetGoal`, `xsGetStrategicNumber` and `xsSetStrategicNumber` act on "the
  current AI" and only exist in an AI script's XS. In a scenario's XS, the whole file fails to load with
  "'xsGetGoal' is a bad syscall - unable to parse", even after `xsSetContextPlayer`.
- **How it was found:** probe v3, 2026-11-05. xs-check accepts these calls, so `xs_check` now reports them for
  scenario code (`context="ai"` allows them), and probes check their own XS before saving.

### Testing setup
- **Speed:** the `DEBUGSPEEDS` launch option lets + raise the speed to 8.0, about 8x real time; it works in
  Return of Rome. `UNCAPPED_SIMULATION_SPEED` does nothing. Set launch options in Steam's game properties:
  launching with `steam://run/813780//ARGS/` started three copies of the game. *2026-11-04.*
- **Built-in test harness:** the game has one. With `TEST_HARNESS_COMM` and `TEST_HARNESS_ADDRESS`, it opens UDP
  port 9999, but it ignored text, JSON and binary messages and sent nothing back. Its format is unknown, so
  it's parked. *2026-11-04.*
- **Record file:** a probe's record is `<probe file name>.xsdat` in the profile's `profile/` folder; Return of
  Rome uses the same folder.

### Fifth probe: Trojan War with difficulty levels, civ army and the base revealed, 2026-11-05
Troy's spec: `levels: auto`, `army: {civ: HITTITE}`, and map revealers over player 1's town for one second.
- **A one-second reveal is enough:**
  - On Hard, the first attack launched at 1:15, as soon as hard's timer allowed (72 s). That is, Troy knew a
    target building with no scouting.
  - The AI keeps buildings it glimpsed once. The first kill came at 3:00, after the crossing.
  - Before the reveal, the first attack waited for a scout ship (14:01 in the second probe).
- **The levels show:**
  - Standard (the easy level) attacked first at about 6:00 and didn't beat the idle player 1 in 15 minutes.
  - Hard attacked from 1:15 and every 20 s after, about 30 attacks by 12:00, and won.
  - *Standard from the user's playtest; no record kept.*
- **Civ army:** Troy (Hittite) trained Bowmen (7 by 12:00, +1 attack) and kept 5 Stone Throwers (+50% hit
  points), both from its civ bonuses.
- **Same weak spot as before:**
  - Food 0-50 for 10 minutes; step 15 ("5 cavalry") never completed, because the attacks kept killing the
    cavalry, and it was too poor at each step timeout to skip it.
  - So the rest of the build order (techs, more ships) never came.
  - Train steps that count living units stall under constant attacks.
- **Large scripts load:** Troy's script with three levels has about 580 rules, and the Trojan Defenders' about
  1,500. Both ran.

## Open questions
- Is `players-building-count any-enemy` really limited to buildings the AI has seen? The timing says so;
  confirm with a probe where the AI gets an early scout ship.
- Should the share floor be 0 for a resource that piles up with nothing to spend it on, such as Troy's stone?
- Should a train step count units ever made rather than units alive? With attacks from minute 2, "5 cavalry"
  took 9 minutes because they kept dying.
- Can an AI script's `(xs-script-call "name")` call a function in the scenario's XS? If it can, AIs could log
  their own build steps into the probe record. The game's own AIs only call functions from their bundled XS
  libraries.
- Does the Scenario lobby let every slot be a computer player (`ai_probe(human="computer")`)? An idle human in
  player 1 works either way.
