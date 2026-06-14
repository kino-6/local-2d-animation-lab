# Tasks: Conservative Walk Endpoint Gate

Archived checkpoint:

```text
docs/archive/Tasks_20260614_wan_preservation_sweep_from_sidecar_start_completed.md
```

Cleanup report:

```text
docs/output_cleanup_20260614_wan_preservation_sweep.md
```

Retained start source:

```text
assets/reference/generated/anima_00013_sidecar_walk_start_source_20260614.png
```

## Rules

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet.
- [x] Save all new generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Keep `outputs/` free of loose files and stale diagnostic runs after durable findings are recorded.
- [x] Target adopted animation source length is 120 frames; short probes are evidence only.
- [x] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [x] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, shoe unreadability, front-view drift, model-sheet residue, composition collapse, or identity drift are visible.
- [x] LocalVL must not override deterministic artifact gates or Agent visual rejection.

## Current Interpretation

- [x] A better start-reference exists, but plain Wan i2v still damages lower-body structure.
- [x] Scalar-only Wan setting sweeps are not the next main route.
- [x] First/last Wan can help action intent only if the endpoint is conservative, side-view, full-body, clean, and close to the start framing.
- [x] Existing endpoint tooling has `run`, `hit`, and `attack` actions, but walk needs a smaller `walk_stride` endpoint rather than a dramatic run keyframe.
- [x] The next loop should gate the endpoint before any first/last video spend.

## Plan

Primary route:

```text
retained sidecar start source
-> conservative walk_stride endpoint candidate
-> endpoint deterministic gate
-> Agent endpoint review
-> first/last Wan short probe only if endpoint passes
-> standard quality flow
```

If the endpoint is not clean and action-bearing, stop before first/last Wan.

## Active PDCA

- [x] Archive the previous completed `Tasks.md`.
- [x] Write cleanup findings for current local output runs.
- [x] Delete reviewed `outputs/` runs after path safety checks.
- [x] Add `walk_stride` to `scripts/generate_action_keyframe_candidates.py`.
  - Keep prompt conservative: side-view opposite-contact walk pose, not run/high-kick.
  - Support reference-conditioned endpoint generation from the retained start source.
  - Gate endpoint with `source_delta` so clean-but-static endpoints do not pass.
- [x] Add/update tests for the new `walk_stride` endpoint action.
- [x] Run focused tests.
- [x] Generate `walk_stride` endpoint candidates from the retained start source.
- [x] Agent review endpoint contact sheet and selected endpoint.
- [x] If endpoint passes deterministic gate and visual review, run one short first/last Wan probe.
- [x] Run standardized quality flow for any successful first/last probe.
- [x] Update durable knowledge.
  - `docs/action_generalization_pdca_report.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
  - `Tasks.md`

## Success Criteria

- [x] Old output clutter is removed after knowledge capture.
- [x] Tests pass for touched code.
- [x] `walk_stride` endpoint generation exists, or queue/model blocker is recorded.
- [x] Endpoint is labeled honestly as one of:
  - `candidate_ok_for_first_last_probe`;
  - `blocked_endpoint_quality`;
  - `blocked_endpoint_delta_too_low`;
  - `blocked_comfyui_or_model_unavailable`.
- [x] No first/last Wan run occurs from a bad endpoint.
- [x] If first/last Wan runs, final result is labeled honestly as one of:
  - `selected_proof_only`;
  - `rejected_diagnostic`;
  - `rejected_animation_candidate`.
- [x] No 120-frame spend occurs in this loop.

## Result

- [x] Planning and cleanup commit:
  - `efcf061 Plan conservative walk endpoint gate`
- [x] Implemented `walk_stride` in:
  - `scripts/generate_action_keyframe_candidates.py`
- [x] Tests:
  - `uv run pytest tests\test_action_keyframe_candidates_script.py tests\test_fullbody_reference_candidates_script.py tests\test_output_layout_policy.py tests\test_start_frame_quality.py`
  - `25 passed`
- [x] Endpoint probe A, full img2img:
  - `outputs/20260614_100851/action_keyframes/anima_00013_walk_stride_keyframes/`
  - selected status: `manual_review_or_retake`
  - reason: `extra_foreground_components_removed`; visually too close to source.
- [x] Endpoint probe B, lower-body img2img:
  - `outputs/20260614_101109/action_keyframes/anima_00013_walk_stride_keyframes/`
  - selected status: deterministic `candidate_ok`
  - visual block: rear foot/lower leg becomes an oversized boot-like broken structure.
- [x] First/last Wan:
  - not run, because endpoint visual review failed.
- [x] Durable report:
  - `docs/conservative_walk_endpoint_gate_20260614.md`
- [x] Decision:
  - `blocked_endpoint_quality`

## Findings

- [x] `source_delta` alone is not enough; it can measure redraw amount rather than action-bearing pose change.
- [x] Lower-body endpoint editing can pass deterministic still-image gates while visually breaking the foot/lower leg.
- [x] First/last Wan remains gated until endpoint-specific lower-body/shoe-shape checks are implemented.
- [x] No 120-frame spend occurred.
