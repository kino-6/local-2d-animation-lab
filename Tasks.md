# Tasks: Lower-Body Sidecar Control Probe

Archived checkpoint:
`docs/archive/Tasks_20260613_foot_contact_reference_locked_probe_completed.md`

Detailed evidence:

- `docs/reference_lock_motion_template_deep_dive.md`
- `docs/reference_conditioned_regen_pdca.md`
- `docs/walk_candidate_comparison.md`
- `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`

## Rules

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet.
- [x] Save generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Target adopted source length is 120 frames; short probes are evidence only.
- [x] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [x] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, or identity drift are visible.

## Current State

- [x] Best previous reference-locked proof remains:
  - `outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/`
  - Status: `selected_proof_only`.
- [x] Foot-contact v3 source is a better template, but did not improve generation through OpenPose-only:
  - generated output: `outputs/20260613_223902/reference_pose_regen/walk_ipadv_upper_mask_foot_contact_v3_8f/`
  - decision: `rejected_diagnostic`
  - artifact hard failures: `3/8`
  - region retake decisions: `2/8`
  - span motion: `8.918`
- [x] Local ControlNet models currently available:
  - `SDXL\OpenPoseXL2.safetensors`
  - `SDXL\t2i-adapter-openpose-sdxl-1.0.safetensors`
  - `SD1.5\t2iadapter_openpose_sd14v1.pth`
- [x] Local lineart/softedge/depth SDXL ControlNet was not found in the current ComfyUI model directory.

## Plan

The next mechanism test is not more OpenPose geometry. It is a two-control diagnostic:

```text
main OpenPose control = whole body phase and pose
lower_body_sidecar control = separate foot/contact/lower-body constraint candidate
IPAdapterAdvanced upper_body mask = identity lock
```

This is still diagnostic. Since the local second ControlNet choices are OpenPose-family models, it may not understand the sidecar perfectly. The purpose is to determine whether a separate sidecar channel helps at all before downloading or installing a more suitable lineart/softedge/depth model.

## Active PDCA

- [ ] Add optional secondary ControlNet support to `scripts/regenerate_pose_sequence_controlnet.py`.
  - Inputs:
    - `--sidecar-dir`
    - `--sidecar-indices`
    - `--sidecar-controlnet`
    - `--sidecar-strength`
    - `--sidecar-start`
    - `--sidecar-end`
  - Chain the second `ControlNetApplyAdvanced` after the main OpenPose apply.
  - Keep the baseline path unchanged when no sidecar is provided.
  - Record sidecar settings and copied sidecar frames in the run report.
- [ ] Add unit tests for the secondary ControlNet workflow.
  - Baseline workflow must remain unchanged without sidecar args.
  - Sidecar workflow must load a second control image and apply a second ControlNet before KSampler.
- [ ] Confirm ComfyUI queue capacity before generation.
  - Use `/queue`.
  - Do not submit if pending/running queue is above the configured limit.
- [ ] Run one 8-frame sidecar diagnostic probe.
  - Source image:
    - `outputs/20260613_185524/background_normalize/prior_best_start_background_normalize/frames/frame_000.png`
  - Main pose:
    - `outputs/20260613_222505/motion_source_video_pdca/motion_sources/sideview_walk_foot_contact_v3/controlnet`
  - Sidecar:
    - `outputs/20260613_222505/motion_source_video_pdca/motion_sources/sideview_walk_foot_contact_v3/lower_body_sidecar`
  - Pose/sidecar indices:
    - `0,15,30,45,60,75,90,105`
  - Reference settings:
    - checkpoint `novaOrangeXL_v120.safetensors`
    - main ControlNet `SDXL\OpenPoseXL2.safetensors`
    - sidecar ControlNet `SDXL\t2i-adapter-openpose-sdxl-1.0.safetensors`
    - denoise `0.78`
    - main ControlNet strength `0.92`
    - main ControlNet end `0.68`
    - sidecar strength start point `0.35`
    - sidecar end start point `0.55`
    - IPAdapter mode `advanced`
    - IPAdapter weight type `style transfer precise`
    - IPAdapter weight `0.55`
    - IPAdapter end `0.62`
    - IPAdapter attention mask `upper_body`
- [ ] Gate the sidecar probe.
  - `repair_frame_artifacts.py --mask-only --weapon none`
  - `select_best_span.py --action walk --motion-metric foreground --allow-hard-failures`
  - `analyze_sprite_regions.py`
  - Agent visual review of comparison/contact sheets.
- [ ] Compare against both prior proofs.
  - Previous best:
    - `outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/`
  - Foot-contact OpenPose-only diagnostic:
    - `outputs/20260613_223902/reference_pose_regen/walk_ipadv_upper_mask_foot_contact_v3_8f/`
  - Improvement target:
    - artifact hard failures `0`;
    - region retake decisions below `2/8`;
    - or clear visual foot/contact improvement without guide leakage or identity drift.
- [ ] Decide the next mechanism.
  - If sidecar improves: keep sidecar route and test better sidecar render styles or a more suitable ControlNet model.
  - If sidecar worsens or no-ops: record that OpenPose-family secondary ControlNet is not enough and plan model acquisition for lineart/softedge/depth.
- [ ] Update reports and Skill.
  - `docs/reference_lock_motion_template_deep_dive.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`

## Status Vocabulary

- [x] `adopted_animation_candidate`: 120-frame source passes deterministic gates and Agent visual review.
- [x] `selected_proof_only`: useful short proof exists but full adoption blockers remain.
- [x] `rejected_diagnostic`: route/settings fail structurally or semantically.
