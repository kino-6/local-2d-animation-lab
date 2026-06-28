# Implementation

## Plan

1. Add metrics for border chroma fringe, weapon readability, and pack style consistency.
2. Extend auto-fix to desaturate green/cyan alpha-edge noise and normalize pack-level color.
3. Adopt the fixed candidate only if the stricter gate passes.
4. Update tests and rerun focused/full validation.

## Decisions

- Treat high green/cyan boundary color as a production blocker because it is visible against light
  backgrounds and weakens sprite polish.
- Require a readable elongated blade cue for `attack_sword_light` while avoiding hard-coded pixel
  positions.
- Compare each action to the pack's walk/idle style baseline for brightness and saturation drift.

## Files

- `scripts/visual_asset_gate.py`
- `tests/test_visual_asset_gate.py`
- `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/`
