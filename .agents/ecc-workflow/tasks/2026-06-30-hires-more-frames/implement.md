# Implement

## Notes

- Source candidate:
  `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_wide_hires_hurt_recovery_aligned_candidate`
- Target candidate:
  `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate`
- Added `scripts/scale_and_densify_sprite_pack.py`.
  - Copies a sprite pack into a new candidate directory.
  - Resizes every frame to a requested canvas size.
  - Inserts deterministic in-between frames for loop and non-loop actions.
  - Scales runtime origins/collision data and hit-frame indexes.
  - Regenerates action spritesheets, GIF/WebP previews, contact sheets, full-resolution review sheets,
    manifest metadata, runtime manifest, and production gate metadata.
- Added `tests/test_scale_and_densify_sprite_pack.py` for the resize/densify path.

## Candidate

- Generated `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate`
  from the hurt recovery aligned candidate.
- Output frame size: 1024x1024 for every action.
- Output frame counts:
  - `walk`: 16
  - `idle`: 8
  - `run`: 16
  - `jump`: 23
  - `hurt`: 15
  - `attack_sword_light`: 21
- The candidate remains `production_ready=false` because deterministic scaling and blending improve
  reviewability and temporal density, but do not retake inherited visual defects such as clipping,
  scale jitter, and highlight clipping across the whole pack.

## Production Repair

- Added `scripts/repair_sprite_pack_candidate.py`.
  - Reuses the tone-repaired 1024 candidate as input.
  - Removes blended in-between ghosting by replacing generated `_to_` frames with clean hold frames.
  - Reduces foreground highlight clipping.
  - Removes detached `hurt` alpha fragments with largest-component cleanup.
  - Repairs the `jump` recovery tail with clean idle hold frames instead of blended double exposure.
- Updated `scripts/visual_asset_gate.py` so geometry thresholds scale with frame size for high-resolution
  packs instead of applying low-resolution absolute pixel limits to 1024 frames.
- Final production candidate:
  `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate`
