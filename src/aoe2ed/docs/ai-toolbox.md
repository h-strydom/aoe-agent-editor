# AI toolbox: scenario AIs from skills (design)

Status: design, 2026-11-12. Nothing here is built yet. It replaces neither `ai-spec.md` (today's spec compiler) nor
the standard AI option; it is the plan for the next layer.

## Why

Scenario AIs come in two kinds today:
- **The standard skirmish AI**, at a chosen difficulty. It plays well, but it's tuned for skirmishes. On Hard and
  Hardest it sends its whole army (`attack-percent 100`) and fights to win, not to play a role.
- **A spec** compiled to rules (build order, keep list, attack timing). It's flexible, but every mission reinvents
  its AI. Defense and army-only AIs work badly. Example: RoR-RI's A Wonder of the World Canaanites have no
  villagers. They throw their whole army at you early, have nothing left to rebuild with, and never defend.

Playtests (RoR-RI, 2026-11-12) found AIs that were too strong next to AIs that did nothing.

The goal: describe a computer player in a few words and get a working AI built from proven blocks, then tweak only
what the mission needs. For example: "a town on a water map, light fishing, defends itself, light offense, wants
2000 food, medium difficulty".

## What the research found

Sources, read 2026-11-12:
- **airef.github.io**, the maintained AI reference: commands, strategic numbers, DE and UserPatch notes, a bug list
  and RoR constants. It was updated 2026-11-04. Its pages load by JavaScript, so read `js/commands.js` in the repo
  github.com/airef/airef.github.io.
- **RoR's own scripts**, `modes/Pompeii/resources/_common/ai/`: `default/`, the skirmish AI, and `AiBuilder_p/`,
  the developers' scenario AI builder.
- **sn0wsh00's guides for scenario authors** on forums.ageofempires.com: /t/205476 (three ways to attack), /t/205241
  (goals) and /t/210881 (simple campaign AIs).
- **The HD-era official AI**, gist.github.com/Andygmb/1e3a6d9d444b2dfa8c40: named goals, retreat modes and difficulty
  tables.

Facts that shape the design:
1. **DE scales a scenario AI's strategic numbers by difficulty** unless the script sets
   `sn-do-not-scale-for-difficulty-level 1` first (airef):
   - Hard ×0.8, Moderate ×0.6, Easy ×0.4, Easiest ×0.2;
   - it applies to attack groups, boat attack groups and enemy-sighted response.

   Our generated scripts don't set it. Every skill sets it in setup and does its own difficulty scaling.
2. **AiBuilder_p is a parametric scenario AI that RoR's developers built.** Every knob is a constant per phase (1-5),
   with unit and villager caps per difficulty, and a trigger's AI signal moves it to the next phase. It's the closest
   existing thing to this toolbox, and every mechanism in it is proven in RoR. It also has bugs:
   - Hardest and Extreme get the easy caps (by its preprocessor logic; untested);
   - `phaseN-outpost-cap` overwrites the dock cap.
3. **Mechanisms the shipped scripts prove in RoR:**
   - waves: `attack-now` on a timer, with `sn-percent-attack-soldiers` keeping a home guard (AiBuilder
     militaryBehavior 66-89);
   - retreat: `up-retreat-now`, plus `up-reset-attack-now`;
   - town response: `town-under-attack`, `up-get-threat-data`, `defend-soldier-count`, `up-enemy-units-in-town`;
   - gathering: `up-gather-inside`, and gather points via `up-target-point`;
   - farms: `idle-farm-count`;
   - stance: `set-stance`;
   - the free age register: SN 88;
   - strategic numbers such as `sn-maximum-town-size`, `sn-enemy-sighted-response-distance`,
     `sn-gather-idle-soldiers-at-center` and `sn-allow-civilian-defense`.
4. **Strategic numbers no shipped RoR script uses**, so they're unproven in RoR: `sn-number-defend-groups`,
   `sn-minimum/maximum-attack-group-size` and `sn-number-boat-attack-groups`. airef marks the defend-group sizes as
   AoE1-only. Today's spec compiler leans on these, which may be why its AIs don't defend.
5. **RoR unit lines reuse AoE2 line ids** (airef):
   - -287 fishing boats, -285 warships, -284 catapult triremes, -286 transports, -283 trade boats;
   - -266 clubman/axeman, -294 swordsmen, -298 improved bowmen, -295 cavalry, -291 chariots, -290 hoplites,
     -288 stone throwers.

   Caps written per line catch every upgrade. Load-if symbols: `DE-GAME-ROME`, `DE-SOLID-FARMS` and the
   `POMPEII*-MAP` names.

## The design

Three layers:
- **profile** (what a mission says)
- **skills** (blocks with settings)
- **rules** (generated `.per`)

### Profiles: what a mission says

```yaml
ai: {profile: town, pop: default, army: {core: AXEMAN, support: BOWMAN, raiders: SCOUT}, upgrades: economy,
     water: light, defense: home, offense: light, goal: {stockpile: {food: 2000}}}
```

A profile names the player's kind. Each kind is a preset of skills, and every other key overrides one skill. Kinds:

| Kind | For | Skills on by default |
|---|---|---|
| `town` | a player with villagers or a Town Center that should grow and fight | economy, build, defense, offense |
| `army` | soldiers with no economy (Wonder's Canaanites, Trojan defenders) | hold, defense, offense with reinforcements |
| `guard` | a fortified outpost or camp that only defends (River Outpost's Nubians) | hold, defense |
| `raiders` | small parties that strike and come back (Trade's Libyan ships) | raids, retreat |
| `ally` | a friendly town that should look alive and help when you're attacked | economy, build, defense, assist |
| `standard` | RoR's skirmish AI, with constant overrides (below) | none of ours |

### Skills: the blocks

Every skill takes `light / normal / heavy` or numbers, and scales by difficulty through one table of goals (goal per
difficulty, as sn0wsh00 does). Nothing is cheated unless a skill says so.

| Skill | What it does | Settings | Mechanism (proven in) |
|---|---|---|---|
| **base** (always) | sane setup: no difficulty scaling by the engine, airef's essential SNs, new building system | none | `sn-do-not-scale-for-difficulty-level 1` (airef), AiBuilder setup 1068-1121 |
| **population** | grows toward a target over the game: villagers first, the army's share rising with time | `pop: default` (by difficulty, below) or numbers, `grow: minutes` | today's `grow` stages |
| **economy** | villagers to a share of the population, a gatherer split that follows what the plan spends, rebalancing | `villagers`, `split` | today's spec compiler (works) |
| **army** | the composition: a core line, support lines and raiders, by age, plus counters to what it sees of yours | `core`, `support`, `raiders`, `counters: auto` | keep list per line (`-266` clubman/axeman and the other line ids); counters from `players-unit-type-count` on your lines (default units.per) |
| **upgrades** | which research it favours: economy first (gathering, farming), military first (armour, attack, unit upgrades) or balanced, gated by army size and resources | `economy`, `military`, `balanced` | AiBuilder technologies.per upgrade groups gated by villager counts |
| **trade** | when a resource it needs runs low: Market trades (buy and sell), and on water maps Trade Boats and Merchant Ships to an ally's or neutral's Dock | `market`, `boats: N`, `none` | today's `trade` (Market), AiBuilder economy 43-56 (trade carts and boats only if an ally or neutral has a Market or Dock) |
| **farming** | keeps farming: another farm when every farm is worked | `farms` cap | `idle-farm-count` (default buildings 814-1000) |
| **water** | fishing boats and warships, capped | `light` (≤3 boats, ≤2 warships), `normal`, `heavy`, numbers | per-line caps `-287`/`-285`, AiBuilder `fishing-cap` |
| **build** | production buildings, towers, ages, techs | `age`, `techs: light/all` | today's build order and keep list |
| **defense** | answers attacks at home: soldiers within the town radius respond, villagers flee or garrison, a home guard always stays | `home` (30% stays), `radius` | `sn-percent-attack-soldiers`, `sn-enemy-sighted-response-distance`, `sn-gather-idle-soldiers-at-center`, `town-under-attack` (default orb 220-290) |
| **offense** | waves: first at, every, minimum army, share sent, growing with the game | `light` (first 15 min, every 6 min, 50% sent), `normal`, `heavy`, numbers | `attack-now` + timer + `sn-percent-attack-soldiers` (AiBuilder militaryBehavior 66-78) |
| **retreat** | pulls a losing wave home to regroup | `when: outnumbered` | `up-reset-attack-now` + `up-retreat-now` (airef) |
| **hold** | an army without a town stays at its post and defends it | `area` | gather point via `up-target-point action-gather`, small `sn-maximum-town-size` |
| **reinforce** | an army without a town gets new soldiers so it can keep attacking | `every`, `units` | a scenario trigger (create units at its post), or `up-cc-add-resource` on a timer (AiBuilder economy 58-67) |
| **raids** | small parties hit villagers or boats and come back | `units`, `every`, `target` | today's raids |
| **goal** | plays for the mission's own goal: stockpile a resource (hold it above spending), reach an age, keep a unit safe | `stockpile: {food: 2000}` | escrow (`set-escrow-percentage`) plus spend gates (`food-amount > N` on trains) |
| **phases** | changes skills when the scenario says so: a trigger's AI signal moves to the next phase | `phases: [...]` | AiBuilder phaseUpdate (`event-detected trigger N`) |
| **provoked** | neutral until attacked | already built (v0.18.2) | `set-stance`, `set-signal` |

**Difficulty.** Missions are written as Moderate. One table scales skills for Standard and Hard, as `levels: auto`
does today, and that table replaces the engine's own scaling.

**Population targets** (the user, 2026-11-12) are the default for every kind that builds: **Standard about 50,
Moderate about 100, Hard 150 or more**. The army grows toward the target over the game, so early pressure stays
light and later waves are bigger. A mission states its own numbers where the role calls for it (an outpost, a small
raiding camp). When a resource runs out on the map, the **trade** skill keeps the army growing: Market trades on
land, and on water maps Trade Boats to an ally's or neutral's Dock. Many water missions will need this.

**The `standard` kind.** It keeps RoR's skirmish AI for towns that should simply play well. It adds per-mission
overrides of its difficulty constants (`attack-percent`, `min-attack-time`, `max-vills`, `max-pop`,
`additional-military-cap`), so an enemy can send half its army instead of all of it. It can also take rules
appended after the game's own, as `provoked` already does. Fishing caps and stockpiles can't be steered reliably
this way. The game's rules reset their goals every pass, so those need our own kinds.

### How it's built

Each skill is a function: `(settings, level) -> rules and setup`, in `aoe2ed/ai/skills/`.

- Profiles expand into an AI spec. The spec compiler stays the single place that writes `.per`.
- Each skill names the shipped script it's modelled on, and stays unverified until a probe confirms it.
- `reimagined probe` / `aoe2ed.ai.probe` run a mission with an AI and record what it does. Each skill gets a probe
  check: waves sent, units home, boats at or under the cap, food over the goal.

## Build order (proposed)

1. **base + population + army + offense + defense + retreat.** These fix the worst cases: the one-rush army, the AI that never defends,
   and the AI that sends everything. Use them for the `town` and `army` kinds.
2. **water + farming + goal + upgrades + trade.** These give Farming's "light fishing, wants its food" and the naval maps.
3. **hold + reinforce + guard and raiders kinds.** These cover the army-only and outpost missions.
4. **phases + ally.** For missions whose AI should change mid-game, such as Trade's Canaanites turning hostile.
5. **standard overrides** (`attack-percent` and similar), for towns where the skirmish AI is fine but too strong.
