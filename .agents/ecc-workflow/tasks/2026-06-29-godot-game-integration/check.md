# Check

## Verification

- `godot --headless --path godot --script res://tests/character_sprite_pack_game_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json`
- `uv run pytest tests/test_godot_character_sprite_game_integration.py -q`
- `uv run pytest tests/test_godot_character_sprite_game_integration.py tests/test_godot_nun_sprite_pack_quality.py tests/test_godot_character_sprite_pack.py -q`
- `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --require-production-ready`
- `godot --headless --path godot --quit`
- `uv run pytest`
- `git diff --check`

## Result

- Game player runner: passed.
- Observed gameplay actions: `idle`, `walk`, `run`, `jump`, `attack_sword_light`, `hurt`.
- Active nun pack loaded as `production_ready`.
- Collision shape was populated from runtime metadata.
- Focused Godot/Python tests: `5 passed`.
- Full test suite: `198 passed, 1 warning`.

