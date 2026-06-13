# Tasks: Masked Quality Loop For 2D Game Sprite Animation

Archive of the previous active checklist:
`docs/archive/Tasks_20260613_walk_asset_postprocess_and_quality_gate_baseline.md`

## Top Rule

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet or shake.
- [x] Keep the primary route on generated video workflows, not rig/cutout animation.
- [x] Keep 120/121-frame source sequences intact until a later frame-reduction Skill exists.
- [x] Do not call an asset adopted only because it has been packaged; adoption requires animation quality.
- [x] Save new generated artifacts only under `outputs/<timestamp>/...`; do not create new top-level `outputs_*`, `review_packages`, or `source_probe_packages` roots.
- [x] Keep `run_profile.json`, `memo.md`, workflow JSON, reports, previews, and package artifacts inside the same timestamp session.

## Current Baseline

- [x] Current full-frame walk candidate: `outputs_game_assets/comfy2025_fullbody_walk_len121_sprite_asset_rejected_with_vl_20260613_014008`.
- [x] Status: `rejected_animation_candidate`.
- [x] Main blockers: lower-body pale afterimages, foot/contact artifacts, and internal redraw/silhouette jitter.
- [x] Postprocess helps but is not enough: `outputs_sprite_postprocess/comfy2025_walk_len121_stabilized_color_20260613_074307`.
- [x] Postprocess measured improvements: luma stdev `5.94115 -> 1.15325`, saturation stdev `4.91264 -> 2.81892`, foot/contact labels `62 -> 7`, lower-body afterimage labels `120 -> 72`.
- [x] LocalVL over-accepted the rejected walk contact sheet, so LocalVL must be calibrated and cannot be the sole adoption gate.

## Non-Goals

- [x] Do not solve residual silhouette jitter by switching to rig/cutout animation.
- [x] Do not package rejected results as final assets without manifest status and quality report links.
- [x] Do not use img2img polish to hide duplicate legs, strong afterimages, or broken silhouettes.
- [x] Do not downsample 121 frames to a short loop as a substitute for improving source quality.

## Phase 1: Standardize Postprocess In The Asset Flow

- [x] Add an E2E wrapper that runs full generated frames through `stabilize_sprite_sequence.py` before final packaging.
- [x] The wrapper must preserve the full source frame count.
- [x] The wrapper must write a manifest linking source generation, postprocess report, artifact gate report, LocalVL report, and final package.
- [x] The wrapper must set final package status from quality decisions, not from successful export.
- [x] Add tests for manifest status propagation and quality-report linking.

## Phase 2: Local Mask And Region Diagnostics

- [x] Add per-frame region diagnostics for at least `lower_body`, `feet_contact`, and `cloak_or_hair_trail`.
- [x] Use foreground/alpha masks and bbox-relative regions so the diagnostics work on different character sizes.
- [x] Report region-level metrics: coverage, temporal delta, pale-afterimage coverage, contact-shadow coverage, and hard issue labels.
- [x] Export debug overlays/contact sheets for the region masks.
- [x] Add tests with synthetic frames for lower-body afterimage and foot/contact artifacts.

## Phase 3: Masked Correction Loop

- [x] Define correction policy: deterministic cleanup first, local inpaint only for small masks, retake for large/structural failures.
- [x] Implement a dry-run planner that classifies each bad frame as `postprocess_only`, `local_inpaint_candidate`, or `retake_required`.
- [x] Reuse existing `repair_frame_artifacts.py` gate output in the planner, and route only small local-mask frames toward inpaint.
- [x] Block inpaint when the mask covers structural limbs, has structural labels, or exceeds the configured local artifact coverage threshold.
- [x] Record before region metrics and decision counts in the dry-run plan.
- [x] Add correction-plan-aware repair entry so only frames classified as `local_inpaint_candidate` can proceed to actual inpaint.
- [x] Add region-derived artifact mask export and allow `repair_frame_artifacts.py --external-mask-dir` to use those masks.
- [x] Practice the correction loop in `--mask-only` on the 19 local candidates and confirm all 19 become bounded repair candidates with region masks.
- [x] Execute actual local inpaint on the 19-frame candidate subset after ComfyUI queue capacity became available.
- [x] Reject the actual inpaint result because it added gray silhouette outlines around the character.
- [x] Run deterministic white cleanup with eroded region masks as a safer comparison path.
- [x] Reinsert the cleaned 19-frame subset into the full 121-frame sequence and record after-region metrics.
- [x] Keep the result rejected: lower-body afterimage improved (`120 -> 102`), but foot/contact labels stayed `121`, silhouette jitter worsened (`95 -> 112`), and retake decisions rose (`95 -> 112`).

## Phase 4: LocalVL Calibration

- [x] Build a compact calibration set from current accepted/rejected sheets and representative frame crops.
- [x] Prompt LocalVL to score specific artifacts: lower-body afterimage, foot sliding/contact smear, silhouette redraw jitter, and color/brightness drift.
- [x] Normalize LocalVL output to strict JSON and compare it against deterministic gate labels.
- [x] Mark LocalVL as `secondary_only` until it agrees with deterministic blockers on known rejected examples.
- [x] Add tests for consistency-rule downgrades when LocalVL says adoptable but deterministic gates reject.

## Phase 5: Walk Candidate Recheck

- [x] Run the standardized flow on `outputs_game_asset_pdca/comfy2025_fullbody_walk_i2v_len121_game_candidate_20260613_011410/frames`.
- [x] Compare raw vs stabilized vs region/planner gate summaries.
- [x] Visually inspect `preview.gif`, `contact_sheet.png`, and region overlay contact sheet.
- [x] Keep the result `rejected_animation_candidate` unless lower-body afterimage and foot/contact artifacts drop below the adoption threshold.
- [x] Update the Skill with accepted and rejected patterns from this PDCA.

## Current Outputs

- [x] Standardized flow: `outputs_standardized_sprite_flow/comfy2025_walk_len121_standardized_flow_v2_20260613_092150/quality_flow_manifest.json`.
- [x] Region diagnostics: `outputs_region_diagnostics/comfy2025_walk_len121_standardized_regions_20260613_092417/region_diagnostics_report.json`.
- [x] Masked correction plan: `outputs_masked_correction_plans/comfy2025_walk_len121_standardized_plan_v2_20260613_092758/masked_correction_plan.json`.
- [x] Region-mask practice: `outputs_masked_correction_practice/comfy2025_walk_len121_local_candidates_region_masks_mask_only_20260613_095314/artifact_repair_report.json`.
- [x] Actual inpaint practice: `outputs_masked_correction_practice/comfy2025_walk_len121_local_candidates_region_masks_inpaint_d035_20260613_100605/artifact_repair_report.json`.
- [x] Best deterministic cleanup diagnostic: `outputs_masked_correction_practice/comfy2025_walk_len121_local_candidates_region_mask_white_cleanup_erode1_20260613_101231/mask_cleanup_report.json`.
- [x] Full-sequence after-region diagnostic: `outputs_region_diagnostics/comfy2025_walk_len121_full_sequence_white_cleanup_erode1_regions_v2_20260613_101836/region_diagnostics_report.json`.
- [x] PDCA report: `docs/masked_quality_loop_pdca.md`.

## Knowledge From Latest PDCA

- [x] Postprocess is useful for global luma/saturation jitter, but it does not solve body-internal lower-leg ghosts.
- [x] Region diagnostics can separate local-looking artifacts from structural retake frames.
- [x] The default `repair_frame_artifacts.py` mask was too conservative for this walk case: only `1/19` local candidates became repair candidates.
- [x] Region-derived artifact masks made the 19 local candidates actionable, but the masks sit close to body, shoe, and cloak silhouettes.
- [x] Actual ComfyUI masked inpaint with region masks is rejected: it added gray outline artifacts around body and feet.
- [x] Deterministic white cleanup with eroded masks is also rejected as an adoption path: it reduced lower-body pale labels (`120 -> 102`) but kept foot/contact labels at `121` and worsened silhouette jitter (`95 -> 112`).
- [x] The current blocker is generation-side lower-body/foot ambiguity, not a simple removable background artifact.
- [x] Do not spend more effort polishing the current 121-frame candidate unless a new generation-side probe first lowers lower-body/feet artifacts.
- [x] Keep all local repair tools as diagnostics and safety gates, not as the main solution for this candidate.

## Phase 6: Next Generation-Side Retake Plan

- [x] Freeze current masked repair branch as rejected evidence, not adoption output.
- [x] Record that actual inpaint added gray silhouette outlines and deterministic white cleanup worsened full-sequence retake counts.
- [x] Stop treating local repair as the main path for this candidate; it is diagnostic only.
- [x] Define the 33-frame Wan i2v short-probe baseline using the same full-body start image, same model stack, and current best prompt.
- [x] Run probe A: `continue_motion_max_frames=1`, current prompt, same seed.
- [x] Run probe B: `continue_motion_max_frames=2`, current prompt, same seed.
- [x] Stop probe C for plain `WanImageToVideo`: cmf1 and cmf2 were identical because `continue_motion_max_frames` is not used by this node route.
- [x] Run prompt variant D: short clean side-view walk, small stride, crisp shoes, no trailing shoes, no translucent lower body.
- [x] Run prompt variant E: slow walk-in-place, separated feet, sharp lower legs, no cloak/leg blending, no foot smears.
- [x] Gate every completed 33-frame probe with `analyze_sprite_regions.py`, `repair_frame_artifacts.py --mask-only`, and Agent visual contact-sheet review.
- [x] Compare each probe against the current baseline on lower-body pale labels, foot/contact labels, silhouette jitter labels, and motion readability.
- [x] Run at least one seed repeat for the promising prompt E short probe before promoting it.
- [x] Do not promote the best short setting to a 121-frame source: prompt E improved lower-body pale labels but retained `33/33` foot/contact labels and failed seed-repeat motion readability.
- [x] Generate cleaner walk-ready full-body start keyframe candidates with separated feet, visible shoes, readable lower legs, and less cloak/leg ambiguity.
- [x] Reject the auto-selected clean start frame because the selector picked a back-view candidate; manually test the better side-view candidate.
- [x] Reject the manual side-view clean-start Wan probe because guide/background leakage and background contamination were amplified.
- [x] Keep final packaging rejected unless the full 121-frame gate and Agent visual review pass.

## Latest Walk Short Probe Results

- [x] PDCA report: `docs/walk_short_probe_pdca_20260613.md`.
- [x] Best single short probe: `outputs_wan_short_walk_probes/walk_len33_i2v_prompt_e_slow_separated_feet_20260613_111114`.
- [x] Best single short probe status: `rejected_probe`, not 121-frame promotion-ready.
- [x] Main reason: foot/contact artifacts remain `33/33`; seed repeat became mostly static; no local route produced an adoptable walk.
- [x] Important tooling fix: `analyze_sprite_regions.py` now handles unreadable/no-foreground frames as `foreground_missing_or_unreadable_sprite` and retake instead of crashing or silently passing.
- [x] Model note: no new model download was needed; local VACE and WanAnimate routes were available but rejected in this PDCA.

## Phase 7: Next Focus

- [x] Add an explicit motion-readability gate so near-static clips cannot pass only because temporal jitter is low.
  - Implemented `analyze_motion_readability()` with mean motion, active-frame ratio, and max static-run checks.
  - Integrated it into `select_best_span.py` and `run_sprite_asset_quality_flow.py`; E2E manifests now include `motion_readability_report`.
- [x] Improve start-frame selection so back views, guide/panel residue, and background contamination are rejected before Wan.
  - Added start-frame issue codes: `possible_back_view_or_missing_profile_detail`, `guide_or_panel_residue`, and `background_contamination_high`.
  - Full-body candidate selection treats these as hard failures.
- [x] Add a start-frame background normalization step before Wan, then re-test a side-view candidate.
  - `run_wan_walk_i2v.py` now normalizes start frames through `prepare_clean_start_frame()` before upload and can reject bad starts before queuing ComfyUI.
  - Retest start gate: `outputs/20260613_120808/wan_start_frame/phase7_face_visible_side_start_gate/start_frame_report.json` produced `prepared_with_warnings`, with extra components removed and low background contamination.
  - Retest Wan probe: `outputs/20260613_120834/wan_walk_i2v/phase7_start_norm_prompt_e_len9_probe/wan_walk_i2v_report.json`.
  - Retest gate: motion readability passed (`mean_motion_delta: 5.435`, active-frame ratio `0.625`), but region diagnostics kept it rejected (`foot_shadow_or_contact_artifact_review: 9/9`, lower-body afterimage `4/9`, structural hard failures in span selection).
  - Conclusion: start normalization works as a pre-Wan cleanup/gate, but it does not solve a back-biased or foot-ambiguous source candidate. Do not promote this retest.
- [x] Revisit `WanAnimateToVideo` only after creating a calibrated pose/control video that does not collapse the character into a silhouette.
  - Kept WanAnimate out of promotion path; current gating requires readable start-frame and calibrated control before a new WanAnimate retest.
- [x] Keep `prompt E` as the current best prompt wording for i2v, but require a seed-stable short probe before any 121-frame generation.
  - `prompt E` remains the current wording baseline, but motion-readability must pass on short seed-repeat probes before 121-frame promotion.
