# Start-Frame-First Walk PDCA

Date: 2026-06-13

## Purpose

Improve the walking asset pipeline by moving the main quality gate earlier: before Wan i2v, generate and select an animation-ready 2D game start frame with readable side-view legs and shoes.

## Run

- Reference: `assets/reference/ComfyUI2025_131891_trim.png`
- Candidate generation report: `outputs/20260613_170538/fullbody_reference/comfyui2025_131891_trim/reference_candidates_report.json`
- Candidate contact sheet: `outputs/20260613_170538/fullbody_reference/comfyui2025_131891_trim/contact_sheet.png`
- Selected best candidate: `outputs/20260613_170538/fullbody_reference/comfyui2025_131891_trim/selected_reference/start_frame.png`

## Result

The workflow produced 10 candidates and recorded prompt, seed, workflow, cleaned image, debug sheet, start-frame gate, and selection data in one timestamp session.

No candidate passed as an adoption-ready walking start frame. The best-ranked candidate was `walk_ready_clear_lower_legs`, but it remained `manual_review_or_retake` with `shoes_unreadable`.

## Candidate Findings

- Prompts that emphasized clear lower legs did improve face/profile and separated-foot geometry in some candidates.
- The model still often drifts into front view, rear view, model-sheet layouts, or side-view illustrations with poor foot readability.
- The current gate correctly surfaces lower-body blockers: merged feet, unreadable shoes, background contamination, duplicate silhouettes, and large secondary components.
- The generated candidates are useful as evidence, but not ready for Wan promotion.

## Next Action

Do not run Wan from this selected candidate yet. Tighten the start-frame prompt and/or add a lower-body/foot control sidecar before the next generation attempt.

Specific prompt changes to test next:

- Replace "standing pose" with "walk-cycle neutral contact pose".
- Explicitly request "both shoes on ground, separated by white space, side-view shoe silhouettes".
- Avoid "school skirt hides knees"; request "short skirt above knees, knees and lower legs visible".
- Reject "front-facing full-body portrait" and "character design sheet" more strongly.

Specific gate changes to consider:

- Add a side-view/front-view classifier signal, possibly LocalVL secondary check.
- Penalize candidates whose torso is front-facing even when the face is profile.
- Require two shoe components with enough dark/shoe-colored area, not just two foot-zone components.

## Foot Guide Sidecar

Implemented a reusable walk foot-contact guide as a lower-body-only control sidecar.

- Guide contact sheet: `foot_guides/walk/contact_sheet.png`
- Per-frame guide JSON: `foot_guides/walk/frame_000.json` through `frame_119.json`
- Per-frame control images: `foot_guides/walk/control/frame_000.png` through `frame_119.png`
- Wan integration: `scripts/run_wan_walk_i2v.py --foot-guide walk` overlays the guide on control-video frames for modes such as `animate_pose`, `vace`, and `fun_control`.

This was tested and is not adopted in its current visible-overlay form.

Matched short-probe comparison:

- VACE no-guide probe: `outputs/20260613_175024/wan_walk_i2v/phase_start_contact_vace_len9_no_footguide/`
- VACE foot-guide probe: `outputs/20260613_175658/wan_walk_i2v/phase_start_contact_vace_len9_footguide/`
- Wan22Fun no-guide probe: `outputs/20260613_175828/wan_walk_i2v/phase_start_contact_wan22fun_len9_no_footguide/`
- Wan22Fun foot-guide probe: `outputs/20260613_175907/wan_walk_i2v/phase_start_contact_wan22fun_len9_footguide/`
- Region diagnostics: `outputs/20260613_180002/region_diagnostics/`
- Mask-only artifact gates: `outputs/20260613_180046/artifact_repair/`

Results:

- VACE route: both outputs were byte-identical and nearly blank/white. The route did not preserve the character and did not respond meaningfully to the foot guide.
- Wan22Fun route: produced visible motion, but rendered the control map instead of the character. The foot guide leaked into the frame as a visible object and worsened region diagnostics.
- No-guide Wan22Fun region labels: `foot_shadow_or_contact_artifact_review: 5/9`, `silhouette_redraw_jitter_review: 5/9`.
- Foot-guide Wan22Fun region labels: `foot_shadow_or_contact_artifact_review: 9/9`, `silhouette_redraw_jitter_review: 6/9`, `lower_body_pale_afterimage_review: 2/9`.
- Mask-only artifact gate rejected both: `retake_required: 9/9`.

Decision:

Do not adopt the current foot-guide overlay. The idea remains useful, but the guide must not be visible as rendered pixels. Next attempts should either inject the lower-body constraint through a non-rendered mask/latent/control channel, or use a video-control workflow that preserves the reference character while treating control images as guidance rather than content.

## Contact-Pose Start-Frame Retake

After replacing "standing pose" prompt language with "walk-cycle neutral contact pose", the generator produced a stronger visual candidate:

- Run: `outputs/20260613_174107/fullbody_reference/comfyui2025_131891_trim/reference_candidates_report.json`
- Selected candidate: `outputs/20260613_174107/fullbody_reference/comfyui2025_131891_trim/selected_reference/start_frame.png`
- Selected status: `manual_review_or_retake`
- Main issue: at 512px Wan normalization, the start-frame gate still reports `shoes_unreadable`.

This candidate is useful diagnostic evidence because side-view, foot separation, and contact pose improved, but it is still not a 120-frame promotion start frame.

## Frame Count Correction

The asset target is 120 source frames. Earlier `121` labels came from local Wan/video workflow convenience and loop-endpoint experiments. Treat any 121-frame generation as an implementation artifact; trim or normalize to 120 frames before adoption. Frame thinning remains a separate later Skill.

## Mainline Correction

The foot-guide/control-map experiment should not replace the earlier best route. It was useful as a diagnostic, but it produced worse assets than the historical single-keyframe Wan i2v branch.

Current working interpretation:

- Mainline: single-keyframe Wan i2v from a clean full-body side-view reference.
- Historical benchmark: `review_packages/phase10_single_keyframe_wan_i2v_len121_strict_selected_proof_review_20260612_130832`.
- Benchmark strength: better identity preservation, readable walking motion, and no visible control-map burn-in.
- Benchmark blocker: recurring pale lower-body afterimages and foot/contact artifacts.
- Rejected side route: visible foot-guide/control overlays, because they either did not affect output or became visible artifacts.

Next work should reproduce and improve the single-keyframe route under the current `outputs/<timestamp>/...` layout, then apply postprocess only to the parts postprocess can actually fix: luma/saturation jitter, background cleanup, small residual ghosts, and 1024 img2img polish after action readability is already acceptable.

## 2026-06-14 Anima Start-Reference Gate

Run:

- Reference: `assets/reference/Anima_00013_.png`
- Candidate generation report: `outputs/20260614_000549/fullbody_reference/anima_00013/reference_candidates_report.json`
- Candidate contact sheet: `outputs/20260614_000549/fullbody_reference/anima_00013/contact_sheet.png`
- Selected candidate: `outputs/20260614_000549/fullbody_reference/anima_00013/selected_reference/start_frame.png`

Operational note:

- The first attempt waited for ComfyUI queue capacity and timed out at queue size `17`; no prompt was submitted.
- The second attempt waited until queue capacity was acceptable and completed.
- The failed queue-wait session was deleted; only the successful evidence session remains.

Result:

- All 10 candidates were `manual_review_or_retake`; no `candidate_ok` start frame was found.
- Auto-selected candidate: `slight_three_quarter_side`.
- Selected issues:
  - `extra_foreground_components_removed`
  - `large_secondary_component`
  - `shoes_unreadable`
- Lower-body metrics:
  - `foot_component_count: 2`
  - `lower_leg_component_count: 2`
  - `foot_separation_ratio: 0.22305`
  - `foot_zone_coverage: 0.0135`
  - `lower_leg_visibility_ratio: 0.02585`

Agent visual review:

- The selected candidate is clean enough as an illustration, but not walk-ready.
- It is front-facing/near-front rather than side-view.
- Shoes and lower legs are present, but not readable enough for a game walk start.
- Several visually side-facing candidates exist in the sheet, but they have model-sheet/secondary-component residue, foot ambiguity, or non-walk composition.

Implementation update:

- `scripts/generate_fullbody_reference_candidates.py` now records `animation_probe_allowed`.
- If the selected candidate is not `candidate_ok`, the report marks `blocked_start_reference_quality`.
- `foreground_too_wide_for_side_reference` is now a blocking assessment issue.

Decision:

```text
blocked_start_reference_quality
```

Do not run animation generation from this selected candidate. The next improvement should target candidate generation itself: stricter side-profile prompt variants, fewer model-sheet cues, and stronger rejection of front-view full-body portraits before animation spend.

## 2026-06-14 Start-Reference Retake + LocalVL

Run:

- Reference: `assets/reference/Anima_00013_.png`
- Candidate generation report: `outputs/20260614_001954/fullbody_reference/anima_00013/reference_candidates_report.json`
- Candidate contact sheet: `outputs/20260614_001954/fullbody_reference/anima_00013/contact_sheet.png`
- Selected candidate: `outputs/20260614_001954/fullbody_reference/anima_00013/selected_reference/start_frame.png`
- LocalVL review: `outputs/20260614_002335/local_vl_eval/anima_start_reference_retake_vl/start_reference_vl_eval.json`

Changes:

- Added stricter prompt variants:
  - `profile_walk_contact_no_portrait`
  - `small_stride_side_walk_sprite`
- Strengthened negative prompt against props, bicycles, front-facing portraits, hidden shoes, and looking-at-viewer still portrait bias.
- Added a start-reference LocalVL evaluator:
  - `scripts/evaluate_start_reference_with_ollama_vl.py`
  - role: `secondary_start_reference_review`
  - output: `start_reference_vl_eval.json`

Result:

- 12 candidates were generated.
- No candidate reached `candidate_ok`.
- Auto-selected candidate: `strict_side_profile`.
- Selected status: `manual_review_or_retake`.
- Blocking issue: `shoes_unreadable`.
- `animation_probe_allowed: false`.

Lower-body metrics for the selected candidate:

- `foot_component_count: 2`
- `lower_leg_component_count: 1`
- `foot_separation_ratio: 0.53111`
- `foot_zone_coverage: 0.01584`
- `lower_leg_visibility_ratio: 0.02355`

Agent visual review:

- Better side-view composition than the previous front/near-front selection.
- Still not a walk-ready game start frame because the shoe/contact zone is unreliable and the stance is not a clear walk-contact pose.
- Candidate `side_profile_shoes_apart` and `small_stride_side_walk_sprite` are visually interesting, but still carry deterministic issues, so they are evidence, not animation inputs.

LocalVL result:

- `is_walk_ready_start_reference: false`
- blocking reasons:
  - `deterministic_selection_not_candidate_ok`
  - `deterministic_shoes_unreadable`
  - `local_vl_low_shoe_readability_score`
  - `local_vl_low_side_view_score`
  - `local_vl_low_walk_contact_score`

Decision:

```text
blocked_start_reference_quality
```

Do not run animation from this selected candidate. The retake improved side-view composition but did not solve the shoe/contact gate. The next useful change is to condition candidate generation directly on clearer lower-body/foot structure, not to keep asking text alone for shoes.

## 2026-06-14 Lower-Body Sidecar Start-Reference Probe

Run:

- Reference: `assets/reference/Anima_00013_.png`
- Candidate generation report: `outputs/20260614_005144/fullbody_reference/anima_00013/reference_candidates_report.json`
- Candidate contact sheet: `outputs/20260614_005144/fullbody_reference/anima_00013/contact_sheet.png`
- LocalVL review: `outputs/20260614_010050/local_vl_eval/anima_sidecar_start_reference_vl/start_reference_vl_eval.json`

Changes:

- Added optional lower-body/foot lineart sidecar support to `scripts/generate_fullbody_reference_candidates.py`.
- Used `SDXL\t2i-adapter_diffusers_xl_lineart.safetensors` at low strength (`0.16`, end `0.45`) after OpenPose.
- Added tests for sidecar workflow wiring and sidecar image generation.

Result:

- 12 candidates were generated.
- 1 candidate reached deterministic `candidate_ok`.
- Auto-selected candidate: `small_stride_side_walk_sprite`.
- Selected status: `candidate_ok`.
- `animation_probe_allowed: true`.

Selected lower-body metrics:

- `foot_component_count: 2`
- `lower_leg_component_count: 2`
- `foot_separation_ratio: 0.50163`
- `foot_zone_coverage: 0.01894`
- `lower_leg_visibility_ratio: 0.02517`

Agent visual review:

- The selected still is much better than prior Anima start-reference attempts.
- It is full-body, right-facing, and the two shoes are readable.
- The stride is conservative, so the correct status is probe input, not adopted animation source.

Important implementation boundary:

- Re-cleaning the selected cleaned preview can make it fail with `shoes_unreadable`.
- Wan probes should use the generated source image or the recorded `animation_probe_start_image`, so start-frame normalization happens exactly once.
