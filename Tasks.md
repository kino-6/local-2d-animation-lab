# Tasks: Lower-Body Sidecar Start-Reference Probe

Archived checkpoint:

```text
docs/archive/Tasks_20260614_start_reference_retake_localvl_completed.md
```

Cleanup report:

```text
docs/output_cleanup_20260614_start_reference_retake_localvl.md
```

## Rules

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet.
- [x] Save all new generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Keep `outputs/` free of loose files and stale diagnostic runs after durable findings are recorded.
- [x] Target adopted animation source length is 120 frames; short probes are evidence only.
- [x] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [x] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, shoe unreadability, front-view drift, model-sheet residue, composition collapse, or identity drift are visible.

## Current Interpretation

- [x] The current blocker is a walk-ready start reference, not Wan frame interpolation by itself.
- [x] Text-only prompt retakes improved side-view evidence but did not solve readable shoes, clear ankles, or lower-leg separation.
- [x] OpenPose alone is too sparse around feet for a reliable 2D game walk start frame.
- [x] LocalVL is useful as a secondary reviewer, but deterministic start-reference gates remain the adoption authority.
- [x] The next useful experiment is lower-body/foot structure injected during still start-reference generation, before animation spend.

## Plan

Primary route:

```text
design reference
-> OpenPose full-body side-view candidate
-> low-strength lower-body/foot sidecar ControlNet
-> deterministic start-frame gate
-> LocalVL secondary start-reference review
-> Agent visual review
-> animation probe only if candidate_ok + visually walk-ready
```

The sidecar must target only the start-reference still-generation stage. It is not a rig, puppet, or final animation method.

## Active PDCA

- [x] Archive the previous completed `Tasks.md`.
- [x] Write cleanup findings for the current local output runs.
- [x] Delete reviewed `outputs/` runs after path safety checks.
- [x] Add lower-body/foot sidecar support to `scripts/generate_fullbody_reference_candidates.py`.
  - Add CLI args for sidecar style, sidecar ControlNet, strength, start/end percent.
  - Generate a sidecar image under the timestamped run directory.
  - Chain the sidecar ControlNet after OpenPose when enabled.
  - Record sidecar settings and image paths in `reference_candidates_report.json`.
- [x] Add tests for sidecar workflow wiring and nonblank sidecar image generation.
- [x] Run focused tests for the touched generation script and output layout policy.
- [x] Run one fresh Anima start-reference generation with:
  - `novaOrangeXL_v120.safetensors`
  - `SDXL\OpenPoseXL2.safetensors`
  - low-strength lineart sidecar for lower-body/foot/contact guidance
  - queue wait controls enabled
  - progress visibility enabled
- [x] Run LocalVL start-reference review on the new contact sheet and selected start frame.
- [x] Agent visual review.
  - Decide one of:
    - `candidate_ok_for_short_probe`;
    - `blocked_start_reference_quality`;
    - `rejected_diagnostic`.
- [x] Optional short animation probe only if the selected start reference passes both deterministic gate and Agent visual review.
- [x] Update durable knowledge.
  - `docs/start_frame_first_walk_pdca.md`
  - `docs/local_vl_asset_evaluation_pdca.md`
  - `docs/reference_lock_motion_template_deep_dive.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
  - `Tasks.md`

## Success Criteria

- [x] Old output clutter is removed after knowledge capture.
- [x] Tests pass for touched code.
- [x] Fresh sidecar-guided start-reference generation exists, or queue/model blocker is recorded.
- [x] LocalVL start-reference review exists, or Ollama blocker is recorded.
- [x] No animation generation is run from an obviously bad start reference.
- [x] Result is labeled honestly as one of:
  - `candidate_ok_for_short_probe`;
  - `blocked_start_reference_quality`;
  - `blocked_local_vl_unavailable`;
  - `blocked_comfyui_or_model_unavailable`;
  - `rejected_diagnostic`;
  - `selected_proof_only`.

## Result

- [x] Planning and cleanup commit:
  - `88cb1f8 Plan lower-body sidecar start reference probe`
- [x] Implemented lower-body/foot lineart sidecar support in:
  - `scripts/generate_fullbody_reference_candidates.py`
- [x] Added tests in:
  - `tests/test_fullbody_reference_candidates_script.py`
- [x] Tests:
  - `uv run pytest tests\test_fullbody_reference_candidates_script.py tests\test_output_layout_policy.py tests\test_start_frame_quality.py`
  - `19 passed`
- [x] Fresh start-reference run:
  - `outputs/20260614_005144/fullbody_reference/anima_00013/`
  - selected: `small_stride_side_walk_sprite`
  - selected status: `candidate_ok`
  - `animation_probe_allowed: true`
- [x] LocalVL start-reference review:
  - `outputs/20260614_010050/local_vl_eval/anima_sidecar_start_reference_vl/start_reference_vl_eval.json`
  - `is_walk_ready_start_reference: true`
- [x] Found and fixed double-clean boundary:
  - cleaned selected preview can fail pre-Wan gate with `shoes_unreadable`;
  - generator now records `animation_probe_start_image`;
  - Wan probes should normalize from the source exactly once.
- [x] Short animation probe:
  - `outputs/20260614_010251/wan_walk_i2v/anima_sidecar_source_start_probe_i2v_len17/`
  - motion reads as walk but is not adoption-ready.
- [x] Standard quality flow:
  - `outputs/20260614_010359/sprite_asset_quality_flow/anima_sidecar_probe_quality/`
  - final status: `rejected_animation_candidate`
  - motion readability: `passed`
  - artifact gate: `rejected`
  - blockers: lower-body afterimages, leg recoloring/darkening, foot/contact smears, duplicate-silhouette risk.
- [x] Durable report:
  - `docs/lower_body_sidecar_start_reference_pdca_20260614.md`
- [x] Decision:
  - `rejected_diagnostic`

## Next Action

- [x] Do not promote this probe to 120 frames.
- [x] Continue from the improved sidecar start-reference, but focus the next loop on preserving it through video generation:
  - source normalization exactly once;
  - Wan setting comparison using this better start image;
  - BiRefNet foreground separation after this new source;
  - conservative histogram correction only after artifact gate improves;
  - artifact gate remains authoritative over LocalVL.
