# Check

## Verification

- `uv run pytest tests/test_scale_and_densify_sprite_pack.py tests/test_preview_animation_exports.py -q`
  - Passed: 2 tests.
- `uv run pytest tests/test_scale_and_densify_sprite_pack.py tests/test_preview_animation_exports.py tests/test_visual_asset_gate.py -q`
  - Passed: 11 tests.
- Generated candidate manifest inspection:
  - All action frames are 1024x1024.
  - Frame counts are `walk=16`, `idle=8`, `run=16`, `jump=23`, `hurt=15`,
    `attack_sword_light=21`.
  - Full-resolution all-actions review sheet exists.
  - Per-action WebP previews exist.
- `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate/pack_review/visual_gate_report.json`
  - Completed.
  - Decision: `needs_retake_or_manual_review`.
  - Blocking actions: `walk`, `idle`, `run`, `jump`, `hurt`, `attack_sword_light`.
  - Main inherited blockers include foreground highlight clipping, width/scale jitter, run center jitter,
    jump recovery risk, and hurt detached fragment/center jitter.
- `godot --headless --path godot --script res://tests/character_sprite_pack_game_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate/manifest.json`
  - Expected rejection: `pack is not production_ready`.

## Final Production Candidate

- Final candidate:
  `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/manifest.json`
- Final frame counts:
  - `walk=16`
  - `idle=8`
  - `run=16`
  - `jump=23`
  - `hurt=15`
  - `attack_sword_light=21`
- Final visual gate:
  - Command:
    `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/pack_review/visual_gate_report.json --fail-on-review`
  - Result: `production_ready=true`, no blocking actions.
- Final focused tests:
  - Command:
    `uv run pytest tests/test_scale_and_densify_sprite_pack.py tests/test_preview_animation_exports.py tests/test_visual_asset_gate.py tests/test_visual_trauma_corpus.py -q`
  - Result: 22 passed.
- Final Godot validation:
  - Command:
    `godot --headless --path godot --script res://tests/character_sprite_pack_game_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/manifest.json`
  - Result: `ok=true`, `production_ready=true`, observed all six actions.
- Manual image review:
  - Reviewed `pack_review/all_actions_contact_sheet_fullres.png`.
  - Reviewed `jump_fullres_contact_sheet.png` after removing blended double exposure from the recovery tail.
  - Reviewed `hurt_fullres_contact_sheet.png` after detached-fragment cleanup.
