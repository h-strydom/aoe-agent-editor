# Effects (103)

Generated from AoE2ScenarioParser schemas. Use `effect_schema`/`condition_schema` for defaults.
Values in `[Dataset]` accept names (see enums.md, or `lookup`/`enum_values`).

- **none** (0)  
  (no params)
- **change_diplomacy** (1)  
  `diplomacy` [DiplomacyState], `source_player` [PlayerId], `target_player` [PlayerId], `mutual_diplomacy`
- **research_technology** (2)  
  `source_player` [PlayerId], `technology` [TechInfo], `force_research_technology`
- **send_chat** (3): Chat message to source_player.  
  `source_player` [PlayerId], `string_id`, `message`, `sound_name`
- **play_sound** (4)  
  `source_player` [PlayerId], `location_x`, `location_y`, `location_object_reference` [Unit], `global_sound`, `sound_name`
- **tribute** (5)  
  `quantity`, `tribute_list` [Attribute], `source_player` [PlayerId], `target_player` [PlayerId]
- **unlock_gate** (6)  
  `selected_object_ids` [Unit[]]
- **lock_gate** (7)  
  `selected_object_ids` [Unit[]]
- **activate_trigger** (8): Enable another trigger (by name in aoe2ed).  
  `trigger_id` [TriggerId]
- **deactivate_trigger** (9)  
  `trigger_id` [TriggerId]
- **ai_script_goal** (10)  
  `ai_script_goal`
- **create_object** (11): Spawn one unit/building at location.  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `item_id`, `facet`, `disable_sound`
- **task_object** (12): Order units with any action_type (move, patrol, garrison, ...).  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `location_object_reference` [Unit], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `action_type` [ActionType], `selected_object_ids` [Unit[]], `disable_garrison_unload_sound`, `max_units_affected`, `issue_group_command`, `queue_action`
- **declare_victory** (13): End the scenario with victory (enabled=true) for source_player.  
  `source_player` [PlayerId], `enabled`
- **kill_object** (14)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **remove_object** (15)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `object_state` [ObjectState], `selected_object_ids` [Unit[]], `max_units_affected`
- **change_view** (16)  
  `quantity`, `source_player` [PlayerId], `location_x`, `location_y`, `scroll`
- **unload** (17)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `location_object_reference` [Unit], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **change_ownership** (18)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `target_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `flash_object`, `selected_object_ids` [Unit[]], `max_units_affected`
- **patrol** (19)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **display_instructions** (20): Show a message in the instructions panel for display_time seconds.  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `string_id`, `display_time`, `instruction_panel_position` [PanelLocation], `play_sound`, `message`, `sound_name`, `use_tag_color_for_icon`
- **clear_instructions** (21)  
  `instruction_panel_position` [PanelLocation]
- **freeze_object** (22)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **use_advanced_buttons** (23)  
  (no params)
- **damage_object** (24)  
  `quantity`, `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **place_foundation** (25)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`
- **change_object_name** (26)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `string_id`, `area_x1`, `area_y1`, `area_x2`, `area_y2`, `message`, `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_hp** (27)  
  `quantity`, `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `operation` [Operation], `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_attack** (28)  
  `armour_attack_quantity`, `armour_attack_class` [DamageClass], `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `operation` [Operation], `selected_object_ids` [Unit[]], `max_units_affected`
- **stop_object** (29)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **attack_move** (30): Order units (filter by player/area/type) to attack-move to a location.  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `location_object_reference` [Unit], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_armor** (31)  
  `armour_attack_quantity`, `armour_attack_class` [DamageClass], `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `operation` [Operation], `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_range** (32)  
  `quantity`, `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `operation` [Operation], `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_speed** (33)  
  `quantity`, `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **heal_object** (34)  
  `quantity`, `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **teleport_object** (35): Move matching units instantly to location.  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_stance** (36)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `attack_stance` [AttackStance], `selected_object_ids` [Unit[]], `max_units_affected`
- **display_timer** (37): Countdown on screen; message may contain %d. Pair with display_timer_triggered.  
  `string_id`, `display_time`, `time_unit` [TimeUnit], `timer`, `reset_timer`, `message`
- **enable_disable_object** (38)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `enabled`, `item_id`
- **enable_disable_technology** (39)  
  `source_player` [PlayerId], `technology` [TechInfo], `enabled`, `item_id`
- **change_object_cost** (40)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `resource_1` [Attribute], `resource_1_quantity`, `resource_2` [Attribute], `resource_2_quantity`, `resource_3` [Attribute], `resource_3_quantity`
- **set_player_visibility** (41)  
  `source_player` [PlayerId], `target_player` [PlayerId], `visibility_state` [VisibilityState]
- **change_object_icon** (42)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `object_list_unit_id_2` [UnitInfo], `selected_object_ids` [Unit[]], `max_units_affected`
- **replace_object** (43)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `target_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `object_list_unit_id_2` [UnitInfo], `facet2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_description** (44)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `string_id`, `message`
- **change_player_name** (45)  
  `source_player` [PlayerId], `string_id`, `message`
- **change_train_location** (46)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `object_list_unit_id_2` [UnitInfo], `button_location` [ButtonLocation]
- **change_technology_location** (47)  
  `source_player` [PlayerId], `technology` [TechInfo], `object_list_unit_id_2` [UnitInfo], `button_location` [ButtonLocation]
- **change_civilization_name** (48)  
  `source_player` [PlayerId], `string_id`, `message`
- **create_garrisoned_object** (49)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_list_unit_id_2` [UnitInfo], `selected_object_ids` [Unit[]], `max_units_affected`, `disable_sound`
- **acknowledge_ai_signal** (50)  
  `ai_signal_value`
- **modify_attribute** (51): Change a unit type's stat. Integer stats take whole numbers only.  
  `quantity`, `armour_attack_quantity`, `armour_attack_class` [DamageClass], `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `item_id`, `operation` [Operation], `object_attributes` [ObjectAttribute], `message`
- **modify_resource** (52): Set/Add/Subtract a player's resource (tribute_list = Attribute).  
  `quantity`, `tribute_list` [Attribute], `source_player` [PlayerId], `item_id`, `operation` [Operation]
- **modify_resource_by_variable** (53): Resource <- variable.  
  `tribute_list` [Attribute], `source_player` [PlayerId], `item_id`, `operation` [Operation], `variable` [VariableId]
- **set_building_gather_point** (54)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **script_call** (55): Runs the XS function defined in `message`, e.g. 'void f() { ... }'.  
  `string_id`, `message`
- **change_variable** (56): Set/Add/Subtract/Multiply/Divide a trigger variable.  
  `quantity`, `operation` [Operation], `variable` [VariableId], `message`
- **clear_timer** (57)  
  `timer`
- **change_object_player_color** (58)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `player_color` [PlayerColorId], `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_civilization_name** (59)  
  `source_player` [PlayerId], `string_id`, `area_x1`, `area_y1`, `area_x2`, `area_y2`, `message`, `selected_object_ids` [Unit[]], `max_units_affected`
- **change_object_player_name** (60)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `string_id`, `area_x1`, `area_y1`, `area_x2`, `area_y2`, `message`, `selected_object_ids` [Unit[]], `max_units_affected`
- **disable_unit_targeting** (61)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **enable_unit_targeting** (62)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **change_technology_cost** (63)  
  `source_player` [PlayerId], `technology` [TechInfo], `resource_1` [Attribute], `resource_1_quantity`, `resource_2` [Attribute], `resource_2_quantity`, `resource_3` [Attribute], `resource_3_quantity`
- **change_technology_research_time** (64)  
  `quantity`, `source_player` [PlayerId], `technology` [TechInfo]
- **change_technology_name** (65)  
  `source_player` [PlayerId], `technology` [TechInfo], `string_id`, `message`
- **change_technology_description** (66)  
  `source_player` [PlayerId], `technology` [TechInfo], `string_id`, `message`
- **enable_technology_stacking** (67)  
  `quantity`, `source_player` [PlayerId], `technology` [TechInfo]
- **disable_technology_stacking** (68)  
  `source_player` [PlayerId], `technology` [TechInfo]
- **acknowledge_multiplayer_ai_signal** (69)  
  `ai_signal_value`
- **disable_object_selection** (70)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **enable_object_selection** (71)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **change_color_mood** (72)  
  `quantity`, `color_mood` [ColorMood]
- **enable_object_deletion** (73)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `item_id`, `selected_object_ids` [Unit[]], `max_units_affected`
- **disable_object_deletion** (74)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `item_id`, `selected_object_ids` [Unit[]], `max_units_affected`
- **train_unit** (75)  
  `quantity`, `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **initiate_research** (76)  
  `source_player` [PlayerId], `technology` [TechInfo], `selected_object_ids` [Unit[]]
- **create_object_attack** (77)  
  `armour_attack_quantity`, `armour_attack_class` [DamageClass], `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `operation` [Operation], `selected_object_ids` [Unit[]], `max_units_affected`
- **create_object_armor** (78)  
  `armour_attack_quantity`, `armour_attack_class` [DamageClass], `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `operation` [Operation], `selected_object_ids` [Unit[]], `max_units_affected`
- **modify_attribute_by_variable** (79)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `operation` [Operation], `object_attributes` [ObjectAttribute], `variable` [VariableId], `message`, `armour_attack_class` [DamageClass]
- **set_object_cost** (80)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `quantity`, `tribute_list` [Attribute]
- **load_key_value** (81): Campaign bank: load key `message` into variable; quantity is the default.  
  `variable` [VariableId], `message`, `quantity`
- **store_key_value** (82): Campaign bank: store variable under key `message` (campaign-scoped, persists).  
  `variable` [VariableId], `message`
- **delete_key** (83): Campaign bank: delete key `message`.  
  `message`
- **change_technology_icon** (84)  
  `technology` [TechInfo], `source_player` [PlayerId], `quantity`
- **change_technology_hotkey** (85)  
  `technology` [TechInfo], `source_player` [PlayerId], `quantity`
- **modify_variable_by_resource** (86): Variable <- resource.  
  `tribute_list` [Attribute], `source_player` [PlayerId], `operation` [Operation], `variable` [VariableId]
- **modify_variable_by_attribute** (87)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `operation` [Operation], `object_attributes` [ObjectAttribute], `variable` [VariableId], `message`, `armour_attack_class` [DamageClass]
- **change_object_caption** (88)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `string_id`, `message`, `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]]
- **change_player_color** (89)  
  `source_player` [PlayerId], `player_color` [PlayerColorId]
- **create_decision** (90): Two-option popup; pair with the decision_triggered condition.  
  `decision_id`, `string_id`, `message`, `string_id_option1`, `message_option1`, `string_id_option2`, `message_option2`
- **disable_unit_attackable** (98)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **enable_unit_attackable** (99)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `selected_object_ids` [Unit[]], `max_units_affected`
- **modify_variable_by_variable** (100): variable (op)= variable2.  
  `variable` [VariableId], `operation` [Operation], `variable2` [VariableId]
- **count_units_into_variable** (101): Count matching units into variable2.  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_group` [ObjectClass], `variable2` [VariableId]
- **add_train_location** (102)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `object_list_unit_id_2` [UnitInfo], `button_location` [ButtonLocation], `train_time`, `hotkey`
- **research_local_technology** (103)  
  `local_technology` [TechInfo], `source_player` [PlayerId], `selected_object_ids` [Unit[]], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `object_list_unit_id_2` [UnitInfo]
- **modify_attribute_for_class** (104): Change a stat for a whole class (object_group2) / type (object_type2).  
  `object_group2` [ObjectClass], `object_type2` [ObjectType], `source_player` [PlayerId], `object_attributes` [ObjectAttribute], `message`, `operation` [Operation], `quantity`, `armour_attack_quantity`, `armour_attack_class` [DamageClass]
- **modify_object_attribute** (105)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `object_attributes` [ObjectAttribute], `selected_object_ids` [Unit[]], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `operation` [Operation], `message`, `quantity`, `armour_attack_quantity`, `armour_attack_class` [DamageClass], `object_filter` [ObjectModifyAttributeState]
- **modify_object_attribute_by_variable** (106)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `object_attributes` [ObjectAttribute], `selected_object_ids` [Unit[]], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `operation` [Operation], `message`, `variable` [VariableId], `armour_attack_class` [DamageClass]
- **change_object_visibility** (107)  
  `source_player` [PlayerId], `target_player` [PlayerId], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `visibility_state` [VisibilityState], `max_units_affected`, `selected_object_ids` [Unit[]]
- **build_object** (108)  
  `object_list_unit_id` [UnitInfo], `source_player` [PlayerId], `location_x`, `location_y`, `location_object_reference` [Unit], `area_x1`, `area_y1`, `area_x2`, `area_y2`, `wall_x1`, `wall_y1`, `wall_x2`, `wall_y2`, `object_group` [ObjectClass], `object_type` [ObjectType], `building_list` [BuildingInfo], `selected_object_ids` [Unit[]], `disable_garrison_unload_sound`, `max_units_affected`, `issue_group_command`, `queue_action`
- **mirror_diplomacy** (109)  
  `source_player` [PlayerId], `target_player` [PlayerId], `enabled`
