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
- [x] Historical note: do not optimize broad 120-frame generation before 33-frame probes show clean action quality.
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
- [x] Re-run endpoint candidates for `run`, `hit_light`, and `hit_heavy`.
- [x] Use first/last Wan only if at least one endpoint passes the visual endpoint criteria.

Result: rerun roots are `outputs_general_action_quality/action_keyframes_refcond_rerun/ComfyUI2025_131891_trim_run_keyframes_20260612_231436`, `outputs_general_action_quality/action_keyframes_refcond_rerun/ComfyUI2025_131891_trim_hit_light_keyframes_20260612_233040`, and `outputs_general_action_quality/action_keyframes_refcond_rerun/ComfyUI2025_131891_trim_hit_heavy_keyframes_20260612_233101`. The automatic gate reported `candidate_ok`, but visual review rejected all three for first/last use because they remain too neutral/front-facing to read as action endpoints. No first/last Wan was run from these endpoints.

## Phase 1.6: Stronger Pose Transfer Without Breaking Identity

- [x] Try a stronger pose-transfer setting or node stack that lets OpenPose dominate more than basic img2img while preserving the reference design.
- [x] Try localized lower-body img2img/masking so run leg motion can change without redrawing the entire character.
- [x] Keep the `endpoint_delta_too_low` blocker and do not run first/last Wan from neutral-looking endpoints.
- [x] Only expand to `hit_light` and `hit_heavy` after `run` produces a clean, visibly action-bearing endpoint.

Result: stronger img2img/control settings were already tested through `0.72/0.90` and still did not create a readable run endpoint. `--source-edit-region lower_body` was added and tested in `outputs_general_action_quality/action_keyframes_refcond_lower_body/ComfyUI2025_131891_trim_run_keyframes_20260612_233937`; it localized the edit but failed with `duplicate_silhouette_area_high` and visible lower-body/outfit redraw. This path remains diagnostic only.

## Phase 2: Short-Stage Action Generation

- [x] Run `run` with single-keyframe i2v using the best current ComfyUI2025 full-body keyframe as the baseline comparator.
- [x] Run `run` with conservative first/last endpoint and compare against first-frame-only.
- [x] Split `hit_heavy` into short stages: neutral -> recoil and recoil -> recovery.
- [x] Generate each `hit_heavy` stage as a short first/last probe rather than one far endpoint.
- [x] Export Godot review packages for every candidate.

Result: current baseline remains `review_packages/comfy2025_run_len33_generalization_review_20260612_202914`. Conservative first/last endpoint generation was compared and rejected before Wan because no endpoint passed visual criteria. `hit_heavy` stage planning is documented, but stage generation is gated until `run` endpoint control produces a clean action-bearing endpoint. Existing review packages are recorded in `docs/general_action_comparison.md`.

## Phase 3: Quality Gates

- [x] Add visual review labels for endpoint warp or sudden pose teleporting.
- [x] Add visual review labels for view drift from side-view into front-view.
- [x] Add visual review labels for background tone drift after first/last generation.
- [x] Keep `lower_body_pale_afterimage_review` as a blocker for fast leg actions.
- [x] Compare first-frame-only and first/last candidates with the same report fields: motion score, artifact gate, visual decision, Godot status.

Result: `scripts/export_review_package.py` now records `visual_decision`, `visual_labels`, `motion_score`, `artifact_gate_summary`, and `godot_status` in the review manifest. The Skill now names `endpoint_warp_or_pose_teleport_review`, `side_to_front_view_drift_review`, and `background_tone_drift_review`; `lower_body_pale_afterimage_review` remains blocking.

## Phase 4: Weapon Sidecar Planning

- [x] Define the minimum sidecar for `attack_sword`: hand positions, blade line, slash arc, and weapon mask.
- [x] Add a weapon consistency gate: weapon exists, weapon is connected to hand, weapon does not fragment.
- [x] Run one short `attack_sword` sidecar probe only after `run` or `hit` quality improves.

Result: minimum sidecar is documented in `docs/action_generalization_pdca_report.md` and `docs/general_action_comparison.md`. Weapon gate issue codes already exist in `scripts/repair_frame_artifacts.py`: `weapon_missing`, `weapon_fragmented`, `weapon_not_elongated`, and `weapon_detached`. The sidecar probe was intentionally not run because `run`/`hit` endpoint quality did not improve enough to satisfy the prerequisite.

## Phase 5: Documentation And Handoff

- [x] Update `docs/action_generalization_pdca_report.md` with the next probe results.
- [x] Update `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md` with accepted and rejected patterns.
- [x] Keep `docs/walk_candidate_comparison.md` focused on walk; create or update a general action comparison table separately.
- [x] Commit and push after each coherent PDCA checkpoint.

## Phase 6: 120-Frame 2D Game Sprite Asset Continuation

The next deliverable is not a still proof. It must be a 2D game animation asset package that can be inspected as animation.

- [x] Use `assets/reference/ComfyUI2025_131891_trim.png` as the current character design reference.
- [x] Generate a 120/121-frame `walk` candidate with local ComfyUI/Wan using the proven single-keyframe i2v route first.
- [x] Keep frame count intact for asset packaging; do not collapse or sample down to 2 frames.
- [x] Package the full frame sequence as transparent PNG frames, spritesheet, preview GIF, alpha sheet, and manifest.
- [x] Run the existing artifact/animation gates on the full sequence.
- [x] Visually inspect the preview/contact sheet and state plainly whether the animation is adoptable, selected-proof-only, or rejected.
- [x] Record the actual output paths and decision in this file and the Skill/report docs.

Result:

- Direct Wan from `assets/reference/ComfyUI2025_131891_trim.png` failed as a game animation route because the source is bust-up; output stayed upper-body only.
- Full-body reference candidates were generated at `outputs_game_asset_pdca/fullbody_reference/ComfyUI2025_131891_trim_20260613_011006`.
- BiRefNet-cleaned candidate 0 was used as the start frame: `outputs_game_asset_pdca/fullbody_reference_cutout/comfy2025_fullbody_candidate_cutout_20260613_011316/frames/frame_000.png`.
- 121-frame walk generation output: `outputs_game_asset_pdca/comfy2025_fullbody_walk_i2v_len121_game_candidate_20260613_011410`.
- Game asset package: `outputs_game_assets/comfy2025_fullbody_walk_len121_sprite_asset_rejected_with_vl_20260613_014008`.
- Artifact gate: `outputs_game_asset_pdca/quality_gates/comfy2025_fullbody_walk_len121_gate_20260613_013130`.
- LocalVL evaluation: `outputs_local_vl_eval/comfy2025_fullbody_walk_len121_sprite_asset_rejected_vl_20260613_013916`.
- Decision: `rejected_animation_candidate`, not adopted. It reads more like a walk than the bust-up failure, but foot blur/contact artifacts and lower-body pale afterimages are too frequent for a usable 2D game sprite.
- Gate summary: `retake_required: 2`, `repair_candidate: 65`, `no_repair_needed: 54`; review labels include `lower_body_pale_afterimage_review: 120`, `foot_shadow_or_contact_artifact_review: 62`, `skin_colored_afterimage_near_legs_review: 14`.
- LocalVL over-accepted the contact sheet as adoptable, so LocalVL is useful only as a secondary signal until it is calibrated against lower-body afterimage/contact labels.

## Phase 7: Next Correction Target

- [x] Do not spend more effort packaging rejected walk generations as final assets.
- [ ] Improve the start-frame route so the selected full-body reference is side-view, single-character, white-background, and manually accepted before Wan.
- [ ] Add an explicit start-frame visual decision field; block Wan if the selected reference is back-view, front-view, model-sheet, or bust-up.
- [x] Try deterministic postprocess for visible frame jitter and brightness/saturation drift before another generation retake.
- [ ] Reduce lower-body afterimages in generation before trying cosmetic img2img polish.
- [ ] Calibrate LocalVL with examples where artifact gates reject but the contact sheet still looks action-readable at thumbnail scale.

Postprocess result:

- Added `scripts/stabilize_sprite_sequence.py`.
- Input: `outputs_game_assets/comfy2025_fullbody_walk_len121_sprite_asset_rejected_with_vl_20260613_014008/frames`.
- Output: `outputs_sprite_postprocess/comfy2025_walk_len121_stabilized_color_20260613_074307`.
- Test: `tests/test_stabilize_sprite_sequence.py`.
- The deterministic color pass helped: foreground luma stdev `5.94115 -> 1.15325`; foreground saturation stdev `4.91264 -> 2.81892`.
- The visible contact/foot artifact labels also improved: `foot_shadow_or_contact_artifact_review: 62 -> 7`; `lower_body_pale_afterimage_review: 120 -> 72`.
- It did not solve adoption: gate remained `candidate_status: rejected` with `retake_required: 4`, `repair_candidate: 6`, `no_repair_needed: 111`.
- Lesson: brightness/saturation drift is postprocessable. The remaining visible jitter is mostly internal redraw/silhouette instability, not canvas-anchor jitter; bbox anchor stdev was already near zero.
