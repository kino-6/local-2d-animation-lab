# Output Cleanup: Start-Reference Retake With LocalVL Review

Date: 2026-06-14

## Removed Local Runs

The following local `outputs/` runs were reviewed and can be deleted because the durable findings are recorded here and in the linked project notes.

| run | size | role | decision |
| --- | ---: | --- | --- |
| `outputs/20260614_001954/` | 43.9 MB | full-body Anima start-reference candidate generation | `blocked_start_reference_quality` |
| `outputs/20260614_002335/` | 9.5 KB | LocalVL review for the selected start reference | `is_walk_ready_start_reference: false` |

## Key Findings

- `novaOrangeXL_v120.safetensors` with OpenPoseXL at 1024 square can produce cleaner side-view still candidates than earlier runs, but it still does not reliably produce walk-ready lower-body structure.
- No candidate in `outputs/20260614_001954/` passed `candidate_ok`.
- The selected deterministic candidate was `strict_side_profile`, but it remained `manual_review_or_retake`.
- The selected candidate was blocked by `shoes_unreadable`.
- Deterministic lower-body metrics for the selected candidate:
  - `foot_component_count: 2`
  - `lower_leg_component_count: 1`
  - `foot_separation_ratio: 0.53111`
  - `foot_zone_coverage: 0.01584`
  - `lower_leg_visibility_ratio: 0.02355`
- LocalVL agreed with the block when deterministic state was included:
  - `deterministic_selection_not_candidate_ok`
  - `deterministic_shoes_unreadable`
  - `local_vl_low_shoe_readability_score`
  - `local_vl_low_side_view_score`
  - `local_vl_low_walk_contact_score`

## Interpretation

Text-only retakes are no longer the best next lever. The next loop should inject stronger foot and lower-body structure during the start-reference still-generation stage, then keep the same strict start-reference gate before spending time on Wan/VACE animation.

LocalVL remains useful as a secondary reviewer, especially when its numeric scores are combined with deterministic gate results. It should not be the sole adoption authority.

## Cleanup Decision

Delete the local output directories after this report is committed or staged:

```text
outputs/20260614_001954/
outputs/20260614_002335/
```

Retain only durable reports, scripts, tests, and task history in git.
