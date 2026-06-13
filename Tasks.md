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

- [ ] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [ ] Treat the input image as a design reference, not pixels to directly puppet.
- [ ] Save all new generated run artifacts only under `outputs/<timestamp>/...`.
- [ ] Keep `outputs/` free of loose files and stale diagnostic runs after durable findings are recorded.
- [ ] Target adopted animation source length is 120 frames; short probes are evidence only.
- [ ] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [ ] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, shoe unreadability, front-view drift, model-sheet residue, composition collapse, or identity drift are visible.

## Current Interpretation

- [ ] The current blocker is a walk-ready start reference, not Wan frame interpolation by itself.
- [ ] Text-only prompt retakes improved side-view evidence but did not solve readable shoes, clear ankles, or lower-leg separation.
- [ ] OpenPose alone is too sparse around feet for a reliable 2D game walk start frame.
- [ ] LocalVL is useful as a secondary reviewer, but deterministic start-reference gates remain the adoption authority.
- [ ] The next useful experiment is lower-body/foot structure injected during still start-reference generation, before animation spend.

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

- [ ] Archive the previous completed `Tasks.md`.
- [ ] Write cleanup findings for the current local output runs.
- [ ] Delete reviewed `outputs/` runs after path safety checks.
- [ ] Add lower-body/foot sidecar support to `scripts/generate_fullbody_reference_candidates.py`.
  - Add CLI args for sidecar style, sidecar ControlNet, strength, start/end percent.
  - Generate a sidecar image under the timestamped run directory.
  - Chain the sidecar ControlNet after OpenPose when enabled.
  - Record sidecar settings and image paths in `reference_candidates_report.json`.
- [ ] Add tests for sidecar workflow wiring and nonblank sidecar image generation.
- [ ] Run focused tests for the touched generation script and output layout policy.
- [ ] Run one fresh Anima start-reference generation with:
  - `novaOrangeXL_v120.safetensors`
  - `SDXL\OpenPoseXL2.safetensors`
  - low-strength lineart sidecar for lower-body/foot/contact guidance
  - queue wait controls enabled
  - progress visibility enabled
- [ ] Run LocalVL start-reference review on the new contact sheet and selected start frame.
- [ ] Agent visual review.
  - Decide one of:
    - `candidate_ok_for_short_probe`;
    - `blocked_start_reference_quality`;
    - `rejected_diagnostic`.
- [ ] Optional short animation probe only if the selected start reference passes both deterministic gate and Agent visual review.
- [ ] Update durable knowledge.
  - `docs/start_frame_first_walk_pdca.md`
  - `docs/local_vl_asset_evaluation_pdca.md`
  - `docs/reference_lock_motion_template_deep_dive.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
  - `Tasks.md`

## Success Criteria

- [ ] Old output clutter is removed after knowledge capture.
- [ ] Tests pass for touched code.
- [ ] Fresh sidecar-guided start-reference generation exists, or queue/model blocker is recorded.
- [ ] LocalVL start-reference review exists, or Ollama blocker is recorded.
- [ ] No animation generation is run from an obviously bad start reference.
- [ ] Result is labeled honestly as one of:
  - `candidate_ok_for_short_probe`;
  - `blocked_start_reference_quality`;
  - `blocked_local_vl_unavailable`;
  - `blocked_comfyui_or_model_unavailable`;
  - `rejected_diagnostic`;
  - `selected_proof_only`.
