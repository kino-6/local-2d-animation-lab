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

- [x] Add optional secondary ControlNet support to `scripts/regenerate_pose_sequence_controlnet.py`.
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
- [x] Add unit tests for the secondary ControlNet workflow.
  - Baseline workflow must remain unchanged without sidecar args.
  - Sidecar workflow must load a second control image and apply a second ControlNet before KSampler.
- [x] Confirm ComfyUI queue capacity before generation.
  - Use `/queue`.
  - Do not submit if pending/running queue is above the configured limit.
- [x] Run one 8-frame sidecar diagnostic probe.
  - Source image:
    - planned source was missing locally:
      - `outputs/20260613_185524/background_normalize/prior_best_start_background_normalize/frames/frame_000.png`
    - actual fallback source:
      - `outputs/20260613_223902/reference_pose_regen/walk_ipadv_upper_mask_foot_contact_v3_8f/source_reference/source_image.png`
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
- [x] Gate the sidecar probe.
  - `repair_frame_artifacts.py --mask-only --weapon none`
  - `select_best_span.py --action walk --motion-metric foreground --allow-hard-failures`
  - `analyze_sprite_regions.py`
  - Agent visual review of comparison/contact sheets.
- [x] Compare against both prior proofs.
  - Previous best:
    - `outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/`
  - Foot-contact OpenPose-only diagnostic:
    - `outputs/20260613_223902/reference_pose_regen/walk_ipadv_upper_mask_foot_contact_v3_8f/`
  - Improvement target:
    - artifact hard failures `0`;
    - region retake decisions below `2/8`;
    - or clear visual foot/contact improvement without guide leakage or identity drift.
- [x] Decide the next mechanism.
  - If sidecar improves: keep sidecar route and test better sidecar render styles or a more suitable ControlNet model.
  - If sidecar worsens or no-ops: record that OpenPose-family secondary ControlNet is not enough and plan model acquisition for lineart/softedge/depth.
- [x] Update reports and Skill.
  - `docs/reference_lock_motion_template_deep_dive.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`

## Result

- [x] Sidecar diagnostic output:
  - `outputs/20260613_225444/reference_pose_regen/walk_ipadv_upper_mask_foot_contact_v3_sidecar035_8f/`
- [x] Gate outputs:
  - artifact: `outputs/20260613_225559/artifact_repair/walk_ipadv_upper_mask_foot_contact_v3_sidecar035_8f_mask_gate/artifact_repair_report.json`
  - span: `outputs/20260613_225559/span_selection/walk_ipadv_upper_mask_foot_contact_v3_sidecar035_8f_span/span_selection_report.json`
  - region: `outputs/20260613_225559/region_diagnostics/walk_ipadv_upper_mask_foot_contact_v3_sidecar035_8f_regions/region_diagnostics_report.json`
- [x] Metrics:
  - artifact hard failures: `2/8`
  - region retake decisions: `3/8`
  - span motion: `10.505`
  - mean lower-body temporal delta: `0.08048`
  - mean feet/contact temporal delta: `0.0582`
- [x] Decision:
  - `rejected_diagnostic`
- [x] Reason:
  - secondary OpenPose-family sidecar had an effect, but not the desired foot-contact effect.
  - It improved artifact hard failures against the OpenPose-only foot-contact v3 probe (`3/8 -> 2/8`) and recovered some motion (`8.918 -> 10.505`).
  - It worsened region retakes (`2/8 -> 3/8`) and feet/contact temporal instability (`0.02694 -> 0.0582`), and visual review found shoe/leg recolor plus lower-body ghosting.
- [x] Next mechanism:
  - Do not continue scalar tuning of an OpenPose-family secondary ControlNet as the main route.
  - If lower-body sidecar is continued, acquire or test a sidecar-suitable local model such as lineart, softedge, depth, segmentation, or use the sidecar as a non-generation mask/evaluation channel.
  - Keep the previous `IPAdapterAdvanced style transfer precise + upper_body mask` proof as the best current reference-locked ControlNet proof.

## Status Vocabulary

- [x] `adopted_animation_candidate`: 120-frame source passes deterministic gates and Agent visual review.
- [x] `selected_proof_only`: useful short proof exists but full adoption blockers remain.
- [x] `rejected_diagnostic`: route/settings fail structurally or semantically.
