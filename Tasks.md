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

- [ ] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [ ] Treat the input image as a design reference, not pixels to directly puppet.
- [ ] Save all new generated run artifacts only under `outputs/<timestamp>/...`.
- [ ] Keep `outputs/` free of loose files and stale diagnostic runs after durable findings are recorded.
- [ ] Target adopted animation source length is 120 frames; short probes are evidence only.
- [ ] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [ ] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, shoe unreadability, front-view drift, model-sheet residue, composition collapse, or identity drift are visible.
- [ ] LocalVL must not override deterministic artifact gates or Agent visual rejection.

## Current Interpretation

- [ ] A better start-reference exists, but plain Wan i2v still damages lower-body structure.
- [ ] Scalar-only Wan setting sweeps are not the next main route.
- [ ] First/last Wan can help action intent only if the endpoint is conservative, side-view, full-body, clean, and close to the start framing.
- [ ] Existing endpoint tooling has `run`, `hit`, and `attack` actions, but walk needs a smaller `walk_stride` endpoint rather than a dramatic run keyframe.
- [ ] The next loop should gate the endpoint before any first/last video spend.

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

- [ ] Archive the previous completed `Tasks.md`.
- [ ] Write cleanup findings for current local output runs.
- [ ] Delete reviewed `outputs/` runs after path safety checks.
- [ ] Add `walk_stride` to `scripts/generate_action_keyframe_candidates.py`.
  - Keep prompt conservative: side-view opposite-contact walk pose, not run/high-kick.
  - Support reference-conditioned endpoint generation from the retained start source.
  - Gate endpoint with `source_delta` so clean-but-static endpoints do not pass.
- [ ] Add/update tests for the new `walk_stride` endpoint action.
- [ ] Run focused tests.
- [ ] Generate `walk_stride` endpoint candidates from the retained start source.
- [ ] Agent review endpoint contact sheet and selected endpoint.
- [ ] If endpoint passes deterministic gate and visual review, run one short first/last Wan probe.
- [ ] Run standardized quality flow for any successful first/last probe.
- [ ] Update durable knowledge.
  - `docs/action_generalization_pdca_report.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
  - `Tasks.md`

## Success Criteria

- [ ] Old output clutter is removed after knowledge capture.
- [ ] Tests pass for touched code.
- [ ] `walk_stride` endpoint generation exists, or queue/model blocker is recorded.
- [ ] Endpoint is labeled honestly as one of:
  - `candidate_ok_for_first_last_probe`;
  - `blocked_endpoint_quality`;
  - `blocked_endpoint_delta_too_low`;
  - `blocked_comfyui_or_model_unavailable`.
- [ ] No first/last Wan run occurs from a bad endpoint.
- [ ] If first/last Wan runs, final result is labeled honestly as one of:
  - `selected_proof_only`;
  - `rejected_diagnostic`;
  - `rejected_animation_candidate`.
- [ ] No 120-frame spend occurs in this loop.
