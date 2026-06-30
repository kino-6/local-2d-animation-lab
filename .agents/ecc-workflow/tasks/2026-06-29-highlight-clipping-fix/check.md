# Check

## Verification

- `uv run pytest tests/test_visual_asset_gate.py -q`
- `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/visual_gate_report.json --fail-on-review`
- `uv run pytest tests/test_visual_asset_gate.py tests/test_visual_trauma_corpus.py tests/test_godot_nun_sprite_pack_quality.py tests/test_godot_character_sprite_game_integration.py -q`
- `uv run pytest tests/test_preview_animation_exports.py tests/test_visual_asset_gate.py tests/test_visual_trauma_corpus.py tests/test_godot_nun_sprite_pack_quality.py tests/test_godot_character_sprite_game_integration.py -q`
- `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_hires_retake_candidate_tone_fixed/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_hires_retake_candidate_tone_fixed/pack_review/visual_gate_report.json`
- `godot --headless --path godot --script res://tests/character_sprite_pack_game_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_hires_retake_candidate_tone_fixed/manifest.json`
- `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --require-production-ready`
- `godot --headless --path godot --script res://tests/character_sprite_pack_game_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json`
- `uv run pytest`
- `godot --headless --path godot --quit`
- `git diff --check`

## Result

- Active pack visual gate: `production_ready`.
- Blocking actions: none.
- Active GIF foreground highlight ratio: `>=240` is `0.0` for all actions.
- Focused tests: `23 passed`.
- Focused tests after WebP/high-resolution review additions: `24 passed`.
- High-resolution tone-fixed candidate visual gate: `needs_retake_or_manual_review`.
- High-resolution tone-fixed candidate blocking actions: walk, run, jump, hurt, attack_sword_light.
- High-resolution tone-fixed candidate remaining decisive defects:
  - `hurt`: hard vertical alpha cut in frames 1 and 2, poor recovery to idle pose.
  - `jump`: poor recovery to idle pose.
  - walk/run/attack: scale/height jitter remains for review.
- High-resolution tone-fixed candidate is intentionally rejected by the Godot game runner because
  its manifest is not `production_ready`.
- Full test suite: `200 passed, 1 warning`.
- Godot pack E2E and game-player E2E: passed.
