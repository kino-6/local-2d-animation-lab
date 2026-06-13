# Tasks: Wan Preservation Sweep From Sidecar Start

Archived checkpoint:

```text
docs/archive/Tasks_20260614_lower_body_sidecar_start_reference_probe_completed.md
```

Cleanup report:

```text
docs/output_cleanup_20260614_lower_body_sidecar_start_reference.md
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

- [ ] The start-reference stage has improved: lower-body lineart sidecar produced one deterministic `candidate_ok`.
- [ ] The new blocker is preservation through video generation.
- [ ] Plain Wan i2v from the improved source reads as walking but creates lower-body afterimages, recoloring/darkening, foot smears, and duplicate-silhouette risk.
- [ ] Double-cleaned selected previews are unsafe; Wan should receive the retained generated source so normalization happens exactly once.
- [ ] The next loop should compare a small number of Wan settings and post-Wan foreground separation, not regenerate start references again.

## Plan

Primary route:

```text
retained sidecar start source
-> short Wan i2v setting sweep
-> deterministic quality flow per candidate
-> Agent visual review
-> BiRefNet foreground separation for the best candidate
-> conservative masked/histogram correction only if it improves gates
```

No 120-frame generation in this loop unless a short proof genuinely passes artifact gate and visual review.

## Active PDCA

- [ ] Archive the previous completed `Tasks.md`.
- [ ] Write cleanup findings for the current local output runs.
- [ ] Retain only the minimal best start source outside `outputs/`.
- [ ] Delete reviewed `outputs/` runs after path safety checks.
- [ ] Run focused tests for touched code before generation.
- [ ] Check ComfyUI queue before each generation request.
- [ ] Run short Wan setting sweep from the retained start source.
  - Baseline from prior successful route.
  - Lower `shift`/`cfg` preservation variant.
  - Lower motion/ghosting variant if queue capacity allows.
- [ ] Run standardized quality flow for each successful short probe.
- [ ] Compare:
  - motion readability;
  - artifact gate status;
  - luma/saturation drift before and after stabilization;
  - lower-body afterimage labels;
  - foot/contact labels;
  - duplicate-silhouette risk.
- [ ] Agent visual review of the best contact sheet.
- [ ] If a best candidate exists, run BiRefNet foreground separation or foreground compositing on it.
- [ ] Re-run quality flow after BiRefNet or foreground stabilization.
- [ ] Update durable knowledge.
  - `docs/lower_body_sidecar_start_reference_pdca_20260614.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
  - `Tasks.md`

## Success Criteria

- [ ] Old output clutter is removed after knowledge capture.
- [ ] Tests pass for touched code.
- [ ] At least one short Wan probe is generated from the retained source, or queue/model blocker is recorded.
- [ ] Each generated probe has a standardized quality-flow decision.
- [ ] Best candidate is labeled honestly as one of:
  - `selected_proof_only`;
  - `rejected_diagnostic`;
  - `rejected_animation_candidate`;
  - `blocked_comfyui_or_model_unavailable`.
- [ ] No 120-frame spend occurs unless a short proof passes artifact gate and Agent visual review.
