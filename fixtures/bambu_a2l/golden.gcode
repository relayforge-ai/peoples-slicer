; HEADER_BLOCK_START
; BambuStudio 02.07.01.62
; model printing time: 2d 20h 17m 43s; total estimated time: 2d 20h 24m 36s
; total layer number: 404
; total filament length [mm] : 64829.85,94700.85,67326.94,68063.57
; total filament volume [cm^3] : 155934.06,227782.24,161940.27,163712.08
; total filament weight [g] : 193.36,282.45,200.81,203.00
; model label id: 704,763,822,881,940,999,1058,1117,1176,1235,1258
; object max height: 8.80,25.20,25.20,25.20,25.20,25.20,25.20,25.20,25.20,76.20,80.80
; filament_density: 1.24,1.24,1.24,1.24
; filament_diameter: 1.75,1.75,1.75,1.75
; max_z_height: 80.80
; filament: 1,2,3,4
; HEADER_BLOCK_END

; CONFIG_BLOCK_START
; accel_to_decel_enable = 0
; accel_to_decel_factor = 50%
; activate_air_filtration = 0,0,0,0
; additional_cooling_fan_speed = 70,70,70,70
; additional_fan_full_speed_layer = 0,0,0,0
; alternate_extra_wall = 0
; apply_scarf_seam_on_circles = 1
; auxiliary_fan = 0
; avoid_crossing_wall_includes_support = 0
; bed_custom_model = 
; bed_custom_texture = 
; bed_exclude_area = 
; bed_temperature_formula = by_first_filament
; before_layer_change_gcode = 
; best_object_pos = 0.5,0.5
; bottom_color_penetration_layers = 3
; bottom_shell_layers = 3
; bottom_shell_thickness = 0
; bottom_surface_density = 100%
; bottom_surface_pattern = concentric
; bridge_angle = 0
; bridge_flow = 1
; bridge_no_support = 0
; bridge_speed = 50
; brim_object_gap = 0.25
; brim_type = outer_only
; brim_width = 5
; chamber_temperatures = 0,0,0,0
; change_filament_gcode = ;======== A2L filament_change gcode ==========\n;===== 2026/05/26 =====\n\nM620 S[next_filament_id]A\nM204 S9000\n{if toolchange_count > 1 && (z_hop_types[current_filament_id] == 0 || z_hop_types[current_filament_id] == 3)}\nG17\nG2 Z{z_after_toolchange + 0.4} I0.86 J0.86 P1 F10000 ; spiral lift a little from second lift\n{endif}\n\n;nozzle_change_gcode\n\nG1 Z{max_layer_z + 3.0} F1200\n\nM400\nM106 P1 S0\n\n{if toolchange_count == 2}\n; get travel path for change filament\n;M620.1 X[travel_point_1_x] Y[travel_point_1_y] F21000 P0\n;M620.1 X[travel_point_2_x] Y[travel_point_2_y] F21000 P1\n;M620.1 X[travel_point_3_x] Y[travel_point_3_y] F21000 P2\n{endif}\n\n{if ((filament_type[current_filament_id] == \"PLA\") || (filament_type[current_filament_id] == \"PLA-CF\") || (filament_type[current_filament_id] == \"PETG\") || (filament_type[current_filament_id] == \"PETG-CF\")) && (nozzle_diameter_at_nozzle_id[current_nozzle_id] == 0.2)}\nM620.10 A0 F74.8347 L[flush_length] H{nozzle_diameter_at_nozzle_id[current_nozzle_id]} T{flush_temperatures[current_filament_id]} P[old_filament_temp] S1\n{else}\nM620.10 A0 F{flush_volumetric_speeds[current_filament_id]/2.4053*60} L[flush_length] H{nozzle_diameter_at_nozzle_id[current_nozzle_id]} T{flush_temperatures[current_filament_id]} P[old_filament_temp] S1\n{endif}\n\n{if ((filament_type[next_filament_id] == \"PLA\") || (filament_type[next_filament_id] == \"PLA-CF\") || (filament_type[next_filament_id] == \"PETG\") || (filament_type[next_filament_id] == \"PETG-CF\")) && (nozzle_diameter_at_nozzle_id[next_nozzle_id] == 0.2)}\nM620.10 A1 F74.8347 L[flush_length] H{nozzle_diameter_at_nozzle_id[next_nozzle_id]} T{flush_temperatures[next_filament_id]} P[new_filament_temp] S1\n{else}\nM620.10 A1 F{flush_volumetric_speeds[next_filament_id]/2.4053*60} L[flush_length] H{nozzle_diameter_at_nozzle_id[next_nozzle_id]} T{flush_temperatures[next_filament_id]} P[new_filament_temp] S1\n{endif}\n\n{if long_retraction_when_cut}\nM620.11 P1 L0 I[current_filament_id] E-{retraction_distance_when_cut} F{max((flush_volumetric_speeds[current_filament_id]/2.4053*60), 200)}\n{else}\nM620.11 P0 L0 I[current_filament_id] E0\n{endif}\n\nM620.11 K0 I[current_filament_id] R0\n\n\nT[next_filament_id]\n\n;deretract\n{if filament_type[next_filament_id] == \"TPU\"}\n{else}\n;VG1 E4 F{max(new_filament_e_feedrate, 200)}\n;VG1 E4 F{max(new_filament_e_feedrate/2, 100)}\n{endif}\n\n\n; VFLUSH_START\n\n{if flush_length>41.5}\n;VG1 E41.5 F{min(old_filament_e_feedrate,new_filament_e_feedrate)}\n;VG1 E{flush_length-41.5} F{new_filament_e_feedrate}\n{else}\n;VG1 E{flush_length} F{min(old_filament_e_feedrate,new_filament_e_feedrate)}\n{endif}\n\nSYNC T{ceil(flush_length / 80) * 7.5 + 6.5}\n\n; compensate for heating and cooling\n{if flush_length > 0}\n{if flush_temperatures[next_filament_id] > new_filament_temp}\nSYNC T{(flush_temperatures[next_filament_id]-(new_filament_temp - filament_cooling_before_tower[next_filament_id]))/hotend_cooling_rate[filament_map[next_filament_id]-1]}\nSYNC T{(flush_temperatures[next_filament_id]-(new_filament_temp - filament_cooling_before_tower[next_filament_id]))/hotend_heating_rate[filament_map[next_filament_id]-1]}\n{else}\nSYNC T{(new_filament_temp - filament_cooling_before_tower[next_filament_id] -flush_temperatures[next_filament_id])/hotend_cooling_rate[filament_map[next_filament_id]-1]}\nSYNC T{(new_filament_temp - filament_cooling_before_tower[next_filament_id] -flush_temperatures[next_filament_id])/hotend_heating_rate[filament_map[next_filament_id]-1]}\n{endif}\n{endif}\n\n; VFLUSH_END\n\n\n\nM1002 set_filament_type:{filament_type[next_filament_id]}\n\nM400\nM83\n{if next_filament_id < 255}\nM620.10 R{retract_length_toolchange[filament_map[next_filament_id]-1]}\nM628 S0\n;VM109 S[new_filament_temp]\nM629\nM400\nM983.3 F{filament_max_volumetric_speed[next_filament_id]/2.4} A0.4 R{retract_length_toolchange[filament_map[next_filament_id]-1]}\nM400\n\nG1 Z{max_layer_z + 3.0} F3000\n{if layer_z <= (initial_layer_print_height + 0.001)}\nM204 S[initial_layer_acceleration]\n{else}\nM204 S[travel_acceleration]\n{endif}\n\n{else}\nG1 X[x_after_toolchange] Y[y_after_toolchange] Z[z_after_toolchange] F12000\n{endif}\n\nM621 S[next_filament_id]A\n\nM622.1 S0 ;for prev version, default skip\nM1002 judge_flag powerloss_resume_flag\nM622 J1\nM983.3 F{filament_max_volumetric_speed[next_filament_id]/2.4} A0.4 R{retract_length_toolchange[filament_map[next_filament_id]-1]}\nM400\nG1 Z{max_layer_z + 3.0} F3000\n{if layer_z <= (initial_layer_print_height + 0.001)}\nM204 S[initial_layer_acceleration]\n{else}\nM204 S[travel_acceleration]\n{endif}\nM1002 set_flag powerloss_resume_flag=0\nM623\n\n{if (filament_type[next_filament_id] == \"TPU\")}\nM1015.3 S1 H{nozzle_diameter_at_nozzle_id[next_nozzle_id]};enable tpu clog detect\n{else}\nM1015.3 S0;disable tpu clog detect\n{endif}\n\n{if (filament_type[next_filament_id] == \"PLA\") ||  (filament_type[next_filament_id] == \"PETG\")\n ||  (filament_type[next_filament_id] == \"PLA-CF\")  ||  (filament_type[next_filament_id] == \"PETG-CF\")}\nM1015.4 S1 K1 H{nozzle_diameter_at_nozzle_id[next_nozzle_id]} ;enable E air printing detect\n{else}\nM1015.4 S0 K0 H{nozzle_diameter_at_nozzle_id[next_nozzle_id]} ;disable E air printing detect\n{endif}\n\n{if ((filament_type[next_filament_id] == \"PETG\") || (filament_type[next_filament_id] == \"PETG-CF\") || (filament_type[next_filament_id] == \"TPU\") || (filament_type[next_filament_id] == \"TPU-AMS\"))}\n  G390.7 M6 G4 C3\n{else}\n  G390.7 M6 G6 C3\n{endif}\n\nM620.6 I[next_filament_id] W1 ;enable ams air printing detect\n\n;Set the filament gear warning temperature\n{if (temperature_vitrification[next_filament_id] <= 50)}\n    {if ((filament_ids[next_filament_id]==\"GFA05\") || (filament_ids[next_filament_id]==\"GFA06\"))}\n        M142 P1 O45; set PLASILK gear warning temperature when filament change\n    {else}\n        M142 P1 O60; set PLA/PLACF/PLAAERO/PVA/TPU gear warning temperature when filament change\n    {endif}\n{else}\n    M142 P1 O100 ; set gear warning temperature when filament change\n{endif}\n
; circle_compensation_manual_offset = 0
; circle_compensation_speed = 200,200,200,200
; close_additional_fan_first_x_layers = 1,1,1,1
; close_fan_the_first_x_layers = 1,1,1,1
; complete_print_exhaust_fan_speed = 70,70,70,70
; cool_plate_temp = 35,35,35,35
; cool_plate_temp_initial_layer = 35,35,35,35
; cooling_filter_enabled = 0
; cooling_perimeter_transition_distance = 10,10,10,10
; cooling_slowdown_logic = uniform_cooling,uniform_cooling,uniform_cooling,uniform_cooling
; counter_coef_1 = 0,0,0,0
; counter_coef_2 = 0.008,0.008,0.008,0.008
; counter_coef_3 = -0.041,-0.041,-0.041,-0.041
; counter_limit_max = 0.033,0.033,0.033,0.033
; counter_limit_min = -0.035,-0.035,-0.035,-0.035
; curr_bed_type = Textured PEI Plate
; default_acceleration = 6000
; default_filament_colour = ;;;
; default_filament_profile = "Bambu PLA Basic @BBL A2L 0.4 nozzle"
; default_jerk = 0
; default_nozzle_volume_type = Standard
; default_print_profile = 0.20mm Standard @BBL A2L
; deretraction_speed = 30
; detect_floating_vertical_shell = 1
; detect_narrow_internal_solid_infill = 1
; detect_overhang_wall = 1
; detect_thin_wall = 0
; diameter_limit = 50,50,50,50
; different_settings_to_system = bottom_surface_pattern;brim_object_gap;brim_type;outer_wall_speed;skeleton_infill_density;skin_infill_density;sparse_infill_density;sparse_infill_pattern;top_surface_pattern;wall_loops;;;;;
; draft_shield = disabled
; during_print_exhaust_fan_speed = 70,70,70,70
; elefant_foot_compensation = 0.075
; embedding_wall_into_infill = 0
; enable_arc_fitting = 0
; enable_circle_compensation = 0
; enable_filament_dynamic_map = 0
; enable_height_slowdown = 1
; enable_long_retraction_when_cut = 2
; enable_mixed_color_sublayer = 0
; enable_order_independent_overlap_carving = 0
; enable_overhang_bridge_fan = 1,1,1,1
; enable_overhang_speed = 1
; enable_pre_heating = 0
; enable_pressure_advance = 0,0,0,0
; enable_prime_tower = 1
; enable_support = 0
; enable_support_ironing = 0
; enable_tower_interface_features = 0
; enable_wrapping_detection = 0
; enforce_support_layers = 0
; eng_plate_temp = 55,55,55,55
; eng_plate_temp_initial_layer = 55,55,55,55
; ensure_vertical_shell_thickness = enabled
; exclude_object = 1
; extruder_ams_count = 1#0|4#0;1#0|4#0
; extruder_clearance_dist_to_rod = 56.5
; extruder_clearance_height_to_lid = 325
; extruder_clearance_height_to_rod = 25
; extruder_clearance_max_radius = 73
; extruder_colour = #018001
; extruder_max_nozzle_count = 1
; extruder_nozzle_stats = Standard#1
; extruder_offset = 0x0
; extruder_printable_area = 
; extruder_type = Direct Drive
; extruder_variant_list = "Direct Drive Standard"
; fan_cooling_layer_time = 80,80,80,80
; fan_direction = undefine
; fan_max_speed = 80,80,80,80
; fan_min_speed = 60,60,60,60
; filament_adaptive_volumetric_speed = 0,0,0,0
; filament_adhesiveness_category = 100,100,100,100
; filament_bridge_speed = 25,25,25,25
; filament_change_length = 10,10,10,10
; filament_change_length_nc = 10,10,10,10
; filament_colour = #000000;#FFFFFF;#FFFF00;#D3B7A7
; filament_colour_type = 1;1;1;0
; filament_cooling_before_tower = 0,0,0,0
; filament_cost = 20,20,20,20
; filament_density = 1.24,1.24,1.24,1.24
; filament_dev_ams_drying_ams_limitations = 1;0;1;0;1;0;1;0
; filament_dev_ams_drying_heat_distortion_temperature = 45,45,45,45
; filament_dev_ams_drying_temperature = 45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45
; filament_dev_ams_drying_time = 12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12
; filament_dev_chamber_drying_bed_temperature = 70,70,70,70
; filament_dev_chamber_drying_time = 12,12,12,12
; filament_dev_drying_cooling_temperature = 45,45,45,45
; filament_dev_drying_softening_temperature = 50,50,50,50
; filament_diameter = 1.75,1.75,1.75,1.75
; filament_enable_overhang_speed = 1,1,1,1
; filament_end_gcode = "; filament end gcode \n\n";"; filament end gcode \n\n";"; filament end gcode \n\n";"; filament end gcode \n\n"
; filament_extruder_compatibility = 0,0,0,0
; filament_extruder_variant = "Direct Drive Standard";"Direct Drive Standard";"Direct Drive Standard";"Direct Drive Standard"
; filament_flow_ratio = 0.98,0.98,0.98,0.98
; filament_flush_temp = 0,0,0,0
; filament_flush_temp_fast = 220,220,220,220
; filament_flush_volumetric_speed = 0,0,0,0
; filament_ids = GFL99;GFL99;GFL99;GFL99
; filament_is_mixed = 0,0,0,0
; filament_is_support = 0,0,0,0
; filament_map = 1,1,1,1
; filament_map_2 = 0,0,0,0
; filament_map_mode = Auto For Flush
; filament_max_volumetric_speed = 12,12,12,12
; filament_metal_stickiness = None,None,None,None
; filament_minimal_purge_on_wipe_tower = 15,15,15,15
; filament_mixed_components = ;;;
; filament_mixed_gradient = 0,0,0,0
; filament_mixed_gradient_curve = ;;;
; filament_mixed_gradient_per_part = 0,0,0,0
; filament_mixed_gradient_range = ;;;
; filament_mixed_sublayer_ratios = ;;;
; filament_multi_colour = #000000;#FFFFFF;#FFFF00;#D3B7A7
; filament_notes = 
; filament_nozzle_map = 0,0,0,0
; filament_overhang_1_4_speed = 0,0,0,0
; filament_overhang_2_4_speed = 50,50,50,50
; filament_overhang_3_4_speed = 30,30,30,30
; filament_overhang_4_4_speed = 10,10,10,10
; filament_overhang_totally_speed = 10,10,10,10
; filament_pre_cooling_temperature = 0,0,0,0
; filament_pre_cooling_temperature_nc = 0,0,0,0
; filament_preheat_temperature_delta = 0,0,0,0
; filament_prime_volume = 45,45,45,45
; filament_prime_volume_nc = 60,60,60,60
; filament_printable = 3,3,3,3
; filament_ramming_travel_time = 0,0,0,0
; filament_ramming_travel_time_nc = 0,0,0,0
; filament_ramming_volumetric_speed = -1,-1,-1,-1
; filament_ramming_volumetric_speed_nc = -1,-1,-1,-1
; filament_retract_length_nc = 14,14,14,14
; filament_scarf_gap = 15%,15%,15%,15%
; filament_scarf_height = 10%,10%,10%,10%
; filament_scarf_length = 10,10,10,10
; filament_scarf_seam_type = none,none,none,none
; filament_self_index = 1,2,3,4
; filament_settings_id = "Generic PLA @BBL A2L";"Generic PLA @BBL A2L";"Generic PLA @BBL A2L";"Generic PLA @BBL A2L"
; filament_shrink = 100%,100%,100%,100%
; filament_soluble = 0,0,0,0
; filament_start_gcode = ;;;
; filament_tower_interface_pre_extrusion_dist = 10,10,10,10
; filament_tower_interface_pre_extrusion_length = 0,0,0,0
; filament_tower_interface_print_temp = -1,-1,-1,-1
; filament_tower_interface_purge_volume = 20,20,20,20
; filament_tower_ironing_area = 4,4,4,4
; filament_type = PLA;PLA;PLA;PLA
; filament_velocity_adaptation_factor = 1,1,1,1
; filament_vendor = Generic;Generic;Generic;Generic
; filament_volume_map = 0,0,0,0
; filename_format = {input_filename_base}_{filament_type[0]}_{print_time}.gcode
; fill_multiline = 1
; filter_out_gap_fill = 0
; first_layer_print_sequence = 0
; first_x_layer_fan_speed = 0,0,0,0
; first_x_layer_part_fan_speed = 0,0,0,0
; flush_into_infill = 0
; flush_into_objects = 0
; flush_into_support = 1
; flush_multiplier = 1
; flush_multiplier_fast = 1.2
; flush_volumes_matrix = 0,652,542,568,172,0,326,152,212,399,0,298,178,330,393,0
; flush_volumes_vector = 140,140,140,140,140,140,140,140
; full_fan_speed_layer = 0,0,0,0
; fuzzy_skin = none
; fuzzy_skin_first_layer = 0
; fuzzy_skin_mode = displacement
; fuzzy_skin_noise_type = classic
; fuzzy_skin_octaves = 4
; fuzzy_skin_persistence = 0.5
; fuzzy_skin_point_distance = 0.8
; fuzzy_skin_scale = 1
; fuzzy_skin_thickness = 0.3
; gap_infill_speed = 250
; gcode_add_line_number = 0
; gcode_flavor = marlin
; grab_length = 17.4
; group_algo_with_time = 0
; has_filament_switcher = 0
; has_scarf_joint_seam = 0
; head_wrap_detect_zone = 226x224,256x224,256x256,226x256
; hole_coef_1 = 0,0,0,0
; hole_coef_2 = -0.008,-0.008,-0.008,-0.008
; hole_coef_3 = 0.23415,0.23415,0.23415,0.23415
; hole_limit_max = 0.22,0.22,0.22,0.22
; hole_limit_min = 0.088,0.088,0.088,0.088
; host_type = octoprint
; hot_plate_temp = 55,55,55,55
; hot_plate_temp_initial_layer = 55,55,55,55
; hotend_cooling_rate = 2
; hotend_heating_rate = 2
; impact_strength_z = 10,10,10,10
; independent_support_layer_height = 0
; infill_combination = 0
; infill_direction = 45
; infill_instead_top_bottom_surfaces = 0
; infill_jerk = 9
; infill_lock_depth = 1
; infill_rotate_step = 0
; infill_shift_step = 0.4
; infill_wall_overlap = 15%
; initial_layer_acceleration = 500
; initial_layer_flow_ratio = 1
; initial_layer_infill_speed = 105
; initial_layer_jerk = 9
; initial_layer_line_width = 0.5
; initial_layer_print_height = 0.2
; initial_layer_speed = 50
; initial_layer_travel_acceleration = 6000
; inner_wall_acceleration = 0
; inner_wall_jerk = 9
; inner_wall_line_width = 0.45
; inner_wall_speed = 300
; interface_shells = 0
; interlocking_beam = 0
; interlocking_beam_layer_count = 2
; interlocking_beam_width = 0.8
; interlocking_boundary_avoidance = 2
; interlocking_depth = 2
; interlocking_orientation = 22.5
; internal_bridge_support_thickness = 0.8
; internal_solid_infill_line_width = 0.42
; internal_solid_infill_pattern = zig-zag
; internal_solid_infill_speed = 250
; ironing_direction = 45
; ironing_fan_speed = -1,-1,-1,-1
; ironing_flow = 10%
; ironing_inset = 0.21
; ironing_pattern = zig-zag
; ironing_spacing = 0.15
; ironing_speed = 30
; ironing_type = no ironing
; is_infill_first = 0
; layer_change_gcode = ;======== A2L layer_change gcode ==========\n;===== 2026/04/29 ====\n; update layer progress\nM201 N1 Y[curr_y_acceleration_limit]\nM73 L{layer_num+1}\nM991 S0 P{layer_num} ;notify layer change\nM1007 L1
; layer_height = 0.2
; line_width = 0.42
; locked_skeleton_infill_pattern = zigzag
; locked_skin_infill_pattern = crosszag
; long_retractions_when_cut = 0
; long_retractions_when_ec = 0,0,0,0
; machine_bed_mass_Y = 2700
; machine_end_gcode = ;======== A2L end gcode ==========\n;===== 2026/04/07 =====\nM400 ; wait for buffer to clear\nG92 E0 ; zero the extruder\n\n; pull back filament to AMS\nM620 S65535\nT65535\nG150.2\nM621 S65535\nG150.3\nG1 Y295 F3600\nG90\nG1 Z{max_layer_z + 0.4} F900 ; lower z a little\nM1002 judge_flag timelapse_record_flag\nM622 J1\n    M400 ; wait all motion done\n    M991 S0 P-1 ;end smooth timelapse at safe pos\n    M400 S5 ;wait for last picture to be taken\nM623  ;end of \"timelapse_record_flag\"\n\nM106 S0 ; turn off fan\nM106 P2 S0 ; turn off remote part cooling fan\nM106 P3 S0 ; turn off chamber cooling fan\nM142 P1 Q0 ; turn off extruder autocool\n\nM220 S100  ; Reset feedrate magnitude\nM204.2 K1.0 ; Reset acc magnitude\nM73.2 R1.0 ;Reset left time magnitude\n\nM1015.3 S0 ;disable clog detect\nM1015.4 S0 K0 ;disable air printing detect\n;=====printer finish sound=========\nM17\nM400 S1\nM1006 S1\nM1006 A53 B10 L30 C53 D10 M30 E53 F10 N30 \nM1006 A57 B10 L30 C57 D10 M30 E57 F10 N30 \nM1006 A0 B15 L0 C0 D15 M0 E0 F15 N0 \nM1006 A53 B10 L30 C53 D10 M30 E53 F10 N30 \nM1006 A57 B10 L30 C57 D10 M30 E57 F10 N30 \nM1006 A0 B15 L0 C0 D15 M0 E0 F15 N0 \nM1006 A48 B10 L30 C48 D10 M30 E48 F10 N30 \nM1006 A0 B15 L0 C0 D15 M0 E0 F15 N0 \nM1006 A60 B10 L30 C60 D10 M30 E60 F10 N30 \nM1006 W\n;=====printer finish sound=========\nM400\nM18\n\nM104 S0 ; turn off hotend\nM140 S0 ; turn off bed\nM1007 S0
; machine_hotend_change_time = 0
; machine_load_filament_time = 11
; machine_max_acceleration_e = 5000,5000
; machine_max_acceleration_extruding = 12000,12000
; machine_max_acceleration_retracting = 5000,5000
; machine_max_acceleration_travel = 9000,9000
; machine_max_acceleration_x = 12000,12000
; machine_max_acceleration_y = 8000,8000
; machine_max_acceleration_z = 1500,1500
; machine_max_force_Y = 29
; machine_max_jerk_e = 3,3
; machine_max_jerk_x = 9,9
; machine_max_jerk_y = 9,9
; machine_max_jerk_z = 3,3
; machine_max_printed_mass = 2000
; machine_max_speed_e = 30,30
; machine_max_speed_x = 500,500
; machine_max_speed_y = 500,500
; machine_max_speed_z = 30,30
; machine_min_extruding_rate = 0,0
; machine_min_travel_rate = 0,0
; machine_pause_gcode = M400 U1
; machine_prepare_compensation_time = 260
; machine_start_gcode = ;M1002 set_flag extrude_cali_flag=1\n;M1002 set_flag g29_before_print_flag=1\n;M1002 set_flag build_plate_detect_flag=1\n;M1002 set_flag bed_heat_stable_wait_flag=1\n\n;======== A2L start gcode==========\n;===== 2026/05/26 =====\nT1000 O0\nM1002 gcode_claim_action : 2\n{if hold_chamber_temp_for_flat_print && (bed_temperature_initial_layer_single == 55)}\n    M140 S65\n{else}\n    M140 S[bed_temperature_initial_layer_single] ; heat heatbed first\n{endif}\n\nM993 A0 B0 C0 ; nozzle cam detection not allowed.\nM400\n\n;=====printer start sound ===================\nM17\nM400 S1\nM1006 S1\nM1006 A53 B9 L30 C53 D9 M30 E53 F9 N30\nM1006 A56 B9 L30 C56 D9 M30 E56 F9 N30\nM1006 A61 B9 L30 C61 D9 M30 E61 F9 N30\nM1006 A53 B9 L30 C53 D9 M30 E53 F9 N30\nM1006 A56 B9 L30 C56 D9 M30 E56 F9 N30\nM1006 A61 B18 L30 C61 D18 M30 E61 F18 N30\nM1006 W\n;=====printer start sound ===================\n\n  M620 M ;enable remap\n  G389\n\n;===== avoid end stop =================\n  G91\n  G380 S2 Z22 F1200\n  G380 S2 Z-12 F1200\n  G90\n;===== avoid end stop =================\n\n;===== reset machine status =================\n  M204 S10000\n  M630 S0 P1\n  G90\n  M17 D ; reset motor current to default\n  M960 S5 P1 ; turn on logo lamp\n  M220 S100 ;Reset Feedrate\n  M221 S100 ;Reset Flowrate\n  M73.2   R1.0 ;Reset left time magnitude\n  G29.1 Z{+0.0} ; clear z-trim value first\n  M983.1 M1\n  M982.2 S1 ; turn on cog noise reduction\n  M983.4 S0\n;===== reset machine status =================\n;Set the filament gear warning temperature\n{if (temperature_vitrification[initial_filament_id] <= 50)}\n    {if ((filament_ids[initial_filament_id]==\"GFA05\") || (filament_ids[initial_filament_id]==\"GFA06\"))}\n        M142 P1 O45; set PLASILK gear warning temperature when start\n    {else}\n        M142 P1 O60; set PLA/PLACF/PLAAERO/PVA/TPU gear warning temperature when start\n    {endif}\n{else}\n    M142 P1 O100 ; set gear warning temperature when start\n{endif}\n;===== start to heat heatbed & hotend==========\n  M1002 set_filament_type:{filament_type[initial_no_support_filament_id]}\n  M104 S140 A\n\n  G29.2 S0 ; avoid invalid abl data\n\n;===== first homing start =====\n  M1002 gcode_claim_action : 13\n  M105\n  G28 X Z P0 T300 W\n  G150.3\n  G1 Z1.3 F1200\n  G150.1 F16000 ; wipe mouth to avoid filament stick to heatbed\n  G90\n  M400\n;===== first homing end =====\n\n\n;===== detection start =====\n;===== build_plate_detect_flag start =====\nM1002 judge_flag build_plate_detect_flag\nM622 S1\n  G91\n  G1 Z5 F1200\n  G90\n  G0 X15 F30000\n  G0 Y319 F3000\n  G91\n  G1 Z-5 F1200\n  G28 Z P0 T140\n  G1 F1200\n  G39.4\n  G90\n  G1 Z5 F1200\nM623\n;===== build_plate_detect_flag end =====\n;===== detection end =====\n\n\n;===== hotend hotbed pre-heat start =====\n  M104 S{nozzle_temperature_initial_layer[initial_no_support_filament_id]-80} A ; rise nozzle temp in advance\n\n  G90\n  G1 Y220 F3000 ; Put away the heated bed to prevent collisions\n\n  {if hold_chamber_temp_for_flat_print && (bed_temperature_initial_layer_single == 55)}\n      M190 S65\n  {else}\n      M190 S[bed_temperature_initial_layer_single]\n  {endif}\n;===== hotend hotbed pre-heat end =====\n\n\n;===== prepare print temperature and material ==========\n  M400\n  M211 X0 Y0 Z0 ;turn off soft endstop\n  M975 S1 ; turn on input shaping\n\n  G29.2 S0 ; avoid invalid abl data\n  G150.3\n{if ((filament_type[initial_no_support_filament_id] == \"PLA\") || (filament_type[initial_no_support_filament_id] == \"PLA-CF\") || (filament_type[initial_no_support_filament_id] == \"PETG\") || (filament_type[initial_no_support_filament_id] == \"PETG-CF\")) && (nozzle_diameter_at_nozzle_id[initial_nozzle_id] == 0.2)}\nM620.10 A0 F74.8347 H{nozzle_diameter_at_nozzle_id[initial_nozzle_id]} T{flush_temperatures[initial_no_support_filament_id]} P{nozzle_temperature_initial_layer[initial_no_support_filament_id]} S1\nM620.10 A1 F74.8347 H{nozzle_diameter_at_nozzle_id[initial_nozzle_id]} T{flush_temperatures[initial_no_support_filament_id]} P{nozzle_temperature_initial_layer[initial_no_support_filament_id]} S1\n{else}\nM620.10 A0 F{flush_volumetric_speeds[initial_no_support_filament_id]/2.4053*60} H{nozzle_diameter_at_nozzle_id[initial_nozzle_id]} T{flush_temperatures[initial_no_support_filament_id]} P{nozzle_temperature_initial_layer[initial_no_support_filament_id]} S1\nM620.10 A1 F{flush_volumetric_speeds[initial_no_support_filament_id]/2.4053*60} H{nozzle_diameter_at_nozzle_id[initial_nozzle_id]} T{flush_temperatures[initial_no_support_filament_id]} P{nozzle_temperature_initial_layer[initial_no_support_filament_id]} S1\n{endif}\n\n M620.11 P0 L0 I[initial_no_support_filament_id] E0\n M620.11 K0 I[initial_no_support_filament_id] R0\n\n  M620 S[initial_no_support_filament_id]A   ; switch material if AMS exist\n  M1002 gcode_claim_action : 4\n  M1002 set_filament_type:UNKNOWN\n  M400\n  T[initial_no_support_filament_id]\n  M400\n  M628 S0\n  M629\n  M400\n  M1002 set_filament_type:{filament_type[initial_no_support_filament_id]}\n  M621 S[initial_no_support_filament_id]A\n  M104 S{nozzle_temperature_initial_layer[initial_no_support_filament_id]}\n  M400\n  M106 P1 S0\n  M400\n  G29.2 S1\n{if ((filament_type[initial_no_support_filament_id] == \"PETG\") || (filament_type[initial_no_support_filament_id] == \"PETG-CF\") || (filament_type[initial_no_support_filament_id] == \"TPU\") || (filament_type[initial_no_support_filament_id] == \"TPU-AMS\"))}\n  G390.7 M6 G4 C3\n{else}\n  G390.7 M6 G6 C3\n{endif}\n;===== prepare print temperature and material ==========\n\n\n;===== auto extrude cali start =========================\nM975 S1\nM1002 judge_flag extrude_cali_flag\n  M622 J0\n    M983.3 F{filament_max_volumetric_speed[initial_no_support_filament_id]/2.4} A0.4 ; cali dynamic extrusion compensation\n  M623\n\n  M622 J1\n    M1002 set_filament_type:{filament_type[initial_no_support_filament_id]}\n    M1002 gcode_claim_action : 8\n    M109 S{nozzle_temperature[initial_no_support_filament_id]}\n    G90\n    M83\n    M983.3 F{filament_max_volumetric_speed[initial_no_support_filament_id]/2.4} A0.4 ; cali dynamic extrusion compensation\n    M400\n  M623\n\n  M622 J2\n    M1002 set_filament_type:{filament_type[initial_no_support_filament_id]}\n    M1002 gcode_claim_action : 8\n    M109 S{nozzle_temperature[initial_no_support_filament_id]}\n    G90\n    M83\n    M983.3 F{filament_max_volumetric_speed[initial_no_support_filament_id]/2.4} A0.4 ; cali dynamic extrusion compensation\n    M400\n  M623\n;===== auto extrude cali end =========================\n\n\n  {if filament_type[initial_filament_id] == \"TPU\" || filament_type[initial_filament_id] == \"PVA\"}\n  {else}\n    M83\n    G1 E-3 F1800\n    M400 P500\n  {endif}\n  G0 Z1.3 F1200\n  G150.2\n  G150.1 F16000\n\n  G91\n  G1 X20 F12000 ; move away from the trash bin\n  G90\n  M400\n\n\n;===== wipe nozzle start =====\n  M1002 gcode_claim_action : 14\n  G150 T{nozzle_temperature_initial_layer[initial_no_support_filament_id]}\n  M400\n  M109 S140 A\n  M106 P1 S255\n  G91\n  G1 Z1.3 F1200\n  G90\n  M400 S1\n  ;======== enhance brush nozzle start =====\n  G150.1 F16000\n  G91\n  G1 Y5   F5000\n  G1 X-20 F16000\n  G1 Y-10 F5000\n  G1 X-20 F16000\n  G1 Y10  F5000\n  G1 X20  F16000\n  G1 Y-10 F5000\n  G1 X20  F16000\n  G1 Y5   F5000\n  G90\n  G150.1 F16000\n  G150.3\n  ;======== enhance brush nozzle end =====\n  M106 P1 S0\n;===== wipe nozzle end =====\n\n;===== mech mode sweep start =====\n  M1002 gcode_claim_action : 3\n  G90\n  G1 Z5 F1200\n  G1 X165 Y160 F20000\n  M400 P200\n  M970.3 Q1 A5 K0 O3\n  M970.3 Q1 B1\n  M970.2 Q1 K1 W52 Z0.1 B30 ;\n  M970.3 Q0 A10 K0 O1\n  M970.3 Q0 B1\n  M970.2 Q0 K1 W40 Z0.1 B20 ;\n  M974 Q0 S2 P0\n  M974 Q1 S2 P0\n  M975 S1 R1 M1\n  M400\n  G1 X155 F3000\n  G150.3\n;===== mech mode sweep end =====\n\n\n;===== bed leveling ==================================\n\n  {if hold_chamber_temp_for_flat_print && (bed_temperature_initial_layer_single == 55)}\n    M190 S65\n  {else}\n    M190 S[bed_temperature_initial_layer_single] ; ensure bed temp\n  {endif}\n  M109 S140 A\n\n\n  {if hold_chamber_temp_for_flat_print && (bed_temperature_initial_layer_single == 55)}\n    M1002 gcode_claim_action : 58\n    SYNC R0 T600\n    M1030 S500 ; action before has done 200s insulation\n    M1030 C\n  {else}\n    M1002 judge_flag bed_heat_stable_wait_flag\n    M622 J1\n      {if (bed_temperature_initial_layer_single > 35)}\n        M1002 gcode_claim_action : 54\n        G29.30 X{first_layer_print_min[0]} Y{first_layer_print_min[1]} I{first_layer_print_size[0]} J{first_layer_print_size[1]}\n      {endif}\n    M623\n  {endif}\n  SYNC R0 T120 ; Adjust estimated time\n\n  M106 S0 ; turn off fan , too noisy\n  M1002 judge_flag g29_before_print_flag\n  M622 J1\n    M1002 gcode_claim_action : 1\n    {if hold_chamber_temp_for_flat_print && (bed_temperature_initial_layer_single == 55)}\n      G29 R\n    {else}\n      {if (bed_temperature_initial_layer_single > 35)}\n        G29 A1 X{first_layer_print_min[0]} Y{first_layer_print_min[1]} I{first_layer_print_size[0]} J{first_layer_print_size[1]} O1 R\n      {else}\n        G29 A1 X{first_layer_print_min[0]} Y{first_layer_print_min[1]} I{first_layer_print_size[0]} J{first_layer_print_size[1]} O R\n      {endif}\n    {endif}\n    M400\n  M623\n\n  M622 J2\n    M1002 gcode_claim_action : 1\n    {if hold_chamber_temp_for_flat_print && (bed_temperature_initial_layer_single == 55)}\n      G29 R\n    {else}\n      {if (bed_temperature_initial_layer_single > 35)}\n        G29 A2 X{first_layer_print_min[0]} Y{first_layer_print_min[1]} I{first_layer_print_size[0]} J{first_layer_print_size[1]} O1 R\n      {else}\n        G29 A2 X{first_layer_print_min[0]} Y{first_layer_print_min[1]} I{first_layer_print_size[0]} J{first_layer_print_size[1]} O R\n      {endif}\n    {endif}\n    M400\n  M623\n\n  M622 J0\n    G28 R\n  M623\n  G29.2 S1\n;===== bed leveling end ================================\n\n  M985.1 U0 E2\n  M985.1 U1 E2\n\n  M104 S{nozzle_temperature_initial_layer[initial_filament_id]} A\n  G150.3 ; move to garbage can to wait for temp\n\n;===== wait temperature reaching the reference value =======\n  {if hold_chamber_temp_for_flat_print && (bed_temperature_initial_layer_single == 55)}\n    M190 S65\n  {else}\n    M190 S[bed_temperature_initial_layer_single] ; ensure bed temp\n  {endif}\n\n  ;========turn off light and fans =============\n  M960 S1 P0 ; turn off laser\n  M960 S2 P0 ; turn off laser\n  M106 S0 ; turn off cooling fan\n\n;===== wait temperature reaching the reference value =======\n\n  M1002 gcode_claim_action : 255\n  M400\n  M975 S1 ; turn on mech mode supression\n\n;===== for Textured PEI Plate , lower the nozzle as the nozzle was touching topmost of the texture when homing ==\n  {if curr_bed_type==\"Textured PEI Plate\"}\n    {if hold_chamber_temp_for_flat_print && (bed_temperature_initial_layer_single == 55)}\n      G29.1 Z{-0.03} ; for Textured PEI Plate first layer\n    {else}\n      G29.1 Z{-0.04} ; for Textured PEI Plate\n    {endif}\n  {else}\n    G29.1 Z{-0.01}\n  {endif}\n\n;===== nozzle load line ===============================\nM1002 gcode_claim_action : 51\n  G29.2 S1 ; ensure z comp turn on\n  G90\n  M83\n  M400 P50\n  M500 D1\n  M400 S3\n  M109 S{nozzle_temperature_initial_layer[initial_no_support_filament_id]}\n  G0 X145 Y0 F24000\n  M400\n  G130 O0 X145 Y-0.2 Z0.8 F{filament_max_volumetric_speed[initial_no_support_filament_id]/2/2.4053} L40 E20 D4\n  G90\n  M83\n  G1 Z0.2\n  M400\n;===== nozzle load line end ===========================\nM1007 S1 C1;turn on mass estimation && clear\nM1002 gcode_claim_action : 0\n  G29.99\n\n{if (filament_type[initial_no_support_filament_id] == \"TPU\")}\nM1015.3 S1 H{nozzle_diameter_at_nozzle_id[initial_nozzle_id]};enable tpu clog detect\n{else}\nM1015.3 S0;disable tpu clog detect\n{endif}\n\n{if (filament_type[initial_no_support_filament_id] == \"PLA\") ||  (filament_type[initial_no_support_filament_id] == \"PETG\")\n ||  (filament_type[initial_no_support_filament_id] == \"PLA-CF\")  ||  (filament_type[initial_no_support_filament_id] == \"PETG-CF\")}\nM1015.4 S1 K1 H{nozzle_diameter_at_nozzle_id[initial_nozzle_id]} ;enable E air printing detect\n{else}\nM1015.4 S0 K0 H{nozzle_diameter_at_nozzle_id[initial_nozzle_id]} ;disable E air printing detect\n{endif}\n\nM620.6 I[initial_no_support_filament_id] W1 ;enable ams air printing detect\n\nM1010 Q0 B0.005 S0.01\nM1010 Q1 B0.002 S0.01\nM1010.1 S1\n
; machine_switch_extruder_time = 0
; machine_unload_filament_time = 12
; master_extruder_id = 1
; max_bridge_length = 0
; max_layer_height = 0.28
; max_travel_detour_distance = 0
; min_bead_width = 85%
; min_feature_size = 25%
; min_layer_height = 0.08
; minimum_sparse_infill_area = 15
; mmu_segmented_region_interlocking_depth = 0
; mmu_segmented_region_max_width = 0
; monotonic_travel_into_wall = 0%
; no_slow_down_for_cooling_on_outwalls = 0,0,0,0
; nozzle_diameter = 0.4
; nozzle_flush_dataset = 0
; nozzle_height = 4.76
; nozzle_temperature = 220,220,220,220
; nozzle_temperature_initial_layer = 220,220,220,220
; nozzle_temperature_range_high = 240,240,240,240
; nozzle_temperature_range_low = 190,190,190,190
; nozzle_type = stainless_steel
; nozzle_volume = 92
; nozzle_volume_type = Standard
; only_one_wall_first_layer = 0
; ooze_prevention = 0
; other_layers_print_sequence = 0
; other_layers_print_sequence_nums = 0
; outer_wall_acceleration = 5000
; outer_wall_jerk = 9
; outer_wall_line_width = 0.42
; outer_wall_speed = 60
; overhang_1_4_speed = 0
; overhang_2_4_speed = 50
; overhang_3_4_speed = 30
; overhang_4_4_speed = 10
; overhang_fan_speed = 100,100,100,100
; overhang_fan_threshold = 25%,25%,25%,25%
; overhang_threshold_participating_cooling = 95%,95%,95%,95%
; overhang_totally_speed = 10
; override_filament_scarf_seam_setting = 0
; override_process_overhang_speed = 0,0,0,0
; physical_extruder_map = 0
; post_process = 
; pre_start_fan_time = 2,2,2,2
; precise_outer_wall = 0
; precise_z_height = 0
; pressure_advance = 0.02,0.02,0.02,0.02
; prime_tower_brim_width = -1
; prime_tower_enable_framework = 0
; prime_tower_extra_rib_length = 0
; prime_tower_fillet_wall = 1
; prime_tower_flat_ironing = 0
; prime_tower_infill_gap = 150%
; prime_tower_lift_height = -1
; prime_tower_lift_speed = 90
; prime_tower_max_speed = 90
; prime_tower_rib_wall = 1
; prime_tower_rib_width = 8
; prime_tower_skip_points = 1
; prime_tower_width = 35
; prime_volume_mode = Default
; print_compatible_printers = "Bambu Lab A2L 0.4 nozzle"
; print_extruder_id = 1
; print_extruder_variant = "Direct Drive Standard"
; print_flow_ratio = 1
; print_in_clockwise = 0
; print_sequence = by layer
; print_settings_id = 0.20mm Standard @BBL A2L
; printable_area = 0x0,330x0,330x320,0x320
; printable_height = 325
; printer_extruder_id = 1
; printer_extruder_variant = "Direct Drive Standard"
; printer_model = Bambu Lab A2L
; printer_notes = 
; printer_settings_id = Bambu Lab A2L 0.4 nozzle
; printer_structure = i3
; printer_technology = FFF
; printer_variant = 0.4
; printhost_authorization_type = key
; printhost_ssl_ignore_revoke = 0
; printing_by_object_gcode = 
; process_notes = 
; raft_contact_distance = 0.1
; raft_expansion = 1.5
; raft_first_layer_density = 90%
; raft_first_layer_expansion = -1
; raft_layers = 0
; reduce_crossing_wall = 0
; reduce_fan_stop_start_freq = 1,1,1,1
; reduce_infill_retraction_mode = Auto
; required_nozzle_HRC = 3,3,3,3
; resolution = 0.012
; retract_before_wipe = 0%
; retract_length_toolchange = 2
; retract_lift_above = 0
; retract_lift_below = 326
; retract_restart_extra = 0
; retract_restart_extra_toolchange = 0
; retract_when_changing_layer = 1
; retraction_distances_when_cut = 18
; retraction_distances_when_ec = 0,0,0,0
; retraction_length = 0.8
; retraction_minimum_travel = 1
; retraction_speed = 30
; role_base_wipe_speed = 1
; scan_first_layer = 0
; scarf_angle_threshold = 155
; seam_gap = 15%
; seam_placement_away_from_overhangs = 0
; seam_position = aligned
; seam_slope_conditional = 1
; seam_slope_entire_loop = 0
; seam_slope_gap = 0
; seam_slope_inner_walls = 1
; seam_slope_min_length = 10
; seam_slope_start_height = 10%
; seam_slope_steps = 10
; seam_slope_type = none
; silent_mode = 0
; single_extruder_multi_material = 1
; skeleton_infill_density = 10%
; skeleton_infill_line_width = 0.45
; skin_infill_density = 10%
; skin_infill_depth = 2
; skin_infill_line_width = 0.45
; skirt_distance = 2
; skirt_height = 1
; skirt_loops = 0
; skirt_per_object = 1
; slice_closing_radius = 0.049
; slicing_mode = regular
; slow_down_for_layer_cooling = 1,1,1,1
; slow_down_layer_time = 8,8,8,8
; slow_down_min_speed = 20,20,20,20
; slowdown_end_acc = 1000
; slowdown_end_height = 225
; slowdown_end_speed = 500
; slowdown_start_acc = 8000
; slowdown_start_height = 0
; slowdown_start_speed = 500
; small_perimeter_speed = 50%
; small_perimeter_threshold = 0
; smooth_coefficient = 4
; smooth_speed_discontinuity_area = 1
; solid_infill_filament = 0
; sparse_infill_acceleration = 100%
; sparse_infill_anchor = 400%
; sparse_infill_anchor_max = 20
; sparse_infill_density = 10%
; sparse_infill_filament = 0
; sparse_infill_lattice_angle_1 = -45
; sparse_infill_lattice_angle_2 = 45
; sparse_infill_line_width = 0.45
; sparse_infill_pattern = gyroid
; sparse_infill_speed = 270
; spiral_mode = 0
; spiral_mode_max_xy_smoothing = 200%
; spiral_mode_smooth = 0
; standby_temperature_delta = -5
; start_end_points = 30x-3,54x245
; supertack_plate_temp = 45,45,45,45
; supertack_plate_temp_initial_layer = 45,45,45,45
; support_air_filtration = 0
; support_angle = 0
; support_base_pattern = default
; support_base_pattern_spacing = 2.5
; support_bottom_interface_spacing = 0.5
; support_bottom_z_distance = 0.2
; support_chamber_temp_control = 0
; support_cooling_filter = 0
; support_critical_regions_only = 0
; support_expansion = 0
; support_fast_purge_mode = 1
; support_filament = 0
; support_interface_bottom_layers = 2
; support_interface_filament = 0
; support_interface_loop_pattern = 0
; support_interface_not_for_body = 1
; support_interface_pattern = auto
; support_interface_spacing = 0.5
; support_interface_speed = 80
; support_interface_top_layers = 2
; support_ironing_direction = 0
; support_ironing_flow = 10%
; support_ironing_inset = 0
; support_ironing_pattern = zig-zag
; support_ironing_spacing = 0.15
; support_ironing_speed = 30
; support_line_width = 0.42
; support_object_first_layer_gap = 0.2
; support_object_skip_flush = 1
; support_object_xy_distance = 0.35
; support_on_build_plate_only = 0
; support_remove_small_overhang = 1
; support_speed = 150
; support_style = default
; support_threshold_angle = 30
; support_top_z_distance = 0.2
; support_type = tree(auto)
; symmetric_infill_y_axis = 0
; temperature_vitrification = 45,45,45,45
; template_custom_gcode = 
; textured_plate_temp = 55,55,55,55
; textured_plate_temp_initial_layer = 55,55,55,55
; thick_bridges = 0
; thumbnail_size = 50x50
; time_lapse_gcode = ;======== A2L timelapse gcode ==========\n;===== 2026/05/09 ====\n{if !spiral_mode && print_sequence != \"by object\"}\n; SKIPPABLE_START\n; SKIPTYPE: timelapse\nM622.1 S1 ; for prev firware, default turned on\nM1002 judge_flag timelapse_record_flag\nM622 J1\n  G1 Z{max_layer_z + 0.4} F1200\n  G150.3 ; move to garbage can\n  G1 Y{first_layer_center_no_wipe_tower[1]} F30000; move to safe pos\n  M400\n  M1004 S5 P1  ; external shutter\n  M971 S11 C11 O0\n  M400 P350\nM623\n; SKIPPABLE_END\n{endif}\n; SKIPPABLE_START\n; SKIPTYPE: g39_detection\n; go x0 clamping detection, clear_to_x0 = [clear_to_x0]\n{if !spiral_mode && (print_sequence != \"by object\" || clear_to_x0)}\nM1002 judge_flag g39_detection_flag\nM622 J1\n  ; enable nozzle clog detect at 3rd layer\n  {if layer_num == 1 || layer_num == 2}\n    M400\n    G390.7 M7 S1 Z2.5\n  {endif}\n  {if layer_num > 5 && layer_z <= 10 && layer_z > 0.4 && layer_num % 6 == 0}\n    M400\n    G390.7 M7 S1 Z2.5\n  {endif}\n  M1002 judge_flag g39_mass_exceed_flag\n  M622 J1\n    {if layer_num > 2}\n      M400\n      G390.7 M9 S1 Z2.5\n    {endif}\n  M623\nM623\n{endif}\n; SKIPPABLE_END
; timelapse_type = 0
; top_area_threshold = 200%
; top_color_penetration_layers = 5
; top_one_wall_type = all top
; top_shell_layers = 5
; top_shell_thickness = 1
; top_solid_infill_flow_ratio = 1
; top_surface_acceleration = 2000
; top_surface_density = 100%
; top_surface_jerk = 9
; top_surface_line_width = 0.42
; top_surface_pattern = concentric
; top_surface_speed = 200
; top_z_overrides_xy_distance = 0
; travel_acceleration = 8000
; travel_jerk = 9
; travel_short_distance_acceleration = 250
; travel_speed = 500
; travel_speed_z = 0
; tree_support_branch_angle = 45
; tree_support_branch_diameter = 2
; tree_support_branch_diameter_angle = 5
; tree_support_branch_distance = 5
; tree_support_wall_count = -1
; upward_compatible_machine = "Bambu Lab H2S 0.4 nozzle"
; use_firmware_retraction = 0
; use_relative_e_distances = 1
; vertical_shell_speed = 80%
; volumetric_speed_coefficients = "0 0 0 0 0 0";"0 0 0 0 0 0";"0 0 0 0 0 0";"0 0 0 0 0 0"
; wall_distribution_count = 1
; wall_filament = 0
; wall_generator = classic
; wall_loops = 3
; wall_sequence = inner wall/outer wall
; wall_transition_angle = 10
; wall_transition_filter_deviation = 25%
; wall_transition_length = 100%
; wipe = 1
; wipe_distance = 2
; wipe_speed = 80%
; wipe_tower_no_sparse_layers = 0
; wipe_tower_rotation_angle = 0
; wipe_tower_x = 92.9885
; wipe_tower_y = 250.385
; wrapping_detection_gcode = 
; wrapping_detection_layers = 20
; wrapping_exclude_area = 
; xy_contour_compensation = 0
; xy_hole_compensation = 0
; z_direction_outwall_speed_continuous = 0
; z_hop = 0.4
; z_hop_types = Auto Lift
; CONFIG_BLOCK_END

; EXECUTABLE_BLOCK_START
M73 P0 R4104
M201 X12000 Y8000 Z1500 E5000
M203 X500 Y500 Z30 E30
M204 P12000 R5000 T12000
M205 X9.00 Y9.00 Z3.00 E3.00
M106 S0
; FEATURE: Custom
;M1002 set_flag extrude_cali_flag=1
;M1002 set_flag g29_before_print_flag=1
;M1002 set_flag build_plate_detect_flag=1
;M1002 set_flag bed_heat_stable_wait_flag=1

;======== A2L start gcode==========
;===== 2026/05/26 =====
T1000 O0
M1002 gcode_claim_action : 2

    M140 S55 ; heat heatbed first


M993 A0 B0 C0 ; nozzle cam detection not allowed.
M400

;=====printer start sound ===================
M17
M400 S1
M1006 S1
M1006 A53 B9 L30 C53 D9 M30 E53 F9 N30
M1006 A56 B9 L30 C56 D9 M30 E56 F9 N30
M1006 A61 B9 L30 C61 D9 M30 E61 F9 N30
M1006 A53 B9 L30 C53 D9 M30 E53 F9 N30
M1006 A56 B9 L30 C56 D9 M30 E56 F9 N30
M1006 A61 B18 L30 C61 D18 M30 E61 F18 N30
M1006 W
;=====printer start sound ===================

  M620 M ;enable remap
  G389

;===== avoid end stop =================
  G91
  G380 S2 Z22 F1200
  G380 S2 Z-12 F1200
  G90
;===== avoid end stop =================

;===== reset machine status =================
  M204 S10000
  M630 S0 P1
  G90
  M17 D ; reset motor current to default
  M960 S5 P1 ; turn on logo lamp
  M220 S100 ;Reset Feedrate
  M221 S100 ;Reset Flowrate
  M73.2   R1.0 ;Reset left time magnitude
  G29.1 Z0 ; clear z-trim value first
  M983.1 M1
  M982.2 S1 ; turn on cog noise reduction
  M983.4 S0
;===== reset machine status =================
;Set the filament gear warning temperature

    
        M142 P1 O60; set PLA/PLACF/PLAAERO/PVA/TPU gear warning temperature when start
    

;===== start to heat heatbed & hotend==========
  M1002 set_filament_type:PLA
  M104 S140 A

  G29.2 S0 ; avoid invalid abl data

;===== first homing start =====
  M1002 gcode_claim_action : 13
  M105
  G28 X Z P0 T300 W
  G150.3
  G1 Z1.3 F1200
  G150.1 F16000 ; wipe mouth to avoid filament stick to heatbed
  G90
  M400
;===== first homing end =====


;===== detection start =====
;===== build_plate_detect_flag start =====
M1002 judge_flag build_plate_detect_flag
M622 S1
  G91
  G1 Z5 F1200
  G90
  G0 X15 F30000
  G0 Y319 F3000
  G91
  G1 Z-5 F1200
  G28 Z P0 T140
  G1 F1200
  G39.4
  G90
  G1 Z5 F1200
M623
;===== build_plate_detect_flag end =====
;===== detection end =====


;===== hotend hotbed pre-heat start =====
  M104 S140 A ; rise nozzle temp in advance

  G90
  G1 Y220 F3000 ; Put away the heated bed to prevent collisions

  
      M190 S55
  
;===== hotend hotbed pre-heat end =====


;===== prepare print temperature and material ==========
  M400
  M211 X0 Y0 Z0 ;turn off soft endstop
  M975 S1 ; turn on input shaping

  G29.2 S0 ; avoid invalid abl data
  G150.3

M620.10 A0 F299.339 H0.4 T240 P220 S1
M620.10 A1 F299.339 H0.4 T240 P220 S1


 M620.11 P0 L0 I2 E0
 M620.11 K0 I2 R0

  M620 S2A   ; switch material if AMS exist
  M1002 gcode_claim_action : 4
  M1002 set_filament_type:UNKNOWN
  M400
  T2
  M400
  M628 S0
  M629
  M400
  M1002 set_filament_type:PLA
  M621 S2A
  M104 S220
  M400
  M106 P1 S0
  M400
  G29.2 S1

  G390.7 M6 G6 C3

;===== prepare print temperature and material ==========


;===== auto extrude cali start =========================
M975 S1
M1002 judge_flag extrude_cali_flag
  M622 J0
    M983.3 F5 A0.4 ; cali dynamic extrusion compensation
  M623

  M622 J1
    M1002 set_filament_type:PLA
    M1002 gcode_claim_action : 8
    M109 S220
    G90
    M83
    M983.3 F5 A0.4 ; cali dynamic extrusion compensation
    M400
  M623

  M622 J2
    M1002 set_filament_type:PLA
    M1002 gcode_claim_action : 8
    M109 S220
    G90
    M83
    M983.3 F5 A0.4 ; cali dynamic extrusion compensation
    M400
  M623
;===== auto extrude cali end =========================


  
    M83
    G1 E-3 F1800
    M400 P500
  
  G0 Z1.3 F1200
  G150.2
  G150.1 F16000

  G91
  G1 X20 F12000 ; move away from the trash bin
  G90
  M400


;===== wipe nozzle start =====
  M1002 gcode_claim_action : 14
  G150 T220
  M400
  M109 S140 A
  M106 P1 S255
  G91
  G1 Z1.3 F1200
  G90
  M400 S1
  ;======== enhance brush nozzle start =====
  G150.1 F16000
  G91
  G1 Y5   F5000
  G1 X-20 F16000
  G1 Y-10 F5000
  G1 X-20 F16000
  G1 Y10  F5000
  G1 X20  F16000
  G1 Y-10 F5000
  G1 X20  F16000
  G1 Y5   F5000
  G90
  G150.1 F16000
  G150.3
  ;======== enhance brush nozzle end =====
  M106 P1 S0
;===== wipe nozzle end =====

;===== mech mode sweep start =====
  M1002 gcode_claim_action : 3
  G90
  G1 Z5 F1200
  G1 X165 Y160 F20000
  M400 P200
  M970.3 Q1 A5 K0 O3
  M970.3 Q1 B1
  M970.2 Q1 K1 W52 Z0.1 B30 ;
  M970.3 Q0 A10 K0 O1
  M970.3 Q0 B1
  M970.2 Q0 K1 W40 Z0.1 B20 ;
  M974 Q0 S2 P0
  M974 Q1 S2 P0
  M975 S1 R1 M1
  M400
  G1 X155 F3000
  G150.3
;===== mech mode sweep end =====


;===== bed leveling ==================================

  
    M190 S55 ; ensure bed temp
  
  M109 S140 A


  
    M1002 judge_flag bed_heat_stable_wait_flag
    M622 J1
      
        M1002 gcode_claim_action : 54
        G29.30 X48.1452 Y33.7757 I232.677 J263.72
      
    M623
  
  SYNC R0 T120 ; Adjust estimated time

  M106 S0 ; turn off fan , too noisy
  M1002 judge_flag g29_before_print_flag
  M622 J1
    M1002 gcode_claim_action : 1
    
      
        G29 A1 X48.1452 Y33.7757 I232.677 J263.72 O1 R
      
    
    M400
  M623

  M622 J2
    M1002 gcode_claim_action : 1
    
      
        G29 A2 X48.1452 Y33.7757 I232.677 J263.72 O1 R
      
    
    M400
  M623

  M622 J0
    G28 R
  M623
  G29.2 S1
;===== bed leveling end ================================

  M985.1 U0 E2
  M985.1 U1 E2

  M104 S220 A
  G150.3 ; move to garbage can to wait for temp

;===== wait temperature reaching the reference value =======
  
    M190 S55 ; ensure bed temp
  

  ;========turn off light and fans =============
  M960 S1 P0 ; turn off laser
  M960 S2 P0 ; turn off laser
  M106 S0 ; turn off cooling fan

;===== wait temperature reaching the reference value =======

  M1002 gcode_claim_action : 255
  M400
  M975 S1 ; turn on mech mode supression

;===== for Textured PEI Plate , lower the nozzle as the nozzle was touching topmost of the texture when homing ==
  
    
      G29.1 Z-0.04 ; for Textured PEI Plate
    
  

;===== nozzle load line ===============================
M1002 gcode_claim_action : 51
  G29.2 S1 ; ensure z comp turn on
  G90
  M83
  M400 P50
  M500 D1
  M400 S3
  M109 S220
  G0 X145 Y0 F24000
  M400
  G130 O0 X145 Y-0.2 Z0.8 F2.49449 L40 E20 D4
  G90
  M83
  G1 Z0.2
  M400
;===== nozzle load line end ===========================
M1007 S1 C1;turn on mass estimation && clear
M1002 gcode_claim_action : 0
  G29.99


M1015.3 S0;disable tpu clog detect



M1015.4 S1 K1 H0.4 ;enable E air printing detect


M620.6 I2 W1 ;enable ams air printing detect

M1010 Q0 B0.005 S0.01
M1010 Q1 B0.002 S0.01
M1010.1 S1
; MACHINE_START_GCODE_END
;VT2 H-1
G90
G21
M83 ; use relative distances for extrusion
M981 S1 P20000 ;open spaghetti detector
M204 S8000
G1 Z.6 F30000
; CHANGE_LAYER
; Z_HEIGHT: 0.2
; LAYER_HEIGHT: 0.2
G1 E-.8 F1800
;======== A2L layer_change gcode ==========
;===== 2026/04/29 ====
; update layer progress
M201 N1 Y8000
M73 L1
M991 S0 P0 ;notify layer change
M1007 L1
M106 S0
; OBJECT_ID: 1235
; start printing object, unique label id: 1235
M624 AAIAAAAAAAA=
G1 X74.574 Y77.307 F30000
M204 S6000
G1 Z1
M73 P0 R4097
G1 Z.2
G1 E.8 F1800
; FEATURE: Brim
; LINE_WIDTH: 0.5
; LAYER_HEIGHT: 0.2
G1 F3000
M204 S500
G1 X75.093 Y76.849 E.02575
G1 X75.68 Y76.405 E.02744
G1 X76.242 Y76.042 E.0249
G1 X76.885 Y75.69 E.02731
G1 X77.501 Y75.41 E.02522
G1 X78.184 Y75.158 E.02713
G1 X79.036 Y74.927 E.03287
G1 X79.822 Y74.783 E.02975
G1 X80.758 Y74.701 E.03498
G1 X81.616 Y74.707 E.03196
G1 X82.557 Y74.803 E.03526
G1 X82.702 Y74.769 E.00555
G1 X83.311 Y74.014 E.03614
G1 X83.938 Y73.354 E.03387
G1 X84.648 Y72.739 E.03499
G1 X85.274 Y72.29 E.0287
G1 X86.036 Y71.834 E.03308
G1 X86.683 Y71.521 E.02677
G1 X87.432 Y71.23 E.02993
G1 X88.222 Y70.997 E.03067
G1 X89.146 Y70.815 E.03507
G1 X89.849 Y70.74 E.02636
G1 X90.715 Y70.714 E.03226
G1 X91.412 Y70.757 E.026
G1 X92.145 Y70.854 E.02753
G1 X92.802 Y70.991 E.02501
G1 X93.657 Y71.246 E.03323
G1 X94.366 Y71.524 E.02835
G1 X94.673 Y71.667 E.01263
G1 X95.313 Y72.007 E.02697
G1 X95.848 Y72.343 E.02355
G1 X96.44 Y72.777 E.02733
G1 X96.96 Y73.223 E.02552
G1 X97.285 Y73.535 E.01678
G1 X97.59 Y73.859 E.01658
G1 X98.012 Y74.358 E.02434
G1 X98.562 Y75.136 E.03548
G1 X98.91 Y75.737 E.02588
G1 X99.116 Y76.146 E.01705
G1 X99.4 Y76.8 E.02657
G1 X99.624 Y77.455 E.02577
G1 X99.753 Y77.923 E.01809
G1 X99.865 Y78.427 E.01924
G1 X99.971 Y79.09 E.02501
G1 X100.018 Y79.575 E.01816
G1 X100.039 Y80.04 E.01734
G1 X100.028 Y80.728 E.02563
G1 X99.964 Y81.444 E.02678
G1 X99.894 Y81.905 E.01735
G1 X99.749 Y82.578 E.02564
G1 X99.623 Y83.03 E.01749
G1 X99.475 Y83.475 E.01744
G1 X99.204 Y84.143 E.02687
G1 X98.898 Y84.763 E.02574
G1 X98.614 Y85.251 E.02105
G1 X98.235 Y85.822 E.02552
G1 X97.847 Y86.317 E.0234
G1 X97.181 Y87.04 E.03661
G1 X97.121 Y87.176 E.00555
G1 X97.199 Y87.367 E.00767
G1 X97.782 Y87.875 E.02881
G1 X98.436 Y88.558 E.03523
G1 X98.959 Y89.218 E.03134
G1 X99.415 Y89.907 E.0308
G1 X99.534 Y89.998 E.00555
G1 X99.721 Y89.978 E.00703
G1 X100.131 Y89.739 E.01766
G1 X100.726 Y89.48 E.02419
G1 X101.11 Y89.36 E.01495
G1 X101.746 Y89.226 E.02423
G1 X102.081 Y89.176 E.01261
G1 X102.863 Y89.11 E.02922
G1 X103.334 Y89.092 E.01755
G1 X104.286 Y89.088 E.03547
G1 X104.988 Y89.116 E.02616
G1 X105.991 Y89.222 E.03756
G1 X106.27 Y89.272 E.01057
G1 X106.901 Y89.435 E.02428
G1 X107.567 Y89.711 E.02683
G1 X107.69 Y89.78 E.00528
G1 X107.837 Y89.807 E.00555
G1 X107.994 Y89.706 E.00698
G1 X108.445 Y89.01 E.03089
G1 X109.026 Y88.272 E.03496
G1 X109.452 Y87.813 E.02335
G1 X110.137 Y87.184 E.03463
G1 X110.208 Y87.053 E.00555
G1 X110.148 Y86.858 E.0076
G1 X109.504 Y86.183 E.03477
G1 X109.101 Y85.689 E.02371
G1 X108.713 Y85.128 E.02541
G1 X108.312 Y84.449 E.02938
G1 X107.997 Y83.802 E.02679
G1 X107.742 Y83.162 E.02568
G1 X107.526 Y82.475 E.02681
G1 X107.323 Y81.558 E.03497
G1 X107.232 Y80.879 E.02553
G1 X107.19 Y80.164 E.02667
G1 X107.2 Y79.477 E.02557
G1 X107.271 Y78.703 E.02896
G1 X107.437 Y77.804 E.03406
G1 X107.561 Y77.324 E.01846
G1 X107.786 Y76.633 E.02705
G1 X108.137 Y75.811 E.0333
G1 X108.585 Y74.988 E.03491
G1 X109.006 Y74.362 E.02806
G1 X109.315 Y73.959 E.01893
G1 X109.804 Y73.397 E.02775
G1 X110.297 Y72.916 E.02566
G1 X110.625 Y72.634 E.01611
G1 X111.154 Y72.219 E.02503
G1 X111.712 Y71.851 E.02491
G1 X112.38 Y71.476 E.02852
G1 X113.023 Y71.176 E.02643
G1 X113.858 Y70.873 E.03307
G1 X114.232 Y70.763 E.01454
G1 X114.891 Y70.611 E.02519
G1 X115.603 Y70.501 E.02684
G1 X116.324 Y70.442 E.02693
G1 X116.94 Y70.441 E.02295
G1 X117.904 Y70.512 E.03602
G1 X118.532 Y70.612 E.02369
G1 X119.035 Y70.725 E.01918
G1 X119.553 Y70.871 E.02006
G1 X120.172 Y71.087 E.02439
G1 X121.034 Y71.473 E.0352
G1 X121.462 Y71.704 E.01813
G1 X122.455 Y72.363 E.04437
G1 X122.995 Y72.807 E.02602
G1 X123.332 Y73.118 E.0171
G1 X123.812 Y73.614 E.0257
G1 X124.375 Y74.309 E.03332
G1 X124.502 Y74.388 E.00555
G1 X124.581 Y74.392 E.00295
G1 X125.444 Y74.286 E.0324
G1 X126.155 Y74.26 E.02651
G1 X127.092 Y74.305 E.03491
G1 X127.556 Y74.361 E.01744
G1 X128.444 Y74.532 E.03367
G1 X128.932 Y74.666 E.01886
G1 X129.807 Y74.979 E.0346
G1 X130.474 Y75.286 E.02735
G1 X131.202 Y75.698 E.03116
G1 X131.855 Y76.143 E.02943
G1 X132.409 Y76.589 E.02649
G1 X133.039 Y77.182 E.03221
G1 X133.5 Y77.701 E.02587
G1 X133.95 Y78.29 E.02761
G1 X134.318 Y78.851 E.02499
G1 X134.745 Y79.638 E.03333
G1 X134.905 Y79.984 E.01422
G1 X135.167 Y80.654 E.0268
G1 X135.289 Y81.031 E.01475
G1 X135.456 Y81.662 E.02431
G1 X135.586 Y82.348 E.026
G1 X135.632 Y82.687 E.01274
G1 X135.684 Y83.364 E.02532
G1 X135.691 Y84.057 E.02578
G1 X135.648 Y84.706 E.02425
G1 X135.594 Y85.143 E.01639
G1 X135.472 Y85.829 E.02595
G1 X135.287 Y86.525 E.02681
G1 X135.144 Y86.96 E.01706
G1 X134.883 Y87.624 E.02659
G1 X134.579 Y88.245 E.02574
G1 X134.34 Y88.667 E.01808
G1 X134.063 Y89.103 E.01924
G1 X133.661 Y89.658 E.0255
G1 X133.36 Y90.023 E.01761
G1 X132.891 Y90.525 E.02563
G1 X132.364 Y91.012 E.02671
G1 X132.003 Y91.307 E.01736
G1 X131.444 Y91.709 E.02565
G1 X130.831 Y92.084 E.02677
G1 X130.417 Y92.304 E.01744
G1 X129.789 Y92.589 E.02573
G1 X129.111 Y92.839 E.0269
G1 X128.663 Y92.972 E.01741
G1 X127.896 Y93.145 E.02929
G1 X127.455 Y93.217 E.01664
G1 X126.683 Y93.287 E.02887
G1 X126.082 Y93.302 E.0224
G1 X125.942 Y93.354 E.00555
G1 X125.859 Y93.546 E.0078
G1 X125.913 Y94.317 E.0288
G1 X125.893 Y95.264 E.03528
G1 X125.813 Y95.999 E.02754
G1 X125.66 Y96.793 E.03011
G1 X125.681 Y96.941 E.00555
G1 X125.813 Y97.053 E.00645
G1 X126.671 Y97.336 E.03365
G1 X127.357 Y97.701 E.02893
G1 X127.721 Y97.934 E.01609
G1 X128.129 Y98.216 E.01848
G1 X128.637 Y98.619 E.02416
G1 X129.591 Y99.487 E.04804
G1 X130.597 Y100.478 E.0526
G1 X130.93 Y100.856 E.01877
G1 X131.168 Y101.178 E.0149
G1 X131.439 Y101.613 E.01907
G1 X131.614 Y101.96 E.01447
G1 X131.889 Y102.691 E.0291
G1 X131.917 Y102.806 E.00444
G1 X131.998 Y102.932 E.00555
G1 X132.173 Y102.979 E.00677
G1 X132.872 Y102.874 E.0263
G1 X133.599 Y102.821 E.02716
G1 X134.377 Y102.826 E.02899
G1 X134.965 Y102.87 E.02195
G1 X135.109 Y102.833 E.00555
G1 X135.21 Y102.651 E.00774
G1 X135.247 Y101.719 E.03476
G1 X135.324 Y101.063 E.02458
G1 X135.526 Y100.117 E.03603
G1 X135.74 Y99.42 E.02715
G1 X136.094 Y98.547 E.03511
G1 X136.407 Y97.935 E.02561
G1 X136.903 Y97.137 E.03497
G1 X137.331 Y96.565 E.02663
G1 X137.957 Y95.867 E.03492
G1 X138.456 Y95.397 E.02554
G1 X139.061 Y94.909 E.02896
G1 X139.823 Y94.401 E.03407
G1 X140.252 Y94.157 E.01841
G1 X141.109 Y93.753 E.03527
G1 X141.763 Y93.509 E.02601
G1 X142.641 Y93.266 E.03392
G1 X143.624 Y93.097 E.03715
G1 X144.419 Y93.041 E.02969
G1 X144.869 Y93.035 E.01679
G1 X145.697 Y93.084 E.03089
G1 X146.394 Y93.177 E.02617
G1 X147.072 Y93.326 E.02587
G1 X147.803 Y93.543 E.02841
G1 X148.668 Y93.884 E.03463
G1 X149.607 Y94.377 E.0395
G1 X150.175 Y94.745 E.02521
G1 X150.75 Y95.18 E.02685
G1 X151.289 Y95.65 E.02662
G1 X151.734 Y96.108 E.0238
G1 X152.192 Y96.642 E.02621
G1 X152.621 Y97.228 E.02706
G1 X152.981 Y97.802 E.02522
G1 X153.319 Y98.444 E.02704
G1 X153.594 Y99.073 E.02553
G1 X153.832 Y99.75 E.02673
G1 X154.051 Y100.606 E.0329
G1 X154.183 Y101.395 E.02981
G1 X154.252 Y102.33 E.03491
G1 X154.23 Y103.24 E.03393
G1 X154.123 Y104.127 E.03328
G1 X154.155 Y104.273 E.00555
G1 X154.206 Y104.332 E.00294
G1 X154.902 Y104.894 E.0333
G1 X155.552 Y105.529 E.03384
G1 X156.156 Y106.248 E.03498
G1 X156.596 Y106.881 E.02872
G1 X157.042 Y107.651 E.03312
G1 X157.345 Y108.301 E.02672
G1 X157.633 Y109.079 E.03089
G1 X157.847 Y109.849 E.02979
G1 X157.983 Y110.548 E.02652
G1 X158.08 Y111.478 E.03482
G1 X158.093 Y112.345 E.0323
G1 X158.04 Y113.041 E.02598
G1 X157.932 Y113.771 E.02751
G1 X157.736 Y114.615 E.03228
G1 X157.516 Y115.285 E.02627
G1 X157.23 Y115.983 E.02809
G1 X157.083 Y116.288 E.01261
G1 X156.733 Y116.924 E.02701
G1 X156.389 Y117.453 E.0235
G1 X155.945 Y118.042 E.02748
G1 X155.493 Y118.553 E.02541
G1 X155.177 Y118.872 E.01676
G1 X154.848 Y119.174 E.01659
G1 X154.345 Y119.587 E.02424
G1 X153.558 Y120.126 E.03556
G1 X152.952 Y120.465 E.02585
G1 X152.541 Y120.665 E.01701
G1 X151.903 Y120.932 E.02577
G1 X151.224 Y121.154 E.02663
G1 X150.754 Y121.277 E.01808
G1 X150.248 Y121.381 E.01923
G1 X149.571 Y121.479 E.02548
G1 X149.097 Y121.517 E.01771
G1 X148.632 Y121.532 E.01735
G1 X147.944 Y121.511 E.02561
G1 X147.23 Y121.437 E.02677
G1 X146.77 Y121.36 E.01736
G1 X146.098 Y121.205 E.02567
G1 X145.65 Y121.072 E.01742
G1 X144.971 Y120.825 E.02691
G1 X144.543 Y120.638 E.0174
G1 X143.927 Y120.323 E.02575
G1 X143.442 Y120.031 E.02109
G1 X142.876 Y119.643 E.02554
G1 X142.388 Y119.249 E.02337
G1 X141.675 Y118.572 E.03662
G1 X141.539 Y118.511 E.00555
G1 X141.348 Y118.586 E.00767
G1 X140.83 Y119.162 E.02885
G1 X140.3 Y119.666 E.02727
G1 X139.712 Y120.143 E.02818
G1 X139.216 Y120.491 E.02258
G1 X139.129 Y120.612 E.00555
G1 X139.153 Y120.798 E.007
G1 X139.412 Y121.338 E.0223
G1 X139.615 Y121.955 E.0242
G1 X139.723 Y122.486 E.02018
G1 X139.793 Y122.949 E.01743
G1 X139.847 Y123.517 E.02123
G1 X139.917 Y125.201 E.06278
G1 X139.891 Y126.447 E.04642
G1 X139.851 Y126.901 E.017
G1 X139.767 Y127.429 E.0199
G1 X139.524 Y128.263 E.03235
G1 X139.243 Y128.853 E.02435
G1 X139.227 Y129.001 E.00555
G1 X139.319 Y129.138 E.00614
G1 X139.923 Y129.562 E.02748
G1 X140.509 Y130.047 E.02834
G1 X141.036 Y130.558 E.02734
G1 X141.439 Y131.005 E.02241
G1 X141.57 Y131.077 E.00555
G1 X141.768 Y131.016 E.00773
G1 X142.438 Y130.366 E.03476
G1 X142.946 Y129.946 E.02454
G1 X143.746 Y129.401 E.03605
G1 X144.384 Y129.043 E.02725
G1 X145.008 Y128.753 E.02564
G1 X145.892 Y128.43 E.03504
G1 X146.8 Y128.196 E.03495
G1 X147.506 Y128.078 E.02667
G1 X148.188 Y128.016 E.0255
G1 X149.106 Y128.009 E.03417
G1 X149.9 Y128.074 E.02968
G1 X150.8 Y128.233 E.03407
G1 X151.274 Y128.351 E.0182
G1 X152.163 Y128.647 E.03489
G1 X152.817 Y128.925 E.02646
G1 X153.625 Y129.359 E.03416
G1 X154.45 Y129.914 E.03705
G1 X155.065 Y130.422 E.02969
G1 X155.395 Y130.729 E.01679
G1 X155.954 Y131.329 E.03053
G1 X156.4 Y131.886 E.0266
G1 X156.787 Y132.462 E.02581
G1 X157.168 Y133.126 E.02852
G1 X157.472 Y133.767 E.02643
G1 X157.781 Y134.596 E.03297
G1 X157.99 Y135.345 E.02893
G1 X158.114 Y135.966 E.02359
G1 X158.167 Y136.338 E.01403
G1 X158.233 Y137.061 E.02703
G1 X158.231 Y137.935 E.03254
G1 X158.175 Y138.642 E.0264
G1 X158.074 Y139.297 E.02469
G1 X157.907 Y140.024 E.0278
G1 X157.624 Y140.895 E.0341
G1 X157.349 Y141.552 E.02653
G1 X157.01 Y142.211 E.02761
G1 X156.506 Y143.001 E.03487
G1 X156.223 Y143.382 E.0177
G1 X155.61 Y144.092 E.03494
G1 X155.101 Y144.591 E.02653
G1 X154.428 Y145.143 E.03242
G1 X154.35 Y145.27 E.00555
G1 X154.347 Y145.35 E.00298
G1 X154.458 Y146.18 E.03118
G1 X154.494 Y147.094 E.03408
G1 X154.436 Y148.074 E.03655
G1 X154.316 Y148.843 E.02899
G1 X154.107 Y149.707 E.03311
G1 X153.877 Y150.386 E.02672
G1 X153.559 Y151.126 E.02999
G1 X153.172 Y151.852 E.03063
G1 X152.654 Y152.637 E.03505
G1 X152.213 Y153.195 E.0265
G1 X151.626 Y153.828 E.03215
G1 X151.107 Y154.295 E.02599
G1 X150.524 Y154.749 E.02754
G1 X149.965 Y155.122 E.025
G1 X149.185 Y155.553 E.03323
G1 X148.49 Y155.864 E.02835
G1 X148.143 Y155.993 E.0138
G1 X147.482 Y156.2 E.02579
G1 X146.867 Y156.346 E.02356
G1 X146.138 Y156.466 E.02749
G1 X145.48 Y156.522 E.02459
G1 X144.917 Y156.538 E.02098
G1 X143.914 Y156.478 E.03744
G1 X142.973 Y156.325 E.03549
G1 X142.3 Y156.151 E.02589
G1 X141.869 Y156.014 E.01686
G1 X141.219 Y155.765 E.02592
G1 X140.574 Y155.456 E.02664
G1 X140.15 Y155.221 E.01807
G1 X139.712 Y154.947 E.01923
G1 X139.165 Y154.558 E.02502
G1 X138.786 Y154.251 E.01815
G1 X138.439 Y153.94 E.01736
G1 X137.956 Y153.45 E.02563
G1 X137.49 Y152.903 E.02675
G1 X137.211 Y152.53 E.01736
G1 X136.832 Y151.955 E.02565
G1 X136.599 Y151.548 E.01746
G1 X136.279 Y150.901 E.0269
G1 X136.098 Y150.47 E.0174
G1 X135.87 Y149.817 E.02577
G1 X135.721 Y149.271 E.02107
G1 X135.58 Y148.601 E.02548
G1 X135.499 Y147.977 E.02343
G1 X135.45 Y146.996 E.03662
G1 X135.394 Y146.857 E.00555
G1 X135.204 Y146.779 E.00766
G1 X134.434 Y146.839 E.02877
G1 X133.48 Y146.826 E.03552
G1 X132.737 Y146.75 E.02784
G1 X131.902 Y146.593 E.03163
G1 X131.754 Y146.615 E.00555
G1 X131.64 Y146.755 E.00674
G1 X131.507 Y147.222 E.01809
G1 X131.365 Y147.59 E.01467
G1 X131.051 Y148.233 E.02664
G1 X130.806 Y148.672 E.01874
G1 X130.294 Y149.356 E.03182
G1 X129.521 Y150.2 E.04263
G1 X128.592 Y151.176 E.05019
G1 X128.146 Y151.611 E.02323
G1 X127.916 Y151.818 E.01151
G1 X127.396 Y152.209 E.02423
G1 X126.914 Y152.479 E.02059
G1 X126.311 Y152.733 E.02437
G1 X125.909 Y152.868 E.01581
G1 X125.791 Y152.96 E.00555
G1 X125.755 Y153.118 E.00603
G1 X125.864 Y153.871 E.02834
G1 X125.912 Y154.629 E.02831
G1 X125.901 Y155.354 E.02702
G1 X125.85 Y155.964 E.02277
G1 X125.887 Y156.108 E.00555
G1 X126.07 Y156.211 E.00782
G1 X126.781 Y156.236 E.02652
G1 X127.658 Y156.339 E.03288
G1 X128.598 Y156.548 E.03586
G1 X129.294 Y156.768 E.02721
G1 X129.933 Y157.025 E.02564
G1 X130.774 Y157.448 E.03506
G1 X131.566 Y157.95 E.03493
G1 X132.135 Y158.384 E.02664
G1 X132.828 Y159.015 E.03491
G1 X133.293 Y159.518 E.02553
G1 X133.78 Y160.133 E.02918
G1 X134.277 Y160.893 E.03383
G1 X134.515 Y161.319 E.01818
G1 X134.908 Y162.17 E.03491
G1 X135.151 Y162.836 E.02642
G1 X135.389 Y163.724 E.03423
G1 X135.549 Y164.706 E.03705
G1 X135.598 Y165.502 E.0297
G1 X135.6 Y165.964 E.01724
G1 X135.545 Y166.772 E.03017
G1 X135.445 Y167.476 E.02647
G1 X135.29 Y168.152 E.02584
G1 X135.066 Y168.884 E.0285
G1 X134.807 Y169.545 E.02643
G1 X134.413 Y170.338 E.03299
G1 X134.011 Y171.002 E.0289
G1 X133.641 Y171.522 E.02378
G1 X133.078 Y172.188 E.03247
G1 X132.467 Y172.792 E.032
G1 X131.93 Y173.243 E.02612
G1 X131.339 Y173.669 E.02715
G1 X130.764 Y174.022 E.02513
G1 X130.124 Y174.353 E.02684
G1 X129.488 Y174.624 E.02574
G1 X128.808 Y174.857 E.02677
G1 X127.951 Y175.068 E.03287
G1 X127.162 Y175.194 E.02978
G1 X126.224 Y175.254 E.03498
G1 X125.315 Y175.224 E.0339
G1 X124.428 Y175.11 E.03331
G1 X124.282 Y175.14 E.00555
G1 X124.221 Y175.192 E.00295
G1 X123.666 Y175.872 E.03271
G1 X123.046 Y176.498 E.03281
G1 X122.297 Y177.121 E.03626
G1 X121.654 Y177.56 E.02901
G1 X120.881 Y177.998 E.03311
G1 X120.228 Y178.297 E.02675
G1 X119.609 Y178.527 E.0246
G1 X118.886 Y178.736 E.02802
G1 X118.205 Y178.878 E.02591
G1 X117.498 Y178.972 E.02656
G1 X116.804 Y179.012 E.02589
G1 X115.959 Y178.995 E.03147
G1 X115.108 Y178.9 E.0319
G1 X114.441 Y178.77 E.02532
G1 X113.719 Y178.572 E.02788
G1 X112.889 Y178.268 E.0329
G1 X112.24 Y177.964 E.0267
G1 X111.892 Y177.776 E.01474
G1 X111.335 Y177.435 E.02431
G1 X110.769 Y177.029 E.02597
G1 X110.501 Y176.815 E.01276
G1 X110.008 Y176.372 E.02469
G1 X109.57 Y175.928 E.02323
G1 X109.098 Y175.366 E.02734
G1 X108.833 Y175.011 E.01651
G1 X108.435 Y174.407 E.02694
G1 X108.102 Y173.799 E.02582
G1 X107.907 Y173.391 E.01685
G1 X107.641 Y172.74 E.02619
G1 X107.429 Y172.07 E.02617
G1 X107.31 Y171.598 E.01812
G1 X107.212 Y171.103 E.01882
G1 X107.119 Y170.429 E.02532
G1 X107.083 Y169.937 E.0184
G1 X107.073 Y169.47 E.01738
G1 X107.099 Y168.782 E.02565
G1 X107.145 Y168.318 E.01735
G1 X107.261 Y167.609 E.02679
G1 X107.421 Y166.94 E.02561
G1 X107.557 Y166.492 E.01743
G1 X107.81 Y165.816 E.02692
G1 X108.001 Y165.389 E.01741
G1 X108.322 Y164.775 E.02578
G1 X108.615 Y164.297 E.0209
G1 X108.999 Y163.746 E.02499
G1 X109.403 Y163.252 E.02379
G1 X110.091 Y162.538 E.03692
G1 X110.154 Y162.403 E.00555
G1 X110.079 Y162.21 E.00773
G1 X109.641 Y161.818 E.02188
G1 X109.129 Y161.29 E.02739
G1 X108.732 Y160.818 E.02297
G1 X108.338 Y160.284 E.02471
G1 X108.216 Y160.199 E.00555
G1 X108.039 Y160.222 E.00663
G1 X107.27 Y160.532 E.0309
G1 X106.499 Y160.705 E.02941
G1 X105.946 Y160.75 E.02068
G1 X103.99 Y160.767 E.07284
G1 X102.014 Y160.755 E.07361
G1 X101.243 Y160.706 E.02878
G1 X100.521 Y160.548 E.02751
G1 X99.703 Y160.228 E.03271
G1 X99.554 Y160.222 E.00555
G1 X99.436 Y160.305 E.00539
G1 X99.006 Y160.89 E.02703
G1 X98.513 Y161.461 E.02811
G1 X97.991 Y161.977 E.02734
G1 X97.536 Y162.37 E.02239
G1 X97.461 Y162.499 E.00555
G1 X97.517 Y162.698 E.00772
G1 X98.157 Y163.389 E.03508
G1 X98.571 Y163.914 E.02489
G1 X99.09 Y164.711 E.03542
G1 X99.432 Y165.354 E.02714
G1 X99.8 Y166.221 E.03508
G1 X100.014 Y166.875 E.02562
G1 X100.228 Y167.789 E.03498
G1 X100.331 Y168.497 E.02664
G1 X100.384 Y169.433 E.03492
G1 X100.365 Y170.118 E.02553
G1 X100.281 Y170.911 E.02969
G1 X100.105 Y171.793 E.0335
G1 X99.975 Y172.266 E.01825
G1 X99.657 Y173.158 E.03528
G1 X99.369 Y173.793 E.02597
G1 X98.92 Y174.587 E.034
G1 X98.346 Y175.403 E.03715
G1 X97.826 Y176.005 E.02964
G1 X97.502 Y176.337 E.01726
G1 X96.898 Y176.876 E.03016
G1 X96.33 Y177.311 E.02663
G1 X95.711 Y177.706 E.02738
G1 X95.045 Y178.067 E.02821
G1 X94.43 Y178.34 E.02508
G1 X93.594 Y178.631 E.03295
G1 X92.843 Y178.823 E.02889
G1 X91.981 Y178.968 E.03253
G1 X91.31 Y179.02 E.02509
G1 X90.482 Y179.022 E.03084
G1 X89.788 Y178.969 E.02593
G1 X89.069 Y178.86 E.02708
G1 X88.409 Y178.709 E.02523
G1 X87.709 Y178.494 E.02726
G1 X87.076 Y178.247 E.0253
G1 X86.428 Y177.937 E.02677
G1 X85.668 Y177.488 E.03288
G1 X85.01 Y177.021 E.03005
G1 X84.274 Y176.384 E.03626
G1 X83.666 Y175.745 E.03285
G1 X83.123 Y175.054 E.03272
G1 X82.998 Y174.973 E.00555
G1 X82.919 Y174.968 E.00295
G1 X82.029 Y175.064 E.03333
G1 X81.121 Y175.076 E.03382
G1 X80.184 Y174.997 E.03504
G1 X79.426 Y174.862 E.02868
G1 X78.567 Y174.634 E.03312
G1 X77.892 Y174.39 E.02673
G1 X77.039 Y173.995 E.03498
G1 X76.445 Y173.656