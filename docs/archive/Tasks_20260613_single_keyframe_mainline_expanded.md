# Tasks: Start-Frame-First Walking Asset Pipeline

Archive of the previous completed checklist:
`docs/archive/Tasks_20260613_masked_quality_loop_completed.md`

## Top Rule

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet or shake.
- [x] Keep the primary route on generated video workflows, not rig/cutout animation.
- [x] Keep 120-frame source sequences intact until a later frame-reduction Skill exists.
- [x] Save new generated artifacts only under `outputs/<timestamp>/...`; do not create new top-level `outputs_*`, `review_packages`, or `source_probe_packages` roots.
- [x] Do not call an asset adopted only because it has been packaged; adoption requires animation quality.
- [x] Do not promote short probes to 120-frame source generation unless short-probe motion readability, lower-body quality, and foot/contact quality pass.
  - If a Wan node requires a model-native odd length such as 121, treat the extra frame as a generation artifact or loop-closure duplicate and normalize to 120 before asset adoption.

## Current Diagnosis

- [x] Previous walk source remains rejected as a 2D game animation asset.
- [x] Mainline correction: the best historical walk route is still `single-keyframe Wan i2v`, not the later visible foot-guide/control-map experiments.
  - Best evidence: `review_packages/phase10_single_keyframe_wan_i2v_len121_strict_selected_proof_review_20260612_130832`.
  - Why it matters: this route preserved character identity and produced readable walk motion better than VACE/Wan22Fun control routes.
  - Current blocker: recurring pale lower-body afterimages and foot/contact artifacts, not wholesale action failure.
- [x] Postprocess can reduce global luma/saturation jitter but does not fix generation-side lower-leg ghosts or ambiguous feet.
- [x] Masked inpaint and deterministic white cleanup are diagnostic tools, not the main solution for the current walk failure.
- [x] Prompt E is the best current Wan i2v walk wording, but it is not 120-frame promotion-ready.
- [x] Latest normalized-start short probe produced motion readability pass but still failed animation quality:
  - Wan probe: `outputs/20260613_120834/wan_walk_i2v/phase7_start_norm_prompt_e_len9_probe/`.
  - Motion readability: passed with `mean_motion_delta: 5.435`, active-frame ratio `0.625`.
  - Region diagnostics: rejected with `foot_shadow_or_contact_artifact_review: 9/9`, lower-body afterimage `4/9`, and structural hard failures.
- [x] Next bottleneck is start-frame suitability: the source entering Wan must already be animation-ready, side-view, leg-readable, and foot-readable.

## Non-Goals

- [x] Do not switch to rig/cutout animation to hide generation failures.
- [x] Do not treat visible foot-guide/control-map overlays as the new mainline; they worsened generated output or failed to affect it.
- [x] Do not spend more effort polishing the rejected long-source candidate unless a new generation-side probe first lowers lower-body and foot/contact artifacts.
- [x] Do not run expensive 120-frame Wan generations from back-biased, foot-ambiguous, or guide-contaminated start frames.
- [x] Do not use LocalVL as the sole adoption gate; deterministic gates and Agent visual review remain primary.
- [x] Do not revisit `WanAnimateToVideo` until the pose/control video is calibrated enough to preserve identity and avoid silhouette collapse.

## Acceptance Gates

- [x] Start-frame gate rejects likely back/rear views, guide/panel residue, high background contamination, merged legs, unreadable shoes, and clothing that hides the lower legs.
- [x] Short Wan probe gate requires motion readability pass, no structural hard failures, and substantially reduced foot/contact labels before 120-frame promotion.
- [ ] Region diagnostics target for a short walk proof: foot/contact labels below 30% of frames and lower-body afterimage labels below 30% of frames.
- [ ] Full-source adoption requires 120 frames, preview GIF, contact sheet, manifest, motion readability report, region diagnostics, artifact gate, LocalVL secondary report, and Agent visual review.
- [x] Packaged output must retain manifest status; rejected probes may be packaged only as evidence, not final assets.

## Phase 1: Animation-Ready Start-Frame Generator

- [x] Add or update a script for generating multiple 1024px start-frame candidates from a reference image using `novaOrangeXL`.
- [x] Candidate prompt must request a 2D game sprite start frame, not an illustration pose:
  - strict side view facing right;
  - full body visible from head to shoes;
  - face visible in profile;
  - legs separated and readable;
  - shoes separated and readable;
  - no cloak, skirt, coat, weapon, hand, or shadow merging with the lower legs;
  - clean white background;
  - single character only.
- [x] Negative prompt must explicitly reject back view, rear view, front view, model sheet, multiple figures, cropped feet, merged legs, long cloak covering legs, guide lines, panels, background scenery, afterimages, and motion blur.
- [x] Generate at least 10 candidates per reference/action attempt.
  - Run: `outputs/20260613_170538/fullbody_reference/comfyui2025_131891_trim/reference_candidates_report.json`.
  - Result: 10 candidates generated, but no `candidate_ok` start frame was found.
- [x] Save all candidates under one timestamp session with `run_profile.json`, `memo.md`, source prompt, workflow JSON, generated PNGs, cleaned PNGs, and contact sheets.
- [x] Record candidate-level seed, prompt, checkpoint, ControlNet settings if used, and selection gate result.

## Phase 2: Start-Frame Gate Strengthening

- [x] Extend `prepare_clean_start_frame()` or a companion gate to score lower-body animation readiness.
- [x] Add metrics for separated feet:
  - estimated foot-zone component count;
  - shoe/foot horizontal separation;
  - foot-zone foreground width;
  - lower-leg visibility ratio.
- [x] Add metrics for clothing occlusion over lower legs:
  - lower-body foreground mass dominated by torso/cloak color;
  - foot-zone too narrow or merged;
  - shoe region missing or near-background.
- [x] Add `issue_codes` for `feet_not_separated`, `shoes_unreadable`, `lower_legs_occluded`, and `foot_zone_merged`.
- [x] Add tests with synthetic side-view frames that pass/fail the new lower-body gate.
- [x] Update full-body candidate selection so any new lower-body start-frame issue is a hard failure.

## Phase 3: Candidate Selection Review Package

- [x] Build a compact review report for start-frame candidates.
- [x] Include source reference, generated candidate sheet, cleaned candidate sheet, start-frame debug sheets, and gate JSON.
- [x] Rank candidates by:
  - no hard start-frame issues;
  - profile detail pass;
  - separated feet pass;
  - readable shoes pass;
  - low background contamination;
  - no guide/panel residue.
- [x] Mark selected candidate as `start_frame_candidate_only`, not an adopted animation asset.
- [x] Add Agent visual review notes to `memo.md`: side-view confidence, foot readability, lower-leg occlusion, and expected walk suitability.
  - Agent review: selected candidate is not Wan-promotion-ready; it is front-biased and still has `shoes_unreadable`.

## Phase 4: Short Wan Probe Loop

- [x] Do not run Wan from the latest selected start frame because the start-frame gate did not produce `candidate_ok`.
- [x] Run only short probes first: `length=9`, then `length=17` if the 9-frame probe is promising.
  - Ran only diagnostic `length=9` probes from the new visually promising but gate-warning start frame; do not promote.
- [x] Use prompt E as the baseline wording:
  - slow walk-in-place;
  - separated feet;
  - sharp lower legs;
  - crisp shoes;
  - no cloak/leg blending;
  - no foot smears.
- [ ] Run at least two seeds for any promising start-frame candidate.
- [x] Gate each probe with:
  - `select_best_span.py --action walk --motion-metric foreground`;
  - `analyze_sprite_regions.py`;
  - `repair_frame_artifacts.py --mask-only`;
  - Agent contact-sheet and GIF review.
- [ ] Reject near-static seed repeats even if artifact jitter is low.
- [x] Reject probes with persistent foot/contact labels or lower-body afterimage labels above threshold.
  - `wan22_fun_control` no-foot-guide probe rejected: region foot/contact `5/9`, silhouette jitter `5/9`, artifact gate `retake_required: 9/9`.
  - `wan22_fun_control --foot-guide walk` probe rejected: region foot/contact `9/9`, guide leakage `7/9`, artifact gate `retake_required: 9/9`.
- [x] Record all rejected probes as evidence inside timestamped `outputs/<timestamp>/...` sessions.

## Phase 5: Lower-Body / Foot Control Sidecar

- [x] Design a simple lower-body control sidecar before returning to heavy model changes.
- [x] Prototype foot-contact guide images for walk:
  - left/right shoe target zones;
  - ground-contact baseline;
  - small stride envelope;
  - no full-body silhouette overconstraint.
- [x] Add an optional `--foot-guide` or equivalent input path to the Wan probe workflow if the local ComfyUI nodes support an appropriate control path.
  - Implemented `--foot-guide walk` for control-video routes by overlaying reusable lower-body foot/contact guides on pose control frames.
  - Reusable guide assets: `foot_guides/walk/contact_sheet.png`, `foot_guides/walk/control/frame_000.png`, `foot_guides/walk/frame_000.json`.
  - Unit coverage: `tests/test_foot_guides.py`, `tests/test_wan_walk_i2v_script.py`.
- [x] Compare control baseline vs foot-guide short probes on the same start frame and seed.
  - VACE route: no-foot-guide and foot-guide outputs were byte-identical and nearly blank/white; route remains rejected for this setup.
  - `wan22_fun_control` route: foot guide changed output but leaked visibly into frames and worsened foot/contact labels.
- [x] Adopt the foot-guide path only if it reduces foot/contact labels without silhouette collapse or identity loss.
  - Decision: do not adopt the current visible foot-guide overlay. It should become a mask/latent/control hint that cannot be rendered as an in-frame object, or be replaced by a better local video-control route.

## Phase 6: 120-Frame Promotion

- [ ] Promote to 120 frames only after at least one short probe passes all short-probe gates and one seed repeat remains readable.
- [ ] If the local Wan workflow requires 121 generated frames, trim or normalize the generated source to the requested 120-frame asset source before adoption.
- [ ] Keep the selected short probe and 120-frame source in the same timestamp session or link them explicitly in `memo.md`.
- [ ] Run the standardized E2E flow:
  - stabilization;
  - motion readability;
  - region diagnostics;
  - artifact gate;
  - LocalVL secondary evaluation;
  - packaging;
  - Godot playback check if available.
- [ ] Reject the 120-frame source if foot/contact or lower-body issues return at scale.
- [ ] Package as `adopted_animation_candidate` only if deterministic gates and Agent visual review agree.

## Phase 7: Return To Single-Keyframe Wan I2V Mainline

- [ ] Reproduce the historical best `phase10_single_keyframe_wan_i2v` route under the current `outputs/<timestamp>/...` output policy.
  - Benchmark: `review_packages/phase10_single_keyframe_wan_i2v_len121_strict_selected_proof_review_20260612_130832`.
  - Use single full-body side-view start/reference image only; do not add visible pose/control/foot-guide overlays.
  - Use the best current walk prompt wording as the baseline: slow side-view walk, separated feet, sharp lower legs, crisp shoes, no leg blending, no foot smears.
- [ ] Identify the exact historical phase10 settings before rerun.
  - Locate source generation report, workflow JSON, prompt, negative prompt, seed, width/height, length, fps, steps, cfg, sampler, scheduler, Wan model, VAE, CLIP, and start image.
  - Record any missing settings explicitly in `docs/walk_candidate_comparison.md`.
  - Prefer exact reproduction before changing parameters.
- [ ] Select or regenerate a clean full-body side-view start image for the rerun.
  - First try the historical phase10 start image if it is still available.
  - If unavailable, use the best current contact-pose start frame only after `prepare_clean_start_frame()` passes without lower-body hard failures.
  - Reject bust-up, back view, front view, model-sheet, panel residue, guide residue, merged feet, and unreadable shoes before Wan.
- [ ] Run a short single-keyframe Wan i2v probe before full source.
  - Start with `length=17` or `length=33`, not 120.
  - Run at least two seeds if the first short probe is promising.
  - Keep all outputs in `outputs/<timestamp>/wan_walk_i2v/<label>/`.
- [ ] Gate every short probe before promotion.
  - Run `select_best_span.py --action walk --motion-metric foreground`.
  - Run `analyze_sprite_regions.py`.
  - Run `repair_frame_artifacts.py --mask-only`.
  - Review `preview.gif` and `contact_sheet.png` manually as Agent visual review.
  - Reject probes that are near-static, lose identity, drift into front/back view, or show recurring double feet.
- [ ] Promote only a passing short probe to 120-frame source generation.
  - If the Wan node emits 121 frames, save the raw model output as evidence but normalize the candidate source to exactly 120 frames before adoption review.
  - Keep raw source, normalized 120-frame source, preview GIF, contact sheet, and reports in the same timestamp session or cross-link them in `memo.md`.
- [ ] Run full-source deterministic gates on the 120-frame candidate.
  - Stabilization/color-luma report.
  - Motion readability report.
  - Region diagnostics.
  - Artifact mask-only gate.
  - LocalVL as secondary semantic/action check.
  - Godot playback validation if available.
- [ ] Apply postprocess only to issues that postprocess can plausibly fix.
  - Allowed: luma/saturation jitter, dirty background, tiny specks, small residual ghosts, 1024 img2img polish after action readability is already good.
  - Not allowed as postprocess-only fixes: double feet, duplicated lower legs, guide/control burn-in, identity collapse, silhouette collapse, major lower-body redraw, or unreadable walking motion.
- [ ] Run focused postprocess PDCA on the best full-source candidate.
  - Test color/luma stabilization first.
  - Test 1024 img2img polish with conservative denoise around the known useful range, starting near `0.35`.
  - Gate each refined version with the same artifact and region diagnostics.
  - Keep the unrefined candidate as baseline for side-by-side comparison.
- [ ] Decide final status honestly.
  - `adopted_animation_candidate` only if 120-frame source passes deterministic gates and Agent visual review.
  - `selected_proof_only` if a strong span exists but full 120-frame source fails.
  - `rejected_diagnostic` if route/settings create guide burn-in, identity loss, or structural leg failures.

## Phase 8: Lower-Body Afterimage Retake Strategy

- [ ] Treat recurring pale lower-body afterimages as the primary blocker for the single-keyframe route.
- [ ] Build a small comparison matrix for the next retakes.
  - start image crop/framing: historical phase10 crop vs current contact-pose crop.
  - resolution: 768 baseline vs one 1024 short probe only after 768 is promising.
  - prompt: prompt E baseline vs stricter "no translucent lower body / no pale ghost legs" variant.
  - seed: at least two seeds for any promising setting.
- [ ] Avoid visible control-map fixes unless they can be proven not to render into the output.
  - Do not use `--foot-guide walk` as visible overlay for adoption attempts.
  - Do not use VACE/Wan22Fun as mainline unless a probe beats single-keyframe Wan i2v on identity, motion, and artifact gates.
- [ ] Record every retake in `docs/walk_candidate_comparison.md`.
  - Include route, start image, resolution, length, motion score, gate summary, visual decision, and next action.
  - Mark clearly whether each candidate is `adopted_animation_candidate`, `selected_proof_only`, or `rejected_diagnostic`.

## Phase 9: Knowledge Capture

- [x] Update `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md` with accepted and rejected start-frame patterns.
- [x] Record route-level lesson from the latest correction.
  - Keep `single-keyframe Wan i2v` as the current walk mainline.
  - Treat `VACE`, `Wan22Fun`, and visible `--foot-guide walk` as diagnostic/control experiments unless they beat the single-keyframe route on identity, motion, and artifact gates.
  - Use postprocess for color/luma/background polish only after action and identity already read correctly.
  - Use retake, not postprocess, for double feet, guide leakage, control-map burn-in, major lower-body redraw, or character-preservation failure.
- [x] Record start-frame prompt variants that reliably produce animation-ready lower bodies.
  - Current result: none found in the 10-candidate `ComfyUI2025_131891_trim` run.
- [x] Record start-frame prompt variants that produce back-biased, cloak-occluded, or foot-ambiguous candidates.
  - Report: `docs/start_frame_first_walk_pdca.md`.
- [x] Record whether foot-guide sidecar improves or worsens Wan output.
  - Current result: worsens `wan22_fun_control` and has no observable effect on the tested VACE route.
- [x] Keep a concise best/current evidence table in a report doc so `outputs/<timestamp>/...` remains navigable.
  - Current report: `docs/start_frame_first_walk_pdca.md`.

## Current Best / Evidence Pointers

- [x] Best historical walk proof remains rejected/limited; no adopted 2D game walk asset exists yet.
  - Current best route: `single-keyframe Wan i2v`, not visible control-map or foot-guide overlay.
  - Best proof package: `review_packages/phase10_single_keyframe_wan_i2v_len121_strict_selected_proof_review_20260612_130832`.
  - Best comparison table: `docs/walk_candidate_comparison.md`.
- [x] Latest normalized-start probe evidence:
  - start gate: `outputs/20260613_120808/wan_start_frame/phase7_face_visible_side_start_gate/start_frame_report.json`;
  - Wan probe: `outputs/20260613_120834/wan_walk_i2v/phase7_start_norm_prompt_e_len9_probe/`;
  - motion gate: `outputs/20260613_120921/span_selection/phase7_start_norm_prompt_e_len9_motion_gate/span_selection_report.json`;
  - region diagnostics: `outputs/20260613_120921/region_diagnostics/phase7_start_norm_prompt_e_len9_regions/region_diagnostics_report.json`.
- [x] Latest start-frame-first candidate evidence:
  - report: `docs/start_frame_first_walk_pdca.md`;
  - generation: `outputs/20260613_170538/fullbody_reference/comfyui2025_131891_trim/reference_candidates_report.json`;
  - selected best candidate: `outputs/20260613_170538/fullbody_reference/comfyui2025_131891_trim/selected_reference/start_frame.png`;
  - result: no candidate passed as `candidate_ok`; do not promote to Wan.
- [x] Latest contact-pose start-frame retake evidence:
  - generation: `outputs/20260613_174107/fullbody_reference/comfyui2025_131891_trim/reference_candidates_report.json`;
  - selected best candidate: `outputs/20260613_174107/fullbody_reference/comfyui2025_131891_trim/selected_reference/start_frame.png`;
  - result: visually better side-view/contact pose, but 512 start-frame gate still warns `shoes_unreadable`; use only for diagnostic short probes.
- [x] Latest foot-guide comparison evidence:
  - VACE no guide: `outputs/20260613_175024/wan_walk_i2v/phase_start_contact_vace_len9_no_footguide/`;
  - VACE foot guide: `outputs/20260613_175658/wan_walk_i2v/phase_start_contact_vace_len9_footguide/`;
  - Wan22Fun no guide: `outputs/20260613_175828/wan_walk_i2v/phase_start_contact_wan22fun_len9_no_footguide/`;
  - Wan22Fun foot guide: `outputs/20260613_175907/wan_walk_i2v/phase_start_contact_wan22fun_len9_footguide/`;
  - region/mask gates: `outputs/20260613_180002/region_diagnostics/`, `outputs/20260613_180046/artifact_repair/`;
  - result: all rejected; current visible foot guide is not an adoption path.
