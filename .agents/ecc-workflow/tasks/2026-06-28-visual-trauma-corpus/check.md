# Check

## Scope Review

Implemented the requested root-cause-oriented guardrails without adding external tooling or
changing the pack generation route. The change turns known visual failures into a single regression
corpus and prevents auto-fix from adopting candidates that add new blocking findings.

## Trauma Corpus Coverage

- `jump_scale_outlier`
- `hurt_side_panel_overlap`
- `hurt_hard_vertical_cut`
- `green_cyan_alpha_edge_fringe`
- `weak_weapon_readability`
- `action_style_drift`

Additional safety case:

- `auto_fix_keeps_original_when_candidate_adds_new_trauma`

## Verification

- `uv run pytest tests/test_visual_trauma_corpus.py -q`
- `uv run pytest tests/test_visual_asset_gate.py tests/test_visual_trauma_corpus.py tests/test_godot_nun_sprite_pack_quality.py tests/test_godot_character_sprite_pack.py`
- `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/visual_gate_report.json --fail-on-review`
- `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --require-production-ready`
- `uv run pytest`
- `godot --headless --path godot --quit`
- `git diff --check`

Result: all checks passed. Full pytest result: `192 passed, 1 warning`.
