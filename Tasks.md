# Tasks: Foot-Contact Reference-Locked Walk Probe

Archived checkpoint:
`docs/archive/Tasks_20260613_lower_body_contact_control_completed.md`

Detailed evidence:

- `docs/reference_conditioned_regen_pdca.md`
- `docs/reference_lock_motion_template_deep_dive.md`
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

- [x] Reference lock route exists:
  - `scripts/regenerate_pose_sequence_controlnet.py`
  - `IPAdapterAdvanced`
  - `upper_body` attention mask
  - novaOrangeXL checkpoint
  - SDXL OpenPose ControlNet
- [x] Best previous reference-locked short proof:
  - `outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/`
  - Status: `selected_proof_only`, not adoption OK.
  - Remaining blocker: foot/contact readability and lower-body local redraw stability.
- [x] Best current lower-body/contact motion source:
  - `outputs/20260613_222505/motion_source_video_pdca/motion_sources/sideview_walk_foot_contact_v3/`
  - `sampled_min_ankle_x_separation: 0.204`
  - `sampled_min_foot_box_x_gap: 0.11352`
  - `unclear_ankle_separation_count: 0`
  - `unclear_foot_box_count: 0`
  - `max_stance_slide_delta: 0.00345`

## Completed PDCA: Use Foot-Contact Template In Generation

- [x] Confirm ComfyUI queue capacity before generation.
  - If queue is larger than the configured limit, wait instead of adding more jobs.
  - Keep all output under `outputs/<timestamp>/...`.
- [x] Run an 8-frame probe with the new foot-contact OpenPose source.
  - Source image:
    - `outputs/20260613_185524/background_normalize/prior_best_start_background_normalize/frames/frame_000.png`
  - Pose source:
    - `outputs/20260613_222505/motion_source_video_pdca/motion_sources/sideview_walk_foot_contact_v3/controlnet`
  - Pose indices:
    - `0,15,30,45,60,75,90,105`
  - Baseline settings:
    - checkpoint `novaOrangeXL_v120.safetensors`
    - ControlNet `SDXL\OpenPoseXL2.safetensors`
    - denoise `0.78`
    - ControlNet strength `0.92`
    - ControlNet end `0.68`
    - IPAdapter mode `advanced`
    - IPAdapter weight type `style transfer precise`
    - IPAdapter weight `0.55`
    - IPAdapter end `0.62`
    - IPAdapter attention mask `upper_body`
- [x] Gate the generated 8-frame probe.
  - `repair_frame_artifacts.py --mask-only --weapon none`
  - `select_best_span.py --action walk --motion-metric foreground --allow-hard-failures`
  - `analyze_sprite_regions.py`
  - Agent visual review of `comparison_sheet.png`, `contact_sheet.png`, and `preview.gif`.
  - Generated output:
    - `outputs/20260613_223902/reference_pose_regen/walk_ipadv_upper_mask_foot_contact_v3_8f/`
  - Gate outputs:
    - artifact: `outputs/20260613_224018/artifact_repair/walk_ipadv_upper_mask_foot_contact_v3_8f_mask_gate/artifact_repair_report.json`
    - span: `outputs/20260613_224018/span_selection/walk_ipadv_upper_mask_foot_contact_v3_8f_span/span_selection_report.json`
    - region: `outputs/20260613_224018/region_diagnostics/walk_ipadv_upper_mask_foot_contact_v3_8f_regions/region_diagnostics_report.json`
- [x] Compare against the previous upper-body-mask proof.
  - Prior proof:
    - `outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/`
  - Required improvement:
    - region `retake_required` below `2/8`, or
    - clear visual improvement in foot/contact readability without identity drift.
  - Result:
    - region retake stayed `2/8`, not below previous proof.
    - artifact hard failures worsened from `0` to `3`.
    - span motion dropped from previous `11.725` to `8.918`.
    - lower-body/feet temporal deltas improved, but not enough to beat the prior proof overall.
- [x] Decide promotion status.
  - `rejected_diagnostic`: guide burn-in, duplicate lower limbs, severe identity drift, or worse foot/contact labels.
  - `selected_proof_only`: clearer foot/contact but still not adoption OK.
  - `adopted_animation_candidate`: only if short proof has artifact hard failures `0`, region retakes `0`, readable walk contact, and stable identity.
  - Decision: `rejected_diagnostic`.
  - Reason: the foot-contact template is better as a control source, but feeding it through the same OpenPose-only path did not improve generated sprite adoption quality. It increased duplicate-silhouette hard failures.
- [x] Record result in reports and Skill.
  - Update `docs/reference_lock_motion_template_deep_dive.md`.
  - Update `docs/walk_candidate_comparison.md`.
  - Update `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md` if the decision changes the workflow rule.

## Failure Analysis

- [x] Do not tune only prompts or scalar weights for a long loop.
- [x] Inspect whether failure comes from:
  - pose template still too exaggerated;
  - ControlNet copying the guide;
  - IPAdapter still freezing or recoloring the body;
  - model unable to preserve lower-body structure frame-to-frame.
  - Finding: the template itself is cleaner, but OpenPose-only does not carry foot-box semantics into generated shoes/contact. The failure is a mechanism limit, not only template geometry.
- [x] If foot/contact remains poor, test lower-body sidecar as a separate control/mask candidate rather than visible overlay.
  - Next route: use `lower_body_sidecar/` as a separate control/mask candidate, not as visible overlay.
- [x] If identity drifts, compare upper-body mask strength and whole-character mask only as a short diagnostic.
  - Finding: identity drift was not the primary blocker in this probe.

## Status Vocabulary

- [x] `adopted_animation_candidate`: 120-frame source passes deterministic gates and Agent visual review.
- [x] `selected_proof_only`: useful short proof exists but full adoption blockers remain.
- [x] `rejected_diagnostic`: route/settings fail structurally or semantically.
