# ComfyUI2025 74298 Reference Feasibility

Date: 2026-06-15

Reference:

```text
assets/reference/ComfyUI2025_74298_trim.png
```

## Input Assessment

The image is visually strong, but it is not directly animation-ready:

- size: `2563x1489`
- background: fully opaque, scene/background included
- framing: bust-up / upper-body dominant
- view: not side-view
- feet/lower body: unavailable
- direct start-reference LocalVL result: not full-body, not right-facing side-view, shoes not readable, not walk-ready

LocalVL output:

```text
outputs/20260615_reference_eval/20260615_231509/local_vl_eval/comfyui2025_74298_reference_feasibility/
```

## Identity Cues

Use these cues for future reference-faithful work:

- pale white long hair
- black hood
- shiny gold cap band
- glossy black and gold armor
- red collar at the neck
- sleepy half-lidded eyes
- small pale face
- high contrast cel-shaded anime style
- dark fantasy knight/nun silhouette

## Full-Body Side-View Probe

Command route:

```text
scripts/generate_fullbody_reference_candidates.py
```

Output:

```text
outputs/20260615_reference_eval/20260615_231601/fullbody_reference/comfyui2025_74298_trim/
```

Result:

- all 12 candidates stayed at `manual_review_or_retake`
- automatic selected candidate was visually invalid because it contained two characters
- best visual candidate was `cleaned/04_face_visible_side_sprite.png`
- candidate 04 preserved the new reference style much better than previous Anima-derived work
- candidate 04 still has a left-edge fragment and is not a clean adopted start reference
- candidate 08 had strong side-view/style preservation but long skirt/cloak occluded legs, making it weak for walk animation

Interpretation:

```text
This reference is promising for reference-faithful redesign, but it needs a curated single-character full-body design sheet before animation.
```

## Walk Endpoint Probe

Source image:

```text
outputs/20260615_reference_eval/20260615_231601/fullbody_reference/comfyui2025_74298_trim/cleaned/04_face_visible_side_sprite.png
```

Command route:

```text
scripts/generate_action_keyframe_candidates.py --action walk_stride --source-image <candidate04>
```

Output:

```text
outputs/20260615_reference_eval/20260615_232140/action_keyframes/comfyui2025_74298_trim_walk_stride_keyframes/
```

Result:

- both endpoint candidates were `manual_review_or_retake`
- blocker: `endpoint_delta_too_low`
- visual result preserved style/identity better than earlier references
- walk pose change was too small to drive first/last or spritesheet generation

## Decision

Current status:

```text
reference_faithful_probe_promising_not_production
```

This image is better for testing reference-faithful style retention than the prior examples, but it is still not an adopted game animation source.

Next useful step:

1. Generate or manually curate a clean one-character full-body side-view design sheet.
2. Use that design sheet as the style reference, not the original bust-up artwork.
3. Retry walk spritesheet-first generation with stronger lower-body pose control.
4. Add a stricter single-character/model-sheet gate so two-character outputs cannot be auto-selected.
