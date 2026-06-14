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

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet.
- [x] Save all new generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Keep `outputs/` free of loose files and stale diagnostic runs after durable findings are recorded.
- [x] Target adopted animation source length is 120 frames; short probes are evidence only.
- [x] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [x] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, shoe unreadability, front-view drift, model-sheet residue, composition collapse, or identity drift are visible.
- [x] LocalVL must not override deterministic artifact gates or Agent visual rejection.

## Current Interpretation

- [x] The start-reference stage has improved: lower-body lineart sidecar produced one deterministic `candidate_ok`.
- [x] The new blocker is preservation through video generation.
- [x] Plain Wan i2v from the improved source reads as walking but creates lower-body afterimages, recoloring/darkening, foot smears, and duplicate-silhouette risk.
- [x] Double-cleaned selected previews are unsafe; Wan should receive the retained generated source so normalization happens exactly once.
- [x] The next loop should compare a small number of Wan settings and post-Wan foreground separation, not regenerate start references again.

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

- [x] Archive the previous completed `Tasks.md`.
- [x] Write cleanup findings for the current local output runs.
- [x] Retain only the minimal best start source outside `outputs/`.
- [x] Delete reviewed `outputs/` runs after path safety checks.
- [x] Run focused tests for touched code before generation.
- [x] Check ComfyUI queue before each generation request.
- [x] Run short Wan setting sweep from the retained start source.
  - Baseline from prior successful route.
  - Lower `shift`/`cfg` preservation variant.
  - Lower motion/ghosting variant if queue capacity allows.
- [x] Run standardized quality flow for each successful short probe.
- [x] Compare:
  - motion readability;
  - artifact gate status;
  - luma/saturation drift before and after stabilization;
  - lower-body afterimage labels;
  - foot/contact labels;
  - duplicate-silhouette risk.
- [x] Agent visual review of the best contact sheet.
- [x] If a best candidate exists, run BiRefNet foreground separation or foreground compositing on it.
- [x] Re-run quality flow after BiRefNet or foreground stabilization.
- [x] Update durable knowledge.
  - `docs/lower_body_sidecar_start_reference_pdca_20260614.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
  - `Tasks.md`

## Success Criteria

- [x] Old output clutter is removed after knowledge capture.
- [x] Tests pass for touched code.
- [x] At least one short Wan probe is generated from the retained source, or queue/model blocker is recorded.
- [x] Each generated probe has a standardized quality-flow decision.
- [x] Best candidate is labeled honestly as one of:
  - `selected_proof_only`;
  - `rejected_diagnostic`;
  - `rejected_animation_candidate`;
  - `blocked_comfyui_or_model_unavailable`.
- [x] No 120-frame spend occurs unless a short proof passes artifact gate and Agent visual review.

## Result

- [x] Planning and cleanup commit:
  - `a59cd3a Plan Wan preservation sweep from sidecar start`
- [x] Retained minimal source:
  - `assets/reference/generated/anima_00013_sidecar_walk_start_source_20260614.png`
- [x] Tests:
  - `uv run pytest tests\test_fullbody_reference_candidates_script.py tests\test_output_layout_policy.py tests\test_start_frame_quality.py`
  - `19 passed`
- [x] Wan setting sweep:
  - baseline `shift=8.0 cfg=5.0`: `outputs/20260614_011647/wan_walk_i2v/anima_sidecar_preserve_baseline_shift8_cfg5_len17/`
  - low setting `shift=4.0 cfg=2.8`: `outputs/20260614_011740/wan_walk_i2v/anima_sidecar_preserve_shift4_cfg28_len17/`
  - middle setting `shift=5.0 cfg=3.6`: `outputs/20260614_011829/wan_walk_i2v/anima_sidecar_preserve_shift5_cfg36_len17/`
- [x] Quality flows:
  - baseline: `outputs/20260614_011917/sprite_asset_quality_flow/anima_sidecar_preserve_baseline_quality/`
  - `shift4/cfg2.8`: `outputs/20260614_012141/sprite_asset_quality_flow/anima_sidecar_preserve_shift4_cfg28_quality/`
  - `shift5/cfg3.6`: `outputs/20260614_012501/sprite_asset_quality_flow/anima_sidecar_preserve_shift5_cfg36_quality/`
- [x] BiRefNet foreground separation:
  - `outputs/20260614_013017/birefnet_foreground/anima_sidecar_shift4_cfg28_birefnet_white/`
  - follow-up quality flow: `outputs/20260614_013050/sprite_asset_quality_flow/anima_sidecar_shift4_cfg28_birefnet_quality/`
- [x] Durable report:
  - `docs/wan_preservation_sweep_from_sidecar_start_20260614.md`
- [x] Decision:
  - `rejected_diagnostic`

## Findings

- [x] Baseline `shift=8/cfg=5` still has the clearest walk readability, but fails due to lower-body recolor and ghosting.
- [x] Lower `shift/cfg` improves luma and color stability strongly, but increases duplicate-silhouette failures and weakens walk motion.
- [x] BiRefNet slightly improves foreground separation but does not fix duplicate legs or lower-body ghosts inside the character foreground.
- [x] Do not promote to 120 frames from this branch.
- [x] Next route should not be another scalar-only Wan setting sweep.
