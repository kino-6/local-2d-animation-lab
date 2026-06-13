# Masked Quality Loop PDCA

This report records the 2026-06-13 implementation pass for postprocess, local region diagnostics, masked correction planning, and LocalVL calibration.

## Objective

The objective remains local-first 2D game animation asset generation from a character reference image plus a natural-language action request. The reference is a design reference, not a puppet source. The workflow preserves 120-frame source sequences and rejects packaged assets when animation quality is not sufficient. If a local video workflow emits 121 frames for model or loop-endpoint reasons, normalize the adopted source back to 120 frames.

## Implemented Flow

1. Extract a transparent foreground package from generated frames.
2. Stabilize brightness and saturation with `scripts/stabilize_sprite_sequence.py`.
3. Link deterministic artifact reports, LocalVL reports, and source generation reports into one quality manifest.
4. Package the final sprite asset only with a status derived from quality gates.
5. Run bbox-relative region diagnostics for `lower_body`, `feet_contact`, and `cloak_or_hair_trail`.
6. Build a dry-run masked correction plan that separates `postprocess_only`, `local_inpaint_candidate`, and `retake_required`.
7. Pass the correction plan into `repair_frame_artifacts.py` so only `local_inpaint_candidate` frames may proceed to actual inpaint.
8. Export region-derived artifact masks and pass them to repair when the default artifact mask is too conservative.
9. Keep LocalVL as `secondary_only` when deterministic reports reject the candidate.

## Current Recheck

Source:

- `outputs_game_asset_pdca/comfy2025_fullbody_walk_i2v_len121_game_candidate_20260613_011410/frames`

Standardized flow:

- `outputs_standardized_sprite_flow/comfy2025_walk_len121_standardized_flow_v2_20260613_092150/quality_flow_manifest.json`

Final package status:

- `rejected_animation_candidate`

Postprocess effect:

- luma stdev: `5.94115 -> 1.6201`
- saturation stdev: `4.91264 -> 2.84352`

This confirms the postprocess pass helps color and brightness jitter, but it does not solve lower-body afterimages or structural redraw jitter.

## Region Diagnostics

Report:

- `outputs_region_diagnostics/comfy2025_walk_len121_standardized_regions_20260613_092417/region_diagnostics_report.json`

Overlay sheet:

- `outputs_region_diagnostics/comfy2025_walk_len121_standardized_regions_20260613_092417/region_overlay_contact_sheet.png`

Summary:

- frame count: `121`
- `foot_shadow_or_contact_artifact_review`: `121`
- `lower_body_pale_afterimage_review`: `120`
- `silhouette_redraw_jitter_review`: `95`
- decision counts: `local_inpaint_candidate: 26`, `retake_required: 95`

The region diagnostic says some frames have local cleanup-shaped artifacts, but most failures are structural enough to retake.

## Masked Correction Plan

Report:

- `outputs_masked_correction_plans/comfy2025_walk_len121_standardized_plan_v2_20260613_092758/masked_correction_plan.json`

Summary:

- `local_inpaint_candidate`: `19`
- `retake_required`: `102`

Important correction:

- The planner now thresholds local artifact coverage (`pale_afterimage_coverage`, `contact_shadow_coverage`, and `trail_coverage`) instead of raw region foreground coverage.
- Raw region coverage is still recorded for diagnostics, but it is not treated as the repair mask size.

Decision:

- Do not run broad inpaint over this full sequence as an adoption path.
- Local inpaint is allowed only for the 19 small-mask frames.
- The candidate remains primarily a retake/generation-control problem because `silhouette_redraw_jitter_review` and high temporal deltas affect most frames.
- `repair_frame_artifacts.py --correction-plan <masked_correction_plan.json>` is implemented for a later small-subset inpaint run.

## Practice Run

Default repair-mask practice:

- `outputs_masked_correction_practice/comfy2025_walk_len121_local_candidates_mask_only_20260613_094806/artifact_repair_report.json`
- result: `repair_candidate: 1`, `no_repair_needed: 18`

Finding:

- The default repair mask was too conservative for the lower-body/feet afterimage case. It mostly produced empty masks, so actual inpaint would not meaningfully change the candidate.

Region-mask practice:

- region diagnostics with artifact masks: `outputs_region_diagnostics/comfy2025_walk_len121_standardized_regions_v2_20260613_095201/region_diagnostics_report.json`
- repair mask-only subset: `outputs_masked_correction_practice/comfy2025_walk_len121_local_candidates_region_masks_mask_only_20260613_095314/artifact_repair_report.json`
- result: `repair_candidate: 19`, `mean_mask_coverage: 0.03563`

Finding:

- Region-derived masks are usable as bounded repair masks for the 19 local candidates.
- The masks are close to body/foot silhouettes, so actual inpaint must remain limited to `local_inpaint_candidate` frames and must be reviewed with `comparison_sheet.png`.
- Actual ComfyUI inpaint was not queued during this pass because ComfyUI was busy (`running: 1`, `pending: 94`). Do not add inpaint jobs into a large unrelated queue.

## Actual Repair Follow-Up

Actual inpaint:

- `outputs_masked_correction_practice/comfy2025_walk_len121_local_candidates_region_masks_inpaint_d035_20260613_100605/artifact_repair_report.json`
- settings: `denoise 0.35`, `cfg 5.4`, `steps 24`, 19 local candidates only
- result: `inpainted_frames: 19`, `candidate_status: selected_proof_only`

Visual decision:

- Rejected. The inpaint pass added gray silhouette outlines around the body and feet. It increased apparent motion/noise instead of removing the lower-body ghosts.
- Do not use the current ComfyUI masked inpaint recipe for these walk afterimages.

Deterministic white cleanup:

- first fixed a bug in `apply_mask_cleanup.py`: transparent RGBA frames must be composited on white before RGB cleanup, otherwise transparent background becomes black.
- added `--mask-erode` and tested erode `1`.
- subset output: `outputs_masked_correction_practice/comfy2025_walk_len121_local_candidates_region_mask_white_cleanup_erode1_20260613_101231/mask_cleanup_report.json`
- full sequence: `outputs_masked_correction_practice/comfy2025_walk_len121_full_sequence_white_cleanup_erode1_20260613_101231/frames`
- after-region report: `outputs_region_diagnostics/comfy2025_walk_len121_full_sequence_white_cleanup_erode1_regions_v2_20260613_101836/region_diagnostics_report.json`

After-region summary:

- `lower_body_pale_afterimage_review`: `120 -> 102`
- `foot_shadow_or_contact_artifact_review`: `121 -> 121`
- `silhouette_redraw_jitter_review`: `95 -> 112`
- `retake_required`: `95 -> 112`

Decision:

- Rejected. Eroded white cleanup reduces some lower-body pale afterimages, but it creates visible white chips and worsens temporal/silhouette diagnostics. This is useful evidence, not an adoption path.

## LocalVL Calibration

LocalVL remains useful for semantic and visual review, but it over-accepted a known rejected contact sheet. The evaluator now accepts deterministic reports and downgrades LocalVL adoption when deterministic gates reject.

Policy:

- deterministic artifact/region gates decide structural blockers
- LocalVL is `secondary_only` until calibrated against rejected examples
- Agent visual inspection remains required for sprite readability

## Outcome

The implementation improves the workflow quality, not the candidate's final adoption status.

What improved:

- color/brightness jitter is measurable and reduced
- artifacts are localized by body region
- small-mask cleanup candidates are separated from structural retakes
- LocalVL over-acceptance is guarded by deterministic reports
- final packaging no longer implies adoption

What remains blocked:

- the current walk candidate is still not a high-quality 2D game animation asset
- lower-body afterimages are present on almost every frame
- silhouette redraw jitter appears on most frames
- actual inpaint and deterministic white cleanup were both tried on small local-mask frames and should not be used to hide structural motion failure

## Next Strategy

The next work should return to generation-side control. The failed repair trials show the lower-body artifacts are not just removable background noise; they are entangled with the generated body, cloak, and foot silhouettes.

Do not continue broad postprocess, region-mask inpaint, or white cleanup as the main adoption route for this candidate.

Recommended next PDCA:

1. Freeze the current candidate as rejected evidence.
2. Run short 33-frame Wan i2v probes to search for settings that reduce lower-body afterimages before committing to a full 121-frame source.
3. Use the same strict region diagnostics on each short probe.
4. Promote only settings with clearly lower lower-body/feet artifacts and no increase in silhouette jitter to a full 121-frame run.
5. If no setting improves the current route, generate a cleaner walk-ready full-body start keyframe with less lower-body cloak/foot ambiguity, then repeat the Wan i2v probe.

Settings worth testing first:

- `continue_motion_max_frames=1`, `2`, and `3`, because one prior probe suggested `1` may reduce small-mask retakes but was seed-unstable.
- Lower-motion prompt variants: "small clean side-view walk cycle", "short stride", "feet stay crisp", "no trailing shoes", "no translucent lower body".
- Seed repeat on any promising setting before full 121 generation.
- Same `novaOrangeXL` full-body reference route, but with stricter start-frame acceptance: separated feet, visible shoes, readable lower legs, no cloak covering both legs, clean white background.

Promotion gate:

- 33-frame probe must reduce `lower_body_pale_afterimage_review` and `foot_shadow_or_contact_artifact_review` without raising `silhouette_redraw_jitter_review`.
- Full 120-frame output remains the required asset source.
- Packaging remains rejected unless the full 121-frame gate and visual review pass.
