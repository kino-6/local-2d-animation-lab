# Check

## Automated

```text
uv run pytest tests/test_visual_trauma_corpus.py tests/test_visual_asset_gate.py tests/test_export_sprite_pack_showcase.py -q
27 passed
```

## Current Candidate Gate

```text
uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/pack_review/visual_gate_report.json
decision: needs_retake_or_manual_review
production_ready: false
blocking_actions: walk, idle, run, jump, hurt, attack_sword_light
```

Key findings:

- `attack_sword_light`: `missing_separated_weapon_or_effect_layer`
- all actions: `identity_consistency_lock_missing`
- `jump`: `jump_character_scale_too_small`
- `idle`: `idle_too_static_or_low_effort`
- non-idle actions: `low_secondary_motion_or_hold_frame_reuse`
- all actions: `secondary_cloth_motion_policy_missing`

## Showcase

```text
outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/export/game_ready_showcase/index.html
production_ready: false
```
