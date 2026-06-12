# Tasks: General 2D Game Action Asset Quality

This is the active checklist for the next phase.

Archive of the completed previous phase:
`docs/archive/Tasks_20260612_completed_research_grounded_general_action_workflow.md`

Detailed evidence:

- `docs/action_generalization_pdca_report.md`
- `docs/next_phase_run_generation_pdca_report.md`
- `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`

## Top Rule

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet or shake.
- [x] Keep the primary route on generated video workflows, not rig/cutout animation.
- [x] Prefer single-keyframe Wan i2v for first action proof and subject preservation.
- [x] Use first/last keyframes only when the endpoint is conservative, side-view, sprite-like, and close to the start framing.
- [x] Use weapon/action sidecar control for weapon attacks; do not rely on prompt-only weapon generation.
- [x] Keep generated outputs ignored; commit durable scripts, Tasks, reports, and compact references only.

## Current Baseline

- [x] Walk: current best is `review_packages/phase10_single_keyframe_wan_i2v_len121_strict_selected_proof_review_20260612_130832`.
- [x] Walk remains `selected_proof_only` because `lower_body_pale_afterimage_review: 12` blocks adoption.
- [x] Run: current best proof is `review_packages/comfy2025_run_len33_generalization_review_20260612_202914`.
- [x] Run first/last probe is not adopted: `review_packages/comfy2025_run_len33_first_last_review_20260612_213101` passed heuristic gate but visually warped into the endpoint.
- [x] Hit heavy: current semantic proof is `review_packages/comfy2025_hit_heavy_len33_generalization_review_20260612_203118`.
- [x] Hit heavy first/last probe is rejected: `review_packages/comfy2025_hit_heavy_len33_first_last_review_20260612_213306` had `retake_required: 4/33`.
- [x] Attack sword: prompt-only proof is rejected and needs sidecar weapon control.

## Non-Goals

- [x] Do not call a candidate adopted only because artifact gates pass.
- [x] Do not optimize broad 120-frame generation before 33-frame probes show clean action quality.
- [x] Do not use dramatic illustration-like endpoint keyframes for first/last Wan interpolation.
- [x] Do not hide duplicate legs, strong afterimages, or structural weapon failures with Image2Image.
- [x] Do not pursue universal action generation before `run` and `hit` quality stabilize.

## Phase 1: Conservative Endpoint Keyframes

- [x] Add or tune conservative endpoint templates for `run`: low stride, clear side view, no high kick, no extreme hair spread.
- [x] Add or tune conservative endpoint templates for `hit_light`: small stagger, one foot shift, limited torso bend.
- [x] Add or tune conservative endpoint templates for `hit_heavy`: recoil endpoint that stays near the start framing.
- [x] Generate endpoint candidates and reject any endpoint with multiple characters, cropped limbs, front view, or illustration-style pose.
- [x] Record endpoint keyframe acceptance criteria in the Skill.

Result: conservative txt2img + OpenPoseXL endpoint generation is not reliable enough for first/last Wan. It still produced front-view poses, high-kick/run illustration poses, cropped crouches, and secondary fragments. Do not pass these endpoints into first/last Wan.

## Phase 1.5: Reference-Conditioned Endpoint Keyframes

- [x] Add a reference-conditioned endpoint generation path that starts from the selected full-body side-view start frame instead of pure txt2img.
- [x] Use smaller pose deltas for `run`, `hit_light`, and `hit_heavy` than the rejected endpoint candidates.
- [x] Add endpoint review labels for front-view drift, secondary fragments, crop, high-kick pose, and endpoint too far from the start frame.
- [ ] Re-run endpoint candidates for `run`, `hit_light`, and `hit_heavy`.
- [ ] Use first/last Wan only if at least one endpoint passes the visual endpoint criteria.

Result so far: reference-conditioned `run` endpoints keep side-view/single-character framing and remove the txt2img failure modes, but the pose delta is too low. Latest checked run: `outputs_general_action_quality/action_keyframes_refcond/ComfyUI2025_131891_trim_run_keyframes_20260612_223625`, rejected with `endpoint_delta_too_low`.

## Phase 1.6: Stronger Pose Transfer Without Breaking Identity

- [ ] Try a stronger pose-transfer setting or node stack that lets OpenPose dominate more than basic img2img while preserving the reference design.
- [ ] Try localized lower-body img2img/masking so run leg motion can change without redrawing the entire character.
- [ ] Keep the `endpoint_delta_too_low` blocker and do not run first/last Wan from neutral-looking endpoints.
- [ ] Only expand to `hit_light` and `hit_heavy` after `run` produces a clean, visibly action-bearing endpoint.

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

- [x] Update `docs/action_generalization_pdca_report.md` with the next probe results.
- [x] Update `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md` with accepted and rejected patterns.
- [ ] Keep `docs/walk_candidate_comparison.md` focused on walk; create or update a general action comparison table separately.
- [x] Commit and push after each coherent PDCA checkpoint.
