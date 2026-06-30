# Implement

## Changes

- Added foreground luminance clipping metrics to `scripts/visual_asset_gate.py`.
- Added `foreground_highlight_clipping` as a blocking visual finding.
- Added a conservative tone-map in auto-fix to soften channel extremes:
  - high channels are shoulder-compressed instead of staying pinned to 255;
  - very dark channels are slightly lifted to reduce black crush.
- Changed GIF preview flattening from near-white to neutral gray so white hair remains reviewable.
- Reprocessed the active nun sprite pack and regenerated previews, sheets, and the visual gate
  report.
- Added regression coverage in:
  - `tests/test_visual_asset_gate.py`
  - `tests/test_visual_trauma_corpus.py`

## Follow-up PDCA on Perceived Quality

- Built a non-destructive high-resolution review candidate from the original action sheets:
  - `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_hires_retake_candidate`
  - frame size: 512x768
  - review contact sheet thumbnails: 300x420
- Added optional animated WebP previews so review can separate GIF palette loss from source-art
  quality:
  - `preview.gif` remains available for compatibility;
  - `preview.webp` is generated as a lossless higher-fidelity review animation.
- Scaled runtime collision boxes when building non-256x384 packs.
- Produced a tone-fixed high-resolution candidate:
  - `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_hires_retake_candidate_tone_fixed`
- Result: white clipping and green/cyan edge fringe are reduced, but the high-resolution candidate
  still fails visual gate because `hurt` has a hard vertical alpha cut and jump/hurt recovery poses
  remain unsuitable. Treat this candidate as retake evidence, not as a production replacement.
