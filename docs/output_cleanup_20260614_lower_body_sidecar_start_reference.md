# Output Cleanup: Lower-Body Sidecar Start-Reference Probe

Date: 2026-06-14

## Retained Minimal Asset

The best start-reference source was copied out of `outputs/` before cleanup:

```text
assets/reference/generated/anima_00013_sidecar_walk_start_source_20260614.png
```

This is the generated source image, not the cleaned preview. It should be passed to Wan so start-frame normalization happens exactly once.

## Removed Local Runs

The following `outputs/<timestamp>/` runs were reviewed and can be deleted because findings are recorded in:

```text
docs/lower_body_sidecar_start_reference_pdca_20260614.md
docs/start_frame_first_walk_pdca.md
docs/reference_lock_motion_template_deep_dive.md
docs/local_vl_asset_evaluation_pdca.md
docs/walk_candidate_comparison.md
```

| run | role | decision |
| --- | --- | --- |
| `outputs/20260614_005144/` | sidecar-guided Anima start-reference generation | one `candidate_ok` start reference |
| `outputs/20260614_010050/` | LocalVL start-reference review | `is_walk_ready_start_reference: true` |
| `outputs/20260614_010156/` | failed Wan preflight from double-cleaned selected preview | `shoes_unreadable` |
| `outputs/20260614_010251/` | 17-frame Wan i2v probe from source image | walk motion readable, not adoptable |
| `outputs/20260614_010359/` | standardized quality flow | `rejected_animation_candidate` |

Total local output size before cleanup was about 123 MB.

## Key Findings

- Lower-body/foot lineart sidecar at the still start-reference stage is useful.
- The best selected source is full-body, right-facing, and has readable shoes.
- The cleaned selected preview should not be fed back into Wan normalization; double-cleaning can reduce foot-zone coverage enough to fail `shoes_unreadable`.
- Plain Wan i2v from the improved source produces readable walking motion but still creates lower-body afterimages, leg recoloring/darkening, foot/contact smears, and duplicate-silhouette risk.
- LocalVL over-promoted the short animation as adoptable. Deterministic artifact gate and Agent visual review remain authoritative.

## Next Direction

Use the retained start source to test preservation through video generation:

```text
retained sidecar start source
-> short Wan setting sweep
-> quality flow
-> BiRefNet foreground separation for the best short probe
-> conservative histogram correction only if artifact gate improves
```

Do not promote to 120 frames until a short proof passes artifact gate and visual review.
