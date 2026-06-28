# Implementation

## Plan

1. Measure the current active pack with the existing visual gate and Godot runner.
2. Separate real asset defects from action-expected movement.
3. Apply the smallest safe material and gate changes.
4. Re-run visual, Godot, and Python checks.

## Decisions

- Treat edge-touching frames as real material defects and fix them by keeping foreground pixels
  inside the frame canvas.
- Do not block `jump` or `hurt` for large height variation, because the vertical arc and impact
  squash are expected animation behavior.
- Do not block `jump` or `hurt` for temporary upper-body hand cue dropout, because those actions
  can legitimately occlude hands or change silhouette.
- Keep upper-body hand cue dropout as a hard blocker for locomotion-style actions where the body
  should stay consistently readable.

## Files

- `scripts/visual_asset_gate.py`
- `tests/test_visual_asset_gate.py`
- `tests/test_godot_nun_sprite_pack_quality.py`
- `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/`
