# Editor coverage

Every panel of the AoE2 DE scenario editor and how an agent does the same thing. **Tool** means a
dedicated MCP/CLI tool. **Block** means a building block in a campaign spec. **Python** means
`run_python` with the full AoE2ScenarioParser API. **UI** means desktop automation (`aoe2-editor-ui` skill).

| Editor area | Control | Agent path |
|---|---|---|
| Map | Map size | Tool `map_resize`; spec `map.size` |
| | Generate from random map script | UI (the generator runs in game), then the file tools |
| | Procedural map (no RMS) | Tool `map_generate`; spec `map:` |
| | Color mood / lighting | Python `scenario.map_manager.map_color_mood`; trigger `change_color_mood` |
| Terrain | Paint terrain / layered terrain | Tool `map_set_terrain` (with `layer`) |
| | Elevation brush | Tool `map_set_elevation` (smooth or raw) |
| | Cliffs | `units_add` with cliff objects; mapgen `cliffs` (experimental) |
| | Copy / paste a region | Python (copy tiles and units between scenarios) |
| Players | Civilization, architecture, color, age, resources, pop cap, human/AI, lock civ | Tool `player_set` |
| | Active player count | Python `player_manager.active_players`; spec `map.players` / `extra_players` |
| | Player names | Trigger `change_player_name`; Python `players[n].tribe_name` |
| | AI script / personality | Tool `player_set` (`ai_type`, `personality`); Python `set_custom_ai` |
| | Disabled units / techs / buildings | Tool `player_set` (`disabled_*`) |
| | Starting camera | Tool `player_set` (`initial_player_view_x/y`) |
| Diplomacy | Ally / neutral / enemy, team locks | Tool `diplomacy_set`, `options_set` (`lock_teams`, ...) |
| Units | Place / move / rotate / delete / change owner / garrison | Tools `units_add`, `unit_update`, `units_remove` |
| | Captions (names over units) | `units_add` `caption`; trigger `change_object_caption` |
| | Bulk filters (by player, area, type) | Tool `units_list` / `units_remove` filters |
| Messages | Instructions, hints, victory, loss, history, scouts | Tool `messages_set` |
| Cinematics | Intro / victory / loss videos | Python (`message_manager` / `sections`) |
| | In-game camera moves | Trigger `change_view` |
| Triggers | Create / edit / delete / reorder / copy | Tools `triggers_add`, `trigger_update`, `triggers_remove`, `triggers_reorder`, `triggers_copy` |
| | All 103 effects / 41 conditions | `triggers_add` with any type; `effect_schema` / `condition_schema` |
| | Objectives panel | Trigger fields `display_as_objective`, `description`, ...; block `objective` |
| | Variables | Tools `variables_list`, `variable_add`, `variable_rename` |
| Victory | Standard / conquest / score / time / custom | Tool `options_set` (`victory_condition`, ...) |
| Options | Lock teams, random start, villager force drop, ... | Tool `options_set` |
| | Global victory / secondary game modes | Tool `options_set` (`secondary_game_modes`) |
| XS | Script file / embedded script | Tools `xs_set_script_name`, `xs_embed`; spec `xs:` |
| | Check script | Tool `xs_check` (xs-check, offline) |
| Test | Editor Test button | UI; normally a test-mode build plus a playtest (`aoe2-playtest`) |
| Return of Rome | RoR scenarios and campaigns, RoR units/techs/civs | `game: ror` in a spec; `scenario_new(game="ror")`; `lookup(..., game="ror")` |
| Campaigns | Campaign editor (add, order, name) | Tools `campaign_build`, `campaign_read`, `campaign_extract`; spec `missions:` |
| AI scripts | Player AI: custom .per, None AI, immobile | Tools `ai_build`, `ai_set`, `ai_check`, `ai_lookup`; `player_set ai: {name, spec}`; guide `ai-spec` |
| Campaign screens | Map background, mission icons/flags, intro slideshows (no editor UI; JSON in a mod) | Tools `campaign_screens`, `campaign_install_mod`; spec `screen:`; `aoe2ed.screens.build_layout` |
| | Persistent values between missions | Blocks `bank_load` / `bank_store`; tools `bank_show` / `bank_set` |

Gaps worth tooling later: tile and unit copy/paste between maps, trigger-area visualisation in
previews (partly done: `show_trigger_areas`), and AI scripts (`.ai`/`.per` files are not edited yet).
