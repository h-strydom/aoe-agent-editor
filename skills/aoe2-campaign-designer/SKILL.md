---
name: aoe2-campaign-designer
description: Turn a plain-language Age of Empires II DE campaign, mission or game-mode idea into a concrete design and a buildable campaign spec. Use when someone describes a scenario/campaign/custom mode they want made ("a survival map where...", "a campaign like AoE4's Crucible", "a hero RPG mission", "a tower defense"), before building anything with the aoe2-editor tools.
---

# AoE2 campaign designer

You turn an idea into (1) a short design the person agrees to and (2) a `campaign.yaml` that
`compile_campaign` builds. Building, testing and iterating follow in the `aoe2-builder` and
`aoe2-playtest` skills.

## 1. Understand the idea (ask, don't assume)
Ask at most 3–4 questions, and only ones whose answers change the build. Offer defaults:
- **Structure:** one scenario or a campaign? How many missions? Is there a hub or a metaprogression loop?
- **Player fantasy:** what does the player do minute to minute (build an economy, micro a hero, defend, explore)?
- **Win/lose:** what ends each mission? How long should it take?
- **Persistence:** what carries between missions (currency, unlocks, choices, survivors)?
- **Faction:** a civ, or a custom tech tree built from triggers?

Restate the idea in 3–5 lines before designing.

## 2. Map the design onto what exists
Call `blocks_list()` and `guide("engine-facts")`. Express each mechanic as:
1. **a block**: survive, objective, lose_if_destroyed, waves (+ escalating, `chase`), anchor,
   escort, choice, random_faction, bank_load, bank_store, pad_shop, perk_effects, boon_offers, run_end,
   telemetry.
   Any block can be switched on a variable with `when:`;
2. **raw triggers** (`skills/aoe2-triggers`) when no block fits;
3. **XS** (`skills/aoe2-xs`) for loops, math, randomness or state that triggers can't express.

Known engine constraints that shape designs:
- **Persistence** happens only inside one campaign, through the bank (int values per key). Missions unlock in order; after that, any can be replayed. Replays ask "save your choices?". So hub-and-run loops work, and players must answer YES.
- **Civ** can't be changed by triggers, and a Random civ always plays as Britons inside a campaign. Build factions with `random_faction` / `faction_effects`: enable/disable units and techs, attribute modifiers, `add_train_location`, free techs and a civ name. Architecture and voices stay the scenario civ's.
- **Decisions** are popups with 2 options (`choice`). **Shops** use pads (walk a unit onto a flag) through `pad_shop`.
- **Several units from one trigger** need distinct tiles (`spawn` helper, or `count:` on spec units).
- A player with no counting objects is defeated at once. Enemies that only send waves need `anchor`.
- The game's default AI resigns when losing, so computer players get no AI script by default (they
  only do what triggers tell them). Ask for `ai: default` only for a real skirmish opponent.
- Missions whose stores must count should end in victory.

## 3. Write the design (in chat, short)
For each mission give: goal, map (size, biome, layout, named zones), players, the blocks with their key numbers, persistent keys read and written, and the end conditions. Add a key table, for example `meta_points: currency, written by hub on buy/exit and by runs at end`. Get a yes before building, or note the assumptions if the person said to just go ahead.

## 4. Write the spec
Read `guide("campaign-spec")` and start from the closest example from `examples()`: crucible
(roguelite: hub shop plus 45-minute survival run), frontier (story campaign: escort, siege with a
choice, counter-attack shaped by it) or factions (random factions kept across missions). The files
are also at `${CLAUDE_PLUGIN_ROOT}/examples/<name>/campaign.yaml`. Write the user's spec in their
project, not in the plugin folder. Conventions:
- `name:` is short snake_case and stays stable forever, because the bank is scoped by it. Name files `<name>_<n>_<slug>`.
- Use a generated `map:` with named zones for everything that blocks refer to (spawns, pads, gates, objectives).
  Missions that share a map put it in `defaults: {map: ...}`.
- Give every raw timer `{$secs: N}` so test mode scales it.
- Turn on telemetry for every mission and track the key variables.
- Write numbers for the real game. Test mode scales the time.

Then hand over to **aoe2-builder**.
