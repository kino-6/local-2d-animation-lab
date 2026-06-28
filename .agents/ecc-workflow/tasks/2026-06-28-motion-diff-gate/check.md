# Check

## Verification

- `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/visual_gate_report.json --fail-on-review`
- `uv run pytest tests/test_visual_asset_gate.py tests/test_visual_trauma_corpus.py tests/test_godot_nun_sprite_pack_quality.py -q`
- `uv run pytest tests/test_visual_asset_gate.py tests/test_visual_trauma_corpus.py tests/test_godot_nun_sprite_pack_quality.py tests/test_godot_character_sprite_pack.py -q`
- `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --require-production-ready`
- `uv run pytest`
- `godot --headless --path godot --quit`
- `git diff --check`

## Result

- Active pack visual gate: `production_ready`.
- Blocking actions: none.
- Focused tests: `21 passed`.
- Full tests: `197 passed, 1 warning`.
- Godot pack E2E: passed with `production_ready: true`.

