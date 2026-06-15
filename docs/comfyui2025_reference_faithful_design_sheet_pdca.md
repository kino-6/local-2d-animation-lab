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

## Loop 3: Nun + Gothic Hunter Correction

User review of Loop 1:

```text
The art quality is good, but it reads too much like a biker. The target image is Nun + Bloodborne-like.
```

Correction:

- reduce biker/leather-rider impression;
- increase nun habit / veil / robe silhouette;
- keep the pale sleepy face, white hair, black hood, red collar, and gold forehead ornament;
- keep the side view readable enough for future walk-cycle work.

Outputs:

```text
outputs/20260616_design_sheet_pdca/20260616_081036_nun_bloodborne_design_sheet/design_sheet_v2_nun_gothic.png
outputs/20260616_design_sheet_pdca/20260616_081036_nun_bloodborne_design_sheet/design_sheet_v3_nun_hunter_walkable.png
```

Selected current design-source candidate:

```text
outputs/20260616_design_sheet_pdca/20260616_081036_nun_bloodborne_design_sheet/side_view_v3_nun_hunter_walkable/side_view_v3_nun_hunter_walkable.png
```

Review sheet:

```text
outputs/20260616_design_sheet_pdca/20260616_081036_nun_bloodborne_design_sheet/side_view_v3_nun_hunter_walkable/side_view_v3_nun_hunter_walkable_review.png
```

Human review:

- substantially better target read: dark gothic nun + hunter instead of biker;
- keeps sleepy pale face, long white hair, black hood, red collar, restrained gold head ornament;
- long robe and lace trim are much closer to the intended mood;
- side view still exposes legs/feet through front/side openings, so it can be used for walk experiments;
- remaining risk: robe panels will be harder to animate than pants, so walk generation must preserve cloth panels and visible legs separately.

Comparison to Loop 1 side source:

| Candidate | Read | Strength | Weakness |
| --- | --- | --- | --- |
| `side_view_v1c_alpha.png` | glossy black rider / tactical nun | legs very readable, high contrast | too biker-like, boots/belts/bracers too modern |
| `side_view_v3_nun_hunter_walkable.png` | nun + gothic hunter | much closer costume mood and identity | robe panels are harder for walk-cycle generation |

Updated status:

```text
design_source_candidate_v3_nun_hunter_ready_for_motion_pdca
```

## Loop 4: Skirt + Boots Animation-Friendly Correction

User review of Loop 3:

```text
The robe gives mood, but it probably raises animation difficulty. Skirt + boots may be better.
```

Correction:

- keep the Nun + Bloodborne-like mood;
- replace the long robe with a gothic nun skirt and boots;
- preserve black hood, white hair, red collar, gold forehead band, and sleepy pale face;
- keep legs and boots visible for side-view walk contact/passing poses.

Output:

```text
outputs/20260616_design_sheet_pdca/20260616_0820_nun_skirt_boots_design_sheet/design_sheet_v4_nun_skirt_boots.png
```

Selected side-view candidate:

```text
outputs/20260616_design_sheet_pdca/20260616_0820_nun_skirt_boots_design_sheet/side_view_v4_nun_skirt_boots/side_view_v4_nun_skirt_boots.png
```

Review sheet:

```text
outputs/20260616_design_sheet_pdca/20260616_0820_nun_skirt_boots_design_sheet/side_view_v4_nun_skirt_boots/side_view_v4_nun_skirt_boots_review.png
```

Human review:

- currently the best design-source compromise;
- preserves the intended nun/gothic hunter identity better than the biker-like v1;
- easier to animate than the long-robe v3 because knees, lower legs, and boots are readable;
- still has enough cloth/lace/veil to avoid losing the target mood.

Comparison to Loop 3 robe source:

| Candidate | Read | Strength | Weakness |
| --- | --- | --- | --- |
| `side_view_v3_nun_hunter_walkable.png` | stronger long-robed nun | high mood fidelity | robe panels are high-risk for walk motion |
| `side_view_v4_nun_skirt_boots.png` | nun + skirt + boots | best animation practicality while keeping mood | slightly less austere / less robe drama |

Updated status:

```text
design_source_candidate_v4_nun_skirt_boots_ready_for_walk_pdca
```

## Next PDCA

Use `side_view_v4_nun_skirt_boots.png` as the identity-locked source.

Required next steps:

1. Generate or author a small walk pose set from this side-view design without changing outfit, hair, face, or palette.
2. Reject any output whose value/saturation collapses toward the old dark walk candidate.
3. Reject any output that changes the character into a generic knight, rogue, or different-haired character.
4. Preserve skirt hem, black stockings, and boots across frames; do not collapse the design into pants, robe-only silhouette, or biker gear.
5. Keep legs/feet readable in each contact/passing pose.
6. Package only after identity and palette pass.
7. Then run Godot playback validation.
