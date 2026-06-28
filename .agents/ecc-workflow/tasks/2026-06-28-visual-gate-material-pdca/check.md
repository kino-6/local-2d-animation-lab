# Check

## Scope Review

Implemented stricter material gates for the active adoptable sprite pack. The change stays within
the quality-gate/material-maintenance scope and does not add external workflow tooling.

## Verification

- `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/visual_gate_report.json --fail-on-review`
- `uv run pytest tests/test_visual_asset_gate.py tests/test_godot_nun_sprite_pack_quality.py`
- `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --require-production-ready`
- `uv run pytest`
- `godot --headless --path godot --quit`
- `git diff --check`

Result: active pack reports `production_ready` with no blocking actions under the stricter gate.

Additional PDCA:

- Added a stricter `hurt` right-edge silhouette outlier gate for frame-overlap artifacts such as
  `hurt01` containing a fragment from the next pose.
- Added a minor detached component ratio metric for small side fragments after trimming.
- Regenerated pack review contact sheets at a fixed pack-wide thumbnail scale so crouched `jump`
  frames are not visually enlarged by per-frame thumbnail scaling.
- Re-ran `uv run pytest`, `godot --headless --path godot --quit`, `git diff --check`, and strict
  Godot pack validation. Result remained `production_ready`.
- Added `hard_vertical_alpha_cut` after review found that trimming side artifacts caused unnatural
  vertical cuts in `hurt01` and `hurt02`. The active pack now correctly fails production readiness
  for `hurt` until those frames are regenerated or manually repaired.
- Updated Godot pack validation so `production_ready` is false when the visual gate report is not
  production-ready, even if the manifest still contains an older top-level true value.
- Retook the active `hurt` action instead of trimming it further. A direct re-slice from the
  original hurt sheet still reproduced side-panel/vertical-cut findings, so the adopted retake
  rebuilds the cut impact/recoil frames from clean in-pack silhouettes and regenerates the hurt
  spritesheet, preview, contact sheet, pack review, manifest visual gate, and production gate.
  Result: active pack is back to `production_ready`; `hurt` has no blocking visual findings.

Retake verification:

- `uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/visual_gate_report.json --fail-on-review`
- `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json --require-production-ready`
- `uv run pytest tests/test_visual_asset_gate.py tests/test_godot_nun_sprite_pack_quality.py tests/test_godot_character_sprite_pack.py`
- `uv run pytest`
- `godot --headless --path godot --quit`
- `git diff --check`

Retake result: all checks passed; `hurt` metrics now include `hard_vertical_alpha_cut_frames: []`,
`right_edge_silhouette_outlier_frames: []`, and no blocking findings.

## Risks

- Automated gates still cannot judge pose appeal or anatomy with the same nuance as human review.
- The active pack was rewritten from a generated fixed candidate, so many derived PNG/GIF/spritesheet
  files changed together.

## Follow-Ups

- Human contact-sheet review remains useful before external publication.
