# Implement

## Changes

- Added adjacent-frame ImageDiff metrics to `scripts/visual_asset_gate.py`.
- Added an isolated-frame detector that flags frames where both incoming and outgoing deltas are
  high but the surrounding frames are similar.
- Added `idle` reference metrics:
  - `idle_pose_delta_values`
  - `idle_pose_delta_first`
  - `idle_pose_delta_last`
  - `idle_bbox_pose_delta_values`
  - `idle_bbox_pose_delta_first`
  - `idle_bbox_pose_delta_last`
- Added `poor_recovery_to_idle_pose` for recovery actions whose last frame stays too far from
  `idle`.
- Added GIF E2E tests for the active pack previews.
- Extended the visual trauma corpus with:
  - `abrupt_frame_delta_outlier`
  - `poor_idle_recovery`

## Notes

Weapon actions compare against `idle` using image deltas but avoid blocking on bbox distance alone,
because the sword intentionally expands the bbox.

