# Tasks: Converge Local 2D Animation Asset Workflow

This file is the active convergence checklist only.

Do not append detailed PDCA logs here. Put experiment details in
`docs/next_phase_run_generation_pdca_report.md`, and archive old task expansions under
`docs/archive/`.

## Top Rule

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet or shake.
- [x] Keep the main route on generated video/control workflows, not rig/cutout animation.
- [x] Prefer `novaOrangeXL_v120.safetensors` for still/image refinement and VACE/Wan workflows for temporal motion.
- [x] Preserve 120-frame-class source generations; selected spans are review evidence, not the final thinning/export step.

## Current Best Walk Evidence

- [x] Current source motion: `outputs_motion_source_video_pdca/run_synthetic_sideview_walk_v4_edge_stride`
- [x] Current model route: `WanVaceToVideo` with `wan2.1_vace_1.3B_fp16.safetensors`
- [x] Current control render: `wan_balanced`
- [x] Current prompt route: identity prompt with explicit no-headgear negatives
- [x] Current best 16-frame review package: `review_packages/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_foreground_motion_review_20260611_175401`
- [x] Current best selected-span metrics: foreground motion `4.993`, span hard failures `0/16`, artifact `retake_required: 0/16`, Godot `ok: true`
- [x] Full 121-frame artifact gate was run: `outputs_artifact_repair/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_full_sequence_gate_20260611_175642`
- [x] Full 121-frame source gate now has `retake_required: 0/121` after fixing warm light subject protection in duplicate-silhouette scoring.
- [x] Full 121-frame review package: `review_packages/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_full_source_review_20260611_182900`

## Walk Convergence Criteria

- [x] Full 121-frame source gate has `retake_required: 0`.
- [x] Full 121-frame preview/contact sheet has no recurring headgear, duplicate-leg, strong afterimage, or foreground-internal ghosting pattern.
- [x] A review package exists for the full 121-frame source, not only a selected 16-frame span.
- [x] Godot validation passes for the full 121-frame package.
- [x] The Skill and PDCA report name the chosen walk workflow and the known rejection boundaries.

## Closed Decisions

- [x] Retake or trim/regenerate around full-sequence frames `65` and `116` without reducing the selected-span walk readability.
- [x] Stop broad walk PDCA expansion: the full 121-frame walk source is now clean enough to use as the current workflow reference.
- [x] Keep weapon action PDCA out of this checklist until a new branch/task file is opened for that phase.

## Next Phase Pointer

Sword action PDCA is the next phase, not an open task in this convergence checklist. Start from the weapon guide handoff notes in `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md` and log detailed trials in `docs/next_phase_run_generation_pdca_report.md`.

## Rules For Keeping This File Small

- [x] Archive expanded checklist history at `docs/archive/Tasks_20260611_pdca_expanded_before_convergence.md`.
- [x] Add only convergence-level tasks here.
- [x] When a task needs more than 3-5 evidence bullets, write a report section and link to it instead of expanding this checklist.
