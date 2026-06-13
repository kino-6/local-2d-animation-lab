# Wan Preservation Sweep From Sidecar Start

Date: 2026-06-14

## Objective

Use the retained sidecar-improved Anima start source and test whether Wan settings plus post-Wan foreground separation can preserve a readable 2D game walk without lower-body afterimages, recoloring, or duplicate silhouettes.

Retained start source:

```text
assets/reference/generated/anima_00013_sidecar_walk_start_source_20260614.png
```

## Runs

| route | output | Wan metrics | quality decision | main finding |
| --- | --- | --- | --- | --- |
| baseline `shift=8.0 cfg=5.0` | `outputs/20260614_011647/wan_walk_i2v/anima_sidecar_preserve_baseline_shift8_cfg5_len17/` | mean delta `9.416` | `rejected_animation_candidate` | best walk readability, but strong red/black leg recolor and ghosting |
| low setting `shift=4.0 cfg=2.8` | `outputs/20260614_011740/wan_walk_i2v/anima_sidecar_preserve_shift4_cfg28_len17/` | mean delta `5.05` | `rejected_animation_candidate` | much better luma/color stability, but weaker motion and more duplicate silhouette |
| middle setting `shift=5.0 cfg=3.6` | `outputs/20260614_011829/wan_walk_i2v/anima_sidecar_preserve_shift5_cfg36_len17/` | mean delta `5.361` | `rejected_animation_candidate` | similar to low setting; not a better compromise |
| low setting + BiRefNet | `outputs/20260614_013017/birefnet_foreground/anima_sidecar_shift4_cfg28_birefnet_white/` | BiRefNet mean mask delta `0.01156` | `rejected_animation_candidate` after quality flow | slight improvement, but duplicate silhouettes remain foreground-internal |

Quality-flow evidence:

| route | quality flow | motion readability | gate summary | luma stdev after stabilization | key blockers |
| --- | --- | ---: | --- | ---: | --- |
| baseline | `outputs/20260614_011917/sprite_asset_quality_flow/anima_sidecar_preserve_baseline_quality/` | `36.813` | `no_repair_needed: 15`, `retake_required: 2` | `11.53408` | leg recolor, lower-body afterimage, duplicate-silhouette risk |
| `shift4/cfg2.8` | `outputs/20260614_012141/sprite_asset_quality_flow/anima_sidecar_preserve_shift4_cfg28_quality/` | `27.309` | `retake_required: 11`, `no_repair_needed: 6` | `2.26593` | duplicate silhouette high on 11 frames |
| `shift5/cfg3.6` | `outputs/20260614_012501/sprite_asset_quality_flow/anima_sidecar_preserve_shift5_cfg36_quality/` | `31.622` | `retake_required: 10`, `no_repair_needed: 6`, `repair_candidate: 1` | `2.05443` | duplicate silhouette high on 10 frames, one double-foot risk |
| `shift4/cfg2.8 + BiRefNet` | `outputs/20260614_013050/sprite_asset_quality_flow/anima_sidecar_shift4_cfg28_birefnet_quality/` | `24.596` | `retake_required: 10`, `no_repair_needed: 7` | `2.68287` | duplicate silhouette high on 10 frames |

## Agent Visual Review

- Baseline has the clearest walking motion, but the legs become red/black and lower-body ghosting is obvious.
- `shift4/cfg2.8` and `shift5/cfg3.6` produce brighter, more stable colors, but the walk weakens and body/leg silhouettes overlap in ways the gate correctly rejects.
- BiRefNet slightly improves the low-setting branch by cleaning the foreground/background separation, but it does not remove duplicate legs or body-internal afterimages.

## Decision

```text
rejected_diagnostic
```

No candidate is adoption-ready. Do not spend on 120 frames from these settings.

## Durable Findings

- The improved sidecar start reference is useful and should remain the starting point.
- Wan parameter lowering can trade dark/recolored legs for weaker motion and more duplicate silhouettes.
- BiRefNet helps when drift is background/foreground separation, but not when the bad shape is inside the character foreground.
- The next route should not be another scalar-only Wan setting sweep.

## Next Direction

The next useful branch should add stronger temporal/structural preservation, for example:

- feed a conservative first/last endpoint only after the endpoint itself passes sprite and action gates;
- test a video workflow with explicit identity/reference preservation rather than plain Wan i2v only;
- use a short selected span strategy before 120-frame spend;
- keep lower-body/foot duplicate risk as a hard blocker.
