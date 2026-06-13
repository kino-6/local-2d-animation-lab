# Lower-Body Sidecar Start-Reference PDCA

Date: 2026-06-14

## Objective

Improve the walk start-reference stage for local 2D game asset generation by adding lower-body/foot structure during still-image generation. This is not a rig or puppet route; the input image remains a character design reference.

## Implementation

Updated:

```text
scripts/generate_fullbody_reference_candidates.py
tests/test_fullbody_reference_candidates_script.py
```

New generation controls:

- `--sidecar-style foot_contact_lineart`
- `--sidecar-controlnet SDXL\t2i-adapter_diffusers_xl_lineart.safetensors`
- `--sidecar-strength`
- `--sidecar-start-percent`
- `--sidecar-end-percent`

The workflow chains the sidecar ControlNet after the main OpenPose ControlNet only when sidecar strength is greater than zero. The sidecar is generated and stored under the timestamped run directory.

## Start-Reference Run

Run:

```text
outputs/20260614_005144/fullbody_reference/anima_00013/
```

Settings:

- checkpoint: `novaOrangeXL_v120.safetensors`
- main ControlNet: `SDXL\OpenPoseXL2.safetensors`
- sidecar ControlNet: `SDXL\t2i-adapter_diffusers_xl_lineart.safetensors`
- sidecar style: `foot_contact_lineart`
- sidecar strength: `0.16`
- sidecar end percent: `0.45`

Result:

- 12 candidates generated.
- 1 candidate reached deterministic `candidate_ok`.
- Selected candidate: `small_stride_side_walk_sprite`.
- Selected lower-body metrics:
  - `foot_component_count: 2`
  - `lower_leg_component_count: 2`
  - `foot_separation_ratio: 0.50163`
  - `foot_zone_coverage: 0.01894`
  - `lower_leg_visibility_ratio: 0.02517`

Agent visual review:

- The selected still is much closer to a usable side-view 2D game walk start frame than prior attempts.
- It is right-facing, full-body, and shoes/contact are readable.
- The stride is still conservative, so it is a short-probe input, not an adopted asset.

## LocalVL Start-Reference Review

Run:

```text
outputs/20260614_010050/local_vl_eval/anima_sidecar_start_reference_vl/start_reference_vl_eval.json
```

Result:

- `is_walk_ready_start_reference: true`
- deterministic start status: `candidate_ok`
- no blocking reasons

Interpretation:

- LocalVL agreed with the deterministic start-reference gate for the still candidate.
- This supports the sidecar direction for start-reference generation.

## Double-Clean Bug Boundary

Attempting to feed the cleaned selected reference directly into Wan failed before generation:

```text
outputs/20260614_010156/wan_walk_i2v/anima_sidecar_start_probe_i2v_len17/start_frame_report.json
```

Failure:

```text
shoes_unreadable
```

Cause:

- Candidate selection measured the original generated image while writing a cleaned preview.
- Re-running the start-frame cleaner on the cleaned preview cropped/rescaled it again and reduced foot-zone coverage.

Fix:

- `scripts/generate_fullbody_reference_candidates.py` now also records `selected_reference/animation_probe_start_source.png`.
- Wan probes should use the generated source image or the recorded animation probe source so start-frame normalization happens exactly once.
- The report now records `cleaned_reference_recheck` so this failure mode is visible.

## Short Animation Probe

Successful short probe using the generated source image:

```text
outputs/20260614_010251/wan_walk_i2v/anima_sidecar_source_start_probe_i2v_len17/
```

Result:

- `frame_count: 17`
- motion metrics:
  - `mean_frame_delta: 9.416`
  - `max_frame_delta: 15.808`
  - `min_frame_delta: 1.97`

Agent visual review:

- The action reads as a walk.
- It is not adoptable as a 2D game asset.
- Blocking visual issues:
  - strong lower-body afterimages;
  - leg recoloring and darkening;
  - foot/contact smears;
  - partial duplicate-silhouette frames.

## Standard Quality Flow

Run:

```text
outputs/20260614_010359/sprite_asset_quality_flow/anima_sidecar_probe_quality/
```

Decision:

```text
rejected_animation_candidate
```

Key results:

- motion readability: `passed`
- artifact gate: `rejected`
- artifact summary:
  - `retake_required: 2/17`
  - `no_repair_needed: 15/17`
  - `lower_body_pale_afterimage_review: 6`
  - `masked_ghost_or_small_artifact: 2`
  - `strong_duplicate_silhouette_risk: 1`
  - `duplicate_silhouette_area_high: 1`
- LocalVL over-scored the animation as adoptable despite visible issues, so it remains secondary.

## Conclusion

The sidecar start-reference direction is useful:

```text
OpenPose + low-strength lower-body lineart sidecar
```

produced the first deterministic `candidate_ok` Anima start reference in this loop.

But the animation is still not adoption-ready. The next blocker is no longer "cannot get a plausible start reference"; it is "single-keyframe Wan i2v turns that start reference into a walking clip with lower-body afterimages, recoloring, and foot smears."

Next work should focus on preserving the improved start reference through video generation:

- avoid double-cleaning selected references;
- prefer source-image normalization exactly once;
- compare Wan settings around lower shift/CFG with this better start frame;
- test BiRefNet foreground separation and conservative histogram correction after this new sidecar start;
- keep deterministic artifact gate authoritative over LocalVL.

## 2026-06-14 Preservation Follow-Up

Follow-up report:

```text
docs/wan_preservation_sweep_from_sidecar_start_20260614.md
```

Summary:

- baseline Wan from the retained sidecar start has the best walk readability, but still fails due red/black leg recoloring and lower-body ghosts.
- low `shift/cfg` variants improve luma and color stability but create more duplicate-silhouette failures and weaker walk motion.
- BiRefNet on the low-setting branch slightly improves foreground/background separation but cannot repair duplicate legs or body-internal afterimages.

Decision remains:

```text
rejected_diagnostic
```

Do not promote to 120 frames yet.
