# Output Cleanup: 2026-06-14 Start Reference Gate

Date: 2026-06-14

## Scope

This cleanup records the local `outputs/` session from the walk-ready full-body start-reference gate before deleting it. The durable knowledge is kept in tracked docs.

Archived task checkpoint:

```text
docs/archive/Tasks_20260614_walk_ready_start_reference_gate_completed.md
```

## Local Output Session Before Cleanup

| Session | Purpose | Size | Files | Decision |
| --- | --- | ---: | ---: | --- |
| `outputs/20260614_000549/` | full-body start-reference candidates from `assets/reference/Anima_00013_.png` | `36.70 MB` | `57` | `blocked_start_reference_quality` |

## Durable Findings Kept In Git

Detailed documents:

- `docs/start_frame_first_walk_pdca.md`
- `docs/reference_lock_motion_template_deep_dive.md`
- `docs/walk_candidate_comparison.md`
- `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
- `Tasks.md`

Key retained facts:

- 10 full-body candidates were generated.
- No candidate reached `candidate_ok`.
- Auto-selected candidate:
  - `slight_three_quarter_side`
  - `manual_review_or_retake`
  - issues: `extra_foreground_components_removed`, `large_secondary_component`, `shoes_unreadable`
- Agent visual review:
  - selected image is acceptable as a still illustration, but not as a walk-ready start reference;
  - it is too front-facing/near-front;
  - lower legs and shoes are not reliable enough for 2D walk animation;
  - side-facing alternatives in the sheet still had model-sheet residue, secondary components, foot ambiguity, or non-walk composition.
- Implementation update:
  - `generate_fullbody_reference_candidates.py` records `animation_probe_allowed`;
  - non-`candidate_ok` selections are marked `blocked_start_reference_quality`;
  - `foreground_too_wide_for_side_reference` is now blocking.

Conclusion:

```text
Do not run animation generation from the selected Anima start frame.
The bottleneck is still start-reference generation and selection.
```

## Cleanup Action

After this report is committed, the following local folder may be deleted:

- `outputs/20260614_000549/`

Future generation must create fresh, auditable runs under:

```text
outputs/<YYYYMMDD_HHMMSS>/<category>/<run-label>/
```
