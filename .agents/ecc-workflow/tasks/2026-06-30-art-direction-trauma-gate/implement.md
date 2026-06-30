# Implement

- Added art-direction trauma gates to `scripts/visual_asset_gate.py`.
- New blocking findings:
  - `missing_separated_weapon_or_effect_layer`
  - `identity_consistency_lock_missing`
  - `jump_character_scale_too_small`
  - `idle_too_static_or_low_effort`
  - `low_secondary_motion_or_hold_frame_reuse`
  - `secondary_cloth_motion_policy_missing`
- Added median bbox width/height and hold-frame ratio metrics.
- Compared jump bbox height and width against idle/walk standing references.
- Re-ran the gate against the current 1024 candidate.
- Synced `manifest.json`, `production_gate.json`, and showcase export to the new
  `production_ready=false` result.
