# Production Review

- target: `production_walk_8frame_sideview`
- decision: `candidate_ready_for_manual_polish`
- production_ready: `False`

## Checks

- [x] no_alpha_edge_touch
- [x] stable_ground_line
- [x] stable_head_height
- [x] stable_body_height
- [x] root_motion_not_excessive
- [x] game_previews_exist

## Blocking Issues

- none

## Manual Polish Queue

- Human art review is required because this package uses an AI-generated rough candidate.
- Open the 128px and 192px previews in Aseprite or Godot and confirm the loop in motion.
- Clean remaining per-frame line jitter around hair tips, sleeves, skirt hem, socks, and shoes.
- Check shoe contact and foot shape in contact/down frames.
- Normalize tiny color/value differences across frames after manual edits.

## Production Rule

Do not mark this asset production-ready until a human accepts the loop at game size, frame-level
polish is completed, and a final production review explicitly flips `production_ready` to true.
