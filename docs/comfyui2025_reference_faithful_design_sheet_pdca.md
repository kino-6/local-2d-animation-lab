# ComfyUI2025 Reference-Faithful Design Sheet PDCA

Date: 2026-06-16

Reference:

```text
assets/reference/ComfyUI2025_74298_trim.png
```

## Goal

Stop trying to repair a drifted walk animation and first create a source design that still reads like the reference character.

The design-source gate is higher priority than motion:

1. same-character read
2. palette/saturation retention
3. right-facing full-body side view
4. transparent cutout usable as a future walk input

## Loop 1: Built-In Image Generation Design Sheet

Prompt route:

```text
built-in image generation using the visible reference image as identity/style reference
```

Output:

```text
outputs/20260616_design_sheet_pdca/20260616_0100_reference_faithful_design_sheet/design_sheet_v1.png
```

Human review:

- much closer to the source than the previous walk package;
- preserves pale sleepy face, long white/silver hair, black glossy hood, red collar, and gold forehead band;
- color is alive and high-contrast, not the dull over-dark result from the recolor walk candidate;
- still a redesign: boots, belts, gloves, and gold arm details are stronger and more tactical than the original image;
- acceptable as a design-source candidate for PDCA, not final production art.

## Loop 2: Side-View Extraction

Added:

```text
scripts/extract_design_sheet_side_view.py
```

Purpose:

- crop the right-facing full-body view from the design sheet;
- remove the light background into alpha;
- preserve bright white hair by using connected-background removal rather than naive white removal;
- generate a review sheet, manifest, and notes for later motion PDCA.

Best current side-view candidate:

```text
outputs/20260616_design_sheet_pdca/20260616_0100_reference_faithful_design_sheet/side_view_v1c_alpha/
```

Key files:

```text
side_view_v1c_alpha.png
side_view_v1c_alpha_review.png
manifest.json
notes.md
```

Checks:

- transparent corner alpha: yes
- side-view full body: yes
- no neighboring view leakage: yes
- frame size: `300x963`
- foreground mean saturation: `63.64`
- foreground mean value: `75.24`
- previous over-dark walk frame foreground mean value: `21.4`

LocalVL semantic check:

```text
outputs/20260616_design_sheet_pdca/20260616_012548/local_vl_eval/comfyui2025_74298_design_sheet_v1c_localvl/
```

Result:

- still image quality: `5/5`
- game sprite asset fit: `5/5`
- identity consistency: `5/5`
- background cleanliness: `5/5`
- action readability is low because this is a design sheet, not an action animation

## Current Status

```text
design_source_candidate_ready_for_motion_pdca
```

This is not ProductionOK art. It is the first candidate that is close enough to the source identity and saturation to justify using it as the input to the next walk-generation PDCA.

## Next PDCA

Use `side_view_v1c_alpha.png` as the identity-locked source.

Required next steps:

1. Generate or author a small walk pose set from this side-view design without changing outfit, hair, face, or palette.
2. Reject any output whose value/saturation collapses toward the old dark walk candidate.
3. Reject any output that changes the character into a generic knight, rogue, or different-haired character.
4. Package only after identity and palette pass.
5. Then run Godot playback validation.
