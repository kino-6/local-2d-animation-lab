# Tasks: General 2D Game Action Asset Quality

This is the active checklist for the next phase.

Archive of the completed previous phase:
`docs/archive/Tasks_20260612_completed_research_grounded_general_action_workflow.md`

Detailed evidence:

- `docs/action_generalization_pdca_report.md`
- `docs/next_phase_run_generation_pdca_report.md`
- `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`

## Top Rule

- [ ] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [ ] Treat the input image as a design reference, not pixels to directly puppet or shake.
- [ ] Keep the primary route on generated video workflows, not rig/cutout animation.
- [ ] Prefer single-keyframe Wan i2v for first action proof and subject preservation.
- [ ] Use first/last keyframes only when the endpoint is conservative, side-view, sprite-like, and close to the start framing.
- [ ] Use weapon/action sidecar control for weapon attacks; do not rely on prompt-only weapon generation.
- [ ] Keep generated outputs ignored; commit durable scripts, Tasks, reports, and compact references only.

## Current Baseline

- [ ] Walk: current best is `review_packages/phase10_single_keyframe_wan_i2v_len121_strict_selected_proof_review_20260612_130832`.
- [ ] Walk remains `selected_proof_only` because `lower_body_pale_afterimage_review: 12` blocks adoption.
- [ ] Run: current best proof is `review_packages/comfy2025_run_len33_generalization_review_20260612_202914`.
- [ ] Run first/last probe is not adopted: `review_packages/comfy2025_run_len33_first_last_review_20260612_213101` passed heuristic gate but visually warped into the endpoint.
- [ ] Hit heavy: current semantic proof is `review_packages/comfy2025_hit_heavy_len33_generalization_review_20260612_203118`.
- [ ] Hit heavy first/last probe is rejected: `review_packages/comfy2025_hit_heavy_len33_first_last_review_20260612_213306` had `retake_required: 4/33`.
- [ ] Attack sword: prompt-only proof is rejected and needs sidecar weapon control.

## Non-Goals

- [ ] Do not call a candidate adopted only because artifact gates pass.
- [ ] Do not optimize broad 120-frame generation before 33-frame probes show clean action quality.
- [ ] Do not use dramatic illustration-like endpoint keyframes for first/last Wan interpolation.
- [ ] Do not hide duplicate legs, strong afterimages, or structural weapon failures with Image2Image.
- [ ] Do not pursue universal action generation before `run` and `hit` quality stabilize.

## Phase 1: Conservative Endpoint Keyframes

- [ ] Add or tune conservative endpoint templates for `run`: low stride, clear side view, no high kick, no extreme hair spread.
- [ ] Add or tune conservative endpoint templates for `hit_light`: small stagger, one foot shift, limited torso bend.
- [ ] Add or tune conservative endpoint templates for `hit_heavy`: recoil endpoint that stays near the start framing.
- [ ] Generate endpoint candidates and reject any endpoint with multiple characters, cropped limbs, front view, or illustration-style pose.
- [ ] Record endpoint keyframe acceptance criteria in the Skill.

## Phase 2: Short-Stage Action Generation

- [ ] Run `run` with single-keyframe i2v using the best current ComfyUI2025 full-body keyframe as the baseline comparator.
- [ ] Run `run` with conservative first/last endpoint and compare against first-frame-only.
- [ ] Split `hit_heavy` into short stages: neutral -> recoil and recoil -> recovery.
- [ ] Generate each `hit_heavy` stage as a short first/last probe rather than one far endpoint.
- [ ] Export Godot review packages for every candidate.

## Phase 3: Quality Gates

- [ ] Add visual review labels for endpoint warp or sudden pose teleporting.
- [ ] Add visual review labels for view drift from side-view into front-view.
- [ ] Add visual review labels for background tone drift after first/last generation.
- [ ] Keep `lower_body_pale_afterimage_review` as a blocker for fast leg actions.
- [ ] Compare first-frame-only and first/last candidates with the same report fields: motion score, artifact gate, visual decision, Godot status.

## Phase 4: Weapon Sidecar Planning

- [ ] Define the minimum sidecar for `attack_sword`: hand positions, blade line, slash arc, and weapon mask.
- [ ] Add a weapon consistency gate: weapon exists, weapon is connected to hand, weapon does not fragment.
- [ ] Run one short `attack_sword` sidecar probe only after `run` or `hit` quality improves.

## Phase 5: Documentation And Handoff

- [ ] Update `docs/action_generalization_pdca_report.md` with the next probe results.
- [ ] Update `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md` with accepted and rejected patterns.
- [ ] Keep `docs/walk_candidate_comparison.md` focused on walk; create or update a general action comparison table separately.
- [ ] Commit and push after each coherent PDCA checkpoint.
