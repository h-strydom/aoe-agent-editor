# Conditions (41)

Generated from AoE2ScenarioParser schemas. Use `effect_schema`/`condition_schema` for defaults.
Values in `[Dataset]` accept names (see enums.md, or `lookup`/`enum_values`).

- **none** (0)  
  (no params)
- **bring_object_to_area** (1)  
  `unit_object` [Unit], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `inverted`
- **bring_object_to_object** (2)  
  `unit_object` [Unit], `next_object` [Unit], `inverted`
- **own_objects** (3): True when player owns >= quantity matching objects.  
  `quantity`, `object_list` [UnitInfo], `source_player` [PlayerId], `object_group` [ObjectClass], `object_type` [ObjectType], `include_changeable_weapon_objects`
- **own_fewer_objects** (4): True when player owns <= quantity matching objects (0 = none left).  
  `quantity`, `object_list` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `include_changeable_weapon_objects`
- **objects_in_area** (5): True when >= quantity matching objects of source_player are in area.  
  `quantity`, `object_list` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `inverted`, `object_state` [ObjectState], `include_changeable_weapon_objects`
- **destroy_object** (6)  
  `unit_object` [Unit], `inverted`
- **capture_object** (7)  
  `unit_object` [Unit], `source_player` [PlayerId], `inverted`
- **accumulate_attribute** (8): True when player's resource/attribute >= quantity (inverted: <).  
  `quantity`, `attribute` [Attribute], `source_player` [PlayerId], `inverted`
- **research_technology** (9): Player researched technology.  
  `source_player` [PlayerId], `technology` [TechInfo], `inverted`
- **timer** (10): True `timer` seconds after this trigger became active.  
  `timer`, `inverted`
- **object_selected** (11)  
  `unit_object` [Unit], `inverted`
- **ai_signal** (12)  
  `ai_signal`, `inverted`
- **player_defeated** (13)  
  `source_player` [PlayerId], `inverted`
- **object_has_target** (14)  
  `unit_object` [Unit], `next_object` [Unit], `object_list` [UnitInfo], `object_group` [ObjectClass], `object_type` [ObjectType], `inverted`
- **object_visible** (15)  
  `unit_object` [Unit]
- **object_not_visible** (16)  
  `unit_object` [Unit]
- **researching_tech** (17)  
  `source_player` [PlayerId], `technology` [TechInfo], `inverted`
- **units_garrisoned** (18)  
  `quantity`, `unit_object` [Unit], `inverted`
- **difficulty_level** (19): Compare the game difficulty.  
  `quantity` [DifficultyLevel], `inverted`
- **chance** (20): True with quantity % probability each check.  
  `quantity`
- **technology_state** (21)  
  `quantity` [TechnologyState], `source_player` [PlayerId], `technology` [TechInfo], `inverted`
- **variable_value** (22): Compare a variable to quantity.  
  `quantity`, `inverted`, `variable` [VariableId], `comparison` [Comparison]
- **object_hp** (23)  
  `quantity`, `unit_object` [Unit], `inverted`, `comparison` [Comparison]
- **diplomacy_state** (24)  
  `quantity` [DiplomacyState], `source_player` [PlayerId], `inverted`, `target_player` [PlayerId]
- **script_call** (25): True when the XS function in xs_function returns true.  
  `xs_function`
- **object_selected_multiplayer** (26)  
  `unit_object` [Unit], `source_player` [PlayerId], `inverted`
- **object_visible_multiplayer** (27)  
  `unit_object` [Unit], `source_player` [PlayerId], `allow_in_fog`, `inverted`
- **object_has_action** (28)  
  `unit_object` [Unit], `next_object` [Unit], `object_list` [UnitInfo], `object_group` [ObjectClass], `object_type` [ObjectType], `inverted`, `unit_ai_action` [UnitAIAction]
- **or** (29)  
  (no params)
- **ai_signal_multiplayer** (30)  
  `ai_signal`, `inverted`
- **building_is_trading** (54)  
  `unit_object` [Unit], `inverted`
- **display_timer_triggered** (55)  
  `timer_id`, `inverted`
- **victory_timer** (56)  
  `quantity`, `source_player` [PlayerId], `inverted`, `comparison` [Comparison], `victory_timer_type` [VictoryTimerType]
- **and** (57)  
  (no params)
- **decision_triggered** (75): The player chose option 1/2 of decision_id.  
  `inverted`, `decision_id`, `decision_option` [DecisionOption]
- **object_attacked** (76)  
  `object_list` [UnitInfo], `quantity`, `source_player` [PlayerId], `object_group` [ObjectClass], `object_type` [ObjectType], `unit_object` [Unit], `inverted`
- **hero_power_cast** (77)  
  `source_player` [PlayerId]
- **compare_variables** (78)  
  `inverted`, `variable` [VariableId], `comparison` [Comparison], `variable2` [VariableId]
- **trigger_active** (79)  
  `trigger_id`, `inverted`
- **local_tech_researched** (80)  
  `local_technology` [TechInfo], `source_player` [PlayerId], `unit_object` [Unit], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `inverted`, `quantity`
