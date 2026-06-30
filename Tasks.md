# Tasks: Production-Ready 1024 Sprite Pack

Active branch:

```text
codex/hires-more-frames-sprite-pack
```

Current review candidate:

```text
outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate/manifest.json
```

Current production-ready candidate:

```text
outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/manifest.json
```

Previous root task board archived to:

```text
docs/archive/Tasks_20260614_conservative_walk_endpoint_gate_completed.md
```

## Inventory

- [x] Root `Tasks.md` was still the completed 2026-06-14 conservative walk endpoint task.
- [x] Structured task folders already exist under `.agents/ecc-workflow/tasks/`.
- [x] The latest high-resolution/frame-doubled task is recorded at:
  - `.agents/ecc-workflow/tasks/2026-06-30-hires-more-frames/`
- [x] Earlier relevant completed work:
  - `2026-06-28-nun-pack-quality-pdca`: active pack reached `production_ready`.
  - `2026-06-28-visual-gate-material-pdca`: hurt overlap/cut and review scaling gates were added.
  - `2026-06-28-visual-trauma-corpus`: historical failures were captured.
  - `2026-06-28-motion-diff-gate`: adjacent-frame and idle recovery checks were added.
  - `2026-06-29-highlight-clipping-fix`: highlight clipping became a blocking gate.
  - `2026-06-29-godot-game-integration`: production-ready packs load in Godot.
  - `2026-06-30-hires-more-frames`: 1024x1024 candidate and denser playback were created.
  - `2026-06-30-art-direction-trauma-gate`: object separation, identity consistency,
    jump scale, idle effort, and secondary cloth motion became blocking gates.
- [x] The first 1024 candidate was not production-ready.
- [x] A repaired 1024 candidate passed the earlier numeric visual gate and Godot validation.
- [x] The same candidate is now reclassified as not production-ready by the stricter
  art-direction trauma gate.
- [x] Blended in-between ghosting was found during contact-sheet review and removed by replacing
  generated blend frames with clean hold/recovery frames.

## Current Gate State

Visual gate result:

```text
decision: needs_retake_or_manual_review
production_ready: false
blocking_actions: walk, idle, run, jump, hurt, attack_sword_light
```

Action blockers:

- [x] `walk`
  - `low_secondary_motion_or_hold_frame_reuse`
  - `identity_consistency_lock_missing`
  - `secondary_cloth_motion_policy_missing`
- [x] `idle`
  - `idle_too_static_or_low_effort`
  - `identity_consistency_lock_missing`
  - `secondary_cloth_motion_policy_missing`
- [x] `run`
  - `low_secondary_motion_or_hold_frame_reuse`
  - `identity_consistency_lock_missing`
  - `secondary_cloth_motion_policy_missing`
- [x] `jump`
  - `low_secondary_motion_or_hold_frame_reuse`
  - `jump_character_scale_too_small`
  - `identity_consistency_lock_missing`
  - `secondary_cloth_motion_policy_missing`
- [x] `hurt`
  - `low_secondary_motion_or_hold_frame_reuse`
  - `identity_consistency_lock_missing`
  - `secondary_cloth_motion_policy_missing`
- [x] `attack_sword_light`
  - `low_secondary_motion_or_hold_frame_reuse`
  - `missing_separated_weapon_or_effect_layer`
  - `identity_consistency_lock_missing`
  - `secondary_cloth_motion_policy_missing`

## Production-Ready Definition

- [ ] Candidate manifest has `production_ready=true`.
- [ ] `visual_asset_gate.py` reports:
  - `decision: production_ready`
  - `production_ready: true`
  - no blocking actions
- [x] Every action has stable 1024x1024 transparent frames.
- [x] Frame counts remain at least:
  - `walk >= 16`
  - `idle >= 8`
  - `run >= 16`
  - `jump >= 23`
  - `hurt >= 15`
  - `attack_sword_light >= 21`
- [ ] Preview GIF/WebP playback is not flagged by deterministic art-direction and motion gates.
- [x] Godot headless pack runner accepts the manifest.
- [x] Human review contact sheets and GIF/WebP previews were regenerated for the final candidate.

## Plan

### Phase 0: Baseline Lock

- [x] Save the current 1024 candidate as the baseline under `pack_review/`.
- [x] Record current gate metrics per action before any repair.
- [x] Add a compact compare report format for before/after blocker deltas.
- [x] Confirm no active production pack is overwritten during repair.

Exit criteria:

- [x] Current failing metrics can be reproduced from one command.

### Phase 1: Global Tone Repair

Goal: remove foreground highlight clipping across all actions before per-action retakes.

- [x] Add or reuse a foreground-only tone-normalization step for high-resolution packs.
- [x] Apply tone repair to every 1024 frame.
- [x] Regenerate spritesheets, GIF/WebP previews, contact sheets, and manifest metadata.
- [x] Re-run visual gate.
- [x] Visually review GIFs through deterministic highlight metrics.

Exit criteria:

- [x] `foreground_highlight_clipping` is gone for `idle`.
- [x] Highlight clipping is gone for all other actions in the final gate report.
- [x] No new edge-touch, cut, or detached-fragment blocker is introduced.

### Phase 2: Motion Geometry Repair

Goal: fix scale and center jitter without reducing the 1024 canvas or losing pixels.

- [x] Add a pack-wide geometry stabilizer for bbox scale, center, and ground alignment.
- [x] Treat high-resolution geometry thresholds as canvas-scaled rather than fixed low-res pixels.
- [x] Repair `walk` width jitter finding.
- [x] Repair `run` width, height, and horizontal center jitter findings.
- [x] Repair `hurt` width and horizontal center jitter findings.
- [x] Repair `attack_sword_light` width and height jitter findings while preserving sword reach.
- [x] Rebuild sheets and previews after repair.
- [x] Re-run visual gate after repair.

Exit criteria:

- [x] `large_width_or_scale_jitter` is gone for `walk`, `run`, `hurt`, and `attack_sword_light`.
- [x] `large_height_or_scale_jitter` is gone for `run` and `attack_sword_light`.
- [x] `large_horizontal_center_jitter` is gone for `run` and `hurt`.

### Phase 3: Hurt Retake Or Clean Reconstruction

Goal: remove detached fragments and keep the recovery readable.

- [x] Inspect `hurt` full-resolution frames and GIF/WebP.
- [x] Decide whether deterministic repair is enough or a targeted retake is required.
- [x] If deterministic repair:
  - remove detached side fragments from alpha components;
  - stabilize bbox/center;
  - preserve the final recovery pose near idle.
- [x] Retake was not required after deterministic repair passed; if future retake is needed:
  - generate or reconstruct only the failing hurt frames;
  - avoid side-panel overlap and hard vertical cuts;
  - match pack identity, scale, palette, and 1024 canvas.
- [x] Re-run trauma corpus cases for hurt overlap and hard vertical cut.

Exit criteria:

- [x] `minor_detached_side_fragment` is gone for `hurt`.
- [x] Hurt still has at least 15 playback frames.
- [x] Hurt recovery passes the idle recovery gate.

### Phase 4: Jump Recovery Repair

Goal: make the jump action recover to idle without flattening the jump arc.

- [x] Inspect `jump` last frames against idle using image diff and GIF playback.
- [x] Repair or retake the landing/recovery tail frames only.
- [x] Preserve jump arc, canvas size, and frame count.
- [x] Re-run recovery-to-idle gate.

Exit criteria:

- [x] `poor_recovery_to_idle_pose` is gone for `jump`.
- [x] Jump still preserves non-tail jump arc frames and 23-frame playback.

### Phase 5: In-Between Quality Review

Goal: ensure denser frames are useful animation frames, not visible blend ghosts.

- [x] Add a repair report for before/after action deltas.
- [x] Generate per-action GIF/WebP at actual playback timing.
- [x] Check adjacent ImageDiff through `step_delta_outlier_frames`.
- [x] Retake or reconstruct any in-between that is flagged by deterministic gates.

Exit criteria:

- [x] Blended in-between frames were deghosted into clean hold/recovery frames.
- [x] No inserted frame is flagged as an abrupt or isolated motion outlier.
- [x] Adjacent-frame deltas are smooth enough for the current deterministic gate.

### Phase 6: Production Manifest And Godot Validation

- [x] Re-run full visual gate against the repaired candidate.
- [x] Set manifest and production gate to `production_ready=true` only after the gate passes.
- [x] Run focused Python tests.
- [x] Run Godot headless pack runner.
- [x] Review:
  - `pack_review/all_actions_contact_sheet_fullres.png`
  - per-action full-resolution sheets;
  - per-action GIF/WebP previews.

Exit criteria:

- [x] Visual gate passes with no blocking actions.
- [x] Godot accepts the manifest.
- [x] Final candidate path is recorded here.

Note: Phase 6 records the earlier numeric gate state. Phase 7 supersedes it with
new human-review-derived art-direction blockers.

### Phase 7: Art Direction Trauma Gate

- [x] Add historical failure cases for:
  - sword/effect object separation missing;
  - identity lock missing across actions;
  - jump character scale too small;
  - idle being too static or low effort;
  - excessive hold-frame reuse / weak secondary motion;
  - missing cloth or hair secondary-motion policy.
- [x] Make these cases deterministic blockers in `visual_asset_gate.py`.
- [x] Re-run the gate against the current 1024 candidate.
- [x] Sync `manifest.json`, `production_gate.json`, and showcase export to `production_ready=false`.

Exit criteria:

- [x] The current candidate is no longer labeled production-ready under the stricter gate.
- [x] `jump_character_scale_too_small` is detected on the current candidate.
- [x] Tests cover all newly added trauma cases.

Final candidate:

```text
outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/manifest.json
```

Final checks:

```text
uv run pytest tests/test_visual_trauma_corpus.py tests/test_visual_asset_gate.py tests/test_export_sprite_pack_showcase.py -q
27 passed

uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/pack_review/visual_gate_report.json
decision: needs_retake_or_manual_review
production_ready: false
blocking_actions: walk, idle, run, jump, hurt, attack_sword_light

godot --headless --path godot --script res://tests/character_sprite_pack_game_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_production_candidate/manifest.json
ok: true
production_ready: false
```

## Commands

Baseline gate:

```powershell
uv run python scripts/visual_asset_gate.py --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate/manifest.json --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate/pack_review/visual_gate_report.json
```

Focused tests:

```powershell
uv run pytest tests/test_scale_and_densify_sprite_pack.py tests/test_preview_animation_exports.py tests/test_visual_asset_gate.py -q
```

Godot validation:

```powershell
godot --headless --path godot --script res://tests/character_sprite_pack_game_runner.gd -- --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack_1024_doubled_candidate/manifest.json
```

## Non-Goals

- [x] Do not overwrite the active production pack until the repaired 1024 candidate passes.
- [x] Do not mark `production_ready=true` by bypassing gate findings.
- [x] Do not reduce the 1024 canvas just to hide defects.
- [x] Do not restart broad video or 120-frame research paths for this maintenance task.
