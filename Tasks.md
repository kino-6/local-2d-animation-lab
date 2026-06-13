# Tasks: Walk-Ready Full-Body Start Reference Gate

Archived checkpoint:

```text
docs/archive/Tasks_20260614_sidecar_suitable_lower_body_control_probe_completed.md
```

Cleanup report:

```text
docs/output_cleanup_20260614_lineart_sidecar_probe.md
```

## Rules

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet.
- [x] Save all new generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Target adopted animation source length is 120 frames; short probes are evidence only.
- [x] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [x] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, shoe recolor, composition collapse, or identity drift are visible.

## Current Interpretation

- [x] OpenPose-only cannot carry toe, heel, or foot-box semantics into generated shoes/contact.
- [x] OpenPose-family secondary sidecar is not enough.
- [x] Lineart sidecar is installable and active, but does not fix walk quality when the reference/start composition is not already sprite-compatible.
- [x] The next bottleneck is start/reference suitability:
  - full-body;
  - side-view or near side-view;
  - walk-cycle contact pose;
  - separated readable shoes;
  - clean white or transparent background;
  - no model-sheet/turnaround/secondary-character artifacts.

## Plan

The next mechanism is not another sidecar strength sweep. It is a stricter start-reference gate:

```text
input design reference
-> generate multiple full-body side-view walk-ready start candidates
-> deterministic start-frame gate
-> Agent visual review
-> only then run short walk animation probe
```

If no candidate passes the start-frame gate, do not run animation generation. Record the blocker and improve candidate generation/gating.

Primary input for this loop:

- `assets/reference/Anima_00013_.png`

Secondary input only if needed:

- `assets/reference/ComfyUI2025_131891_trim.png`

## Active PDCA

- [x] Cleanup stale local outputs.
  - Archive old `Tasks.md`.
  - Write `docs/output_cleanup_20260614_lineart_sidecar_probe.md`.
  - Delete stale lineart sidecar `outputs/20260613_*` sessions after durable findings are recorded.
- [x] Review the existing start-frame generation route.
  - `scripts/generate_fullbody_reference_candidates.py`.
  - `natural_sprite_lab.quality.start_frame.prepare_clean_start_frame`.
  - Existing tests around full-body/reference/start-frame readiness.
- [x] Tighten start-reference assessment if needed.
  - Require full-body bbox height and foot-near-bottom checks.
  - Penalize too-wide/front-view/model-sheet compositions.
  - Keep lower-body hard issues blocking:
    - `feet_not_separated`
    - `shoes_unreadable`
    - `lower_legs_occluded`
    - `foot_zone_merged`
    - `possible_back_view_or_missing_profile_detail`
    - `guide_or_panel_residue`
    - `background_contamination_high`
  - Add unit tests for any changed gate behavior.
- [x] Generate fresh full-body side-view start candidates.
  - Use `novaOrangeXL_v120.safetensors`.
  - Use `SDXL\OpenPoseXL2.safetensors`.
  - Check ComfyUI `/queue` before submitting.
  - Generate under `outputs/<timestamp>/fullbody_reference/...`.
  - Do not reuse deleted `outputs/` paths.
- [x] Agent visual review of candidate sheets.
  - Inspect `contact_sheet.png`, `source_contact_sheet.png`, and selected `start_frame.png`.
  - Record:
    - side-view confidence;
    - foot readability;
    - lower-leg occlusion;
    - background cleanliness;
    - expected walk suitability.
- [x] Decide whether animation probing is allowed.
  - If no candidate is visually walk-ready, stop at `blocked_start_reference_quality`.
  - If one candidate is plausible but gated with minor warnings, run one short 8-frame diagnostic only.
  - Do not run 120 frames in this loop.
- [x] Optional short diagnostic if allowed.
  - Rebuild synthetic side-view walk source from code.
  - Use the selected start frame as the reference.
  - Run either:
    - plain IPAdapterAdvanced + OpenPose upper-body-mask route; or
    - lineart sidecar at low strength only if the start frame already passes visual review.
  - Gate and visually review.
- [x] Update durable knowledge.
  - `docs/start_frame_first_walk_pdca.md`.
  - `docs/reference_lock_motion_template_deep_dive.md`.
  - `docs/walk_candidate_comparison.md`.
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`.
  - `Tasks.md` final result.

## Success Criteria

- [x] Old output clutter is removed after knowledge capture.
- [x] Tests pass for touched code.
- [x] A fresh start-reference report exists under `outputs/<timestamp>/...`, or a blocker is recorded.
- [x] No animation generation is run from an obviously bad start/reference.
- [x] Result is labeled honestly as one of:
  - `start_reference_candidate_only`;
  - `selected_proof_only`;
  - `blocked_start_reference_quality`;
  - `rejected_diagnostic`.

## Result

- [x] Queue behavior:
  - First generation attempt waited `120s` and timed out at queue size `17`.
  - No prompt was submitted during that failed wait.
  - The stale failed-wait output session was deleted.
  - Second attempt waited until queue capacity was acceptable and completed.
- [x] Tests:
  - `uv run pytest tests\test_fullbody_reference_candidates_script.py tests\test_start_frame_quality.py tests\test_output_layout_policy.py`
  - `17 passed`
- [x] Implementation:
  - `scripts/generate_fullbody_reference_candidates.py` now records `animation_probe_allowed`.
  - If selected candidate is not `candidate_ok`, the selected report records `blocking_status: blocked_start_reference_quality`.
  - `foreground_too_wide_for_side_reference` is now a blocking assessment issue.
- [x] Fresh start-reference run:
  - `outputs/20260614_000549/fullbody_reference/anima_00013/`
  - report: `outputs/20260614_000549/fullbody_reference/anima_00013/reference_candidates_report.json`
  - contact sheet: `outputs/20260614_000549/fullbody_reference/anima_00013/contact_sheet.png`
  - selected: `outputs/20260614_000549/fullbody_reference/anima_00013/selected_reference/start_frame.png`
- [x] Candidate result:
  - no `candidate_ok` among 10 candidates.
  - selected candidate: `slight_three_quarter_side`
  - selected status: `manual_review_or_retake`
  - selected issues:
    - `extra_foreground_components_removed`
    - `large_secondary_component`
    - `shoes_unreadable`
  - lower-body readiness:
    - `foot_component_count: 2`
    - `lower_leg_component_count: 2`
    - `foot_separation_ratio: 0.22305`
    - `foot_zone_coverage: 0.0135`
    - `lower_leg_visibility_ratio: 0.02585`
- [x] Agent visual review:
  - selected candidate is a decent still illustration;
  - not walk-ready because it is front-facing/near-front;
  - shoes and lower legs are not reliable enough for 2D walk animation;
  - several side-facing candidates in the sheet still have model-sheet residue, secondary components, foot ambiguity, or non-walk composition.
- [x] Decision:
  - `blocked_start_reference_quality`
- [x] Next action:
  - Do not run animation from this selected candidate.
  - Improve candidate generation prompts and/or add a reference-gate LocalVL pass before any animation spend.
