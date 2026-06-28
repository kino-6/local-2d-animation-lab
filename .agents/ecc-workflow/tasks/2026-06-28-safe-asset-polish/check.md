# Check

## Result

Adopted the safe auto-fix candidate into the active nun sprite pack. The contact sheet remains
visually stable, while material metrics improved:

- `hurt.border_green_cyan_fringe_ratio_max`: `0.0518` -> `0.0`
- `idle.saturation_range`: `0.0336` -> `0.0091`
- `run.saturation_range`: `0.0338` -> `0.0108`
- `jump.saturation_range`: `0.0453` -> `0.0121`
- `attack_sword_light.saturation_range`: `0.0414` -> `0.0074`

Rejected manual blade-highlight candidates because they made some attack frames read as duplicate
blade lines.

## Verification

- `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/visual_gate_report.json --fail-on-review`
- `uv run pytest tests/test_visual_asset_gate.py tests/test_visual_trauma_corpus.py tests/test_godot_nun_sprite_pack_quality.py tests/test_godot_character_sprite_pack.py`
- `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --require-production-ready`
- `uv run pytest`
- `godot --headless --path godot --quit`
- `git diff --check`

Result: all checks passed. Full pytest result: `192 passed, 1 warning`.
