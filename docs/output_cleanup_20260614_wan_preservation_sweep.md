# Output Cleanup: Wan Preservation Sweep From Sidecar Start

Date: 2026-06-14

## Runs Removed After Knowledge Capture

The following local output runs were reviewed and can be deleted after this report because their findings are recorded in:

```text
docs/wan_preservation_sweep_from_sidecar_start_20260614.md
docs/lower_body_sidecar_start_reference_pdca_20260614.md
docs/walk_candidate_comparison.md
docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md
```

| run | role | decision |
| --- | --- | --- |
| `outputs/20260614_011647/` | baseline Wan `shift=8.0 cfg=5.0` from retained sidecar start | `rejected_diagnostic` |
| `outputs/20260614_011740/` | low Wan `shift=4.0 cfg=2.8` | `rejected_diagnostic` |
| `outputs/20260614_011829/` | middle Wan `shift=5.0 cfg=3.6` | `rejected_diagnostic` |
| `outputs/20260614_011917/` | quality flow for baseline | `rejected_animation_candidate` |
| `outputs/20260614_012141/` | quality flow for `shift4/cfg2.8` | `rejected_animation_candidate` |
| `outputs/20260614_012501/` | quality flow for `shift5/cfg3.6` | `rejected_animation_candidate` |
| `outputs/20260614_013017/` | BiRefNet foreground separation for `shift4/cfg2.8` | diagnostic only |
| `outputs/20260614_013050/` | quality flow after BiRefNet | `rejected_animation_candidate` |

Total local output size before cleanup was about 285 MB.

## Findings Preserved

- Baseline Wan has the clearest walking motion but produces red/black leg recoloring and lower-body ghosts.
- Lower `shift/cfg` settings improve foreground luma and saturation stability, but increase duplicate-silhouette failures and weaken the walk.
- BiRefNet slightly improves foreground separation but does not repair body-internal duplicate legs or afterimages.
- LocalVL is not sufficient for adoption when deterministic artifact gates reject.
- Do not promote any of these runs to 120 frames.

## Retained Input

The retained start source remains:

```text
assets/reference/generated/anima_00013_sidecar_walk_start_source_20260614.png
```

Future probes should continue to use that source so start-frame normalization happens exactly once.
