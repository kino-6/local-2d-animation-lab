# Run Action

- status: `production_ready`
- production_ready: `True`
- source: `imagegen_run_8frame_20260614_rough`
- method: `route_a_generated_run_rough_cleanup`
- frame_count: `8`
- phase_names: `['right_contact', 'right_down', 'flight_forward', 'left_reach', 'left_contact', 'left_down', 'flight_backward', 'right_reach']`
- contact_ground_y_range: `26`
- airborne_lift_detected: `True`
- alpha_edge_touch_frames: `[]`

This is an accepted run cycle packaged under the same identity contract. It adds run-specific
contact/down/flight/reach timing without introducing a new model backend.
