# Conservative Walk Endpoint Gate

Date: 2026-06-14

## Objective

Test a non-scalar route after the Wan preservation sweep: create a conservative first/last endpoint for the retained sidecar start source, then run first/last Wan only if the endpoint is clean, side-view, full-body, and action-bearing.

Retained start source:

```text
assets/reference/generated/anima_00013_sidecar_walk_start_source_20260614.png
```

## Implementation

Added `walk_stride` to:

```text
scripts/generate_action_keyframe_candidates.py
tests/test_action_keyframe_candidates_script.py
```

The new action has two conservative endpoint candidates:

- `walk_opposite_contact_small_stride`
- `walk_passing_pose_conservative`

The prompts explicitly avoid running, high kicks, dramatic illustration poses, and front-facing drift.

## Tests

```text
uv run pytest tests\test_action_keyframe_candidates_script.py tests\test_fullbody_reference_candidates_script.py tests\test_output_layout_policy.py tests\test_start_frame_quality.py
```

Result:

```text
25 passed
```

## Endpoint Probe A: Full Img2Img

Run:

```text
outputs/20260614_100851/action_keyframes/anima_00013_walk_stride_keyframes/
```

Settings:

- `source_edit_region: full`
- `denoise: 0.52`
- `controlnet_strength: 0.80`
- `min_endpoint_delta: 8.0`

Result:

- selected: `walk_passing_pose_conservative`
- selected status: `manual_review_or_retake`
- issue: `extra_foreground_components_removed`
- candidate deltas:
  - `walk_opposite_contact_small_stride: 11.93901`
  - `walk_passing_pose_conservative: 11.91566`

Agent visual review:

- The endpoint remains too similar to the start pose.
- The numerical delta mostly reflects redraw/stylistic differences, not a useful opposite-contact walk keyframe.
- Do not run first/last Wan from this endpoint.

## Endpoint Probe B: Lower-Body Img2Img

Run:

```text
outputs/20260614_101109/action_keyframes/anima_00013_walk_stride_keyframes/
```

Settings:

- `source_edit_region: lower_body`
- `denoise: 0.64`
- `controlnet_strength: 0.82`
- `min_endpoint_delta: 8.0`

Result:

- selected: `walk_opposite_contact_small_stride`
- selected status: `candidate_ok`
- candidate deltas:
  - `walk_opposite_contact_small_stride: 12.34334`
  - `walk_passing_pose_conservative: 12.22645`

Agent visual review:

- The deterministic gate missed a severe visual failure.
- The rear lower leg/foot becomes an oversized boot-like structure.
- The image is not a clean walk endpoint and should not be passed to first/last Wan.

## Decision

```text
blocked_endpoint_quality
```

No first/last Wan probe was run. This is intentional: the endpoint gate prevented spending on a bad endpoint.

## Findings

- Adding `walk_stride` endpoint tooling is useful, but endpoint generation is not yet reliable enough.
- `source_delta` is necessary but insufficient. It can measure redraw amount rather than action-bearing pose change.
- Lower-body localized endpoint editing can pass deterministic still gates while visually breaking foot/leg anatomy.
- First/last Wan should remain gated by Agent visual review plus a stronger endpoint-specific lower-body/foot-shape gate.

## Next Direction

Before revisiting first/last Wan:

- add endpoint-specific visual/metric checks for lower-leg and shoe shape drift;
- compare endpoint against the start image with region-aware pose/foot delta, not only whole-image mean delta;
- reject endpoints where the rear foot becomes a boot-like blob or lower leg merges with the shoe.
