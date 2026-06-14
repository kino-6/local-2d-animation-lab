# Walk 8-Frame Baseline MVP

This repository is temporarily refocused from broad 120-frame animation research to one small
adoptable 2D game asset package.

## Goal

Create one boring but concrete game-loadable sprite package:

```text
outputs/adoptable/walk_8frame_sideview_baseline/
```

The package is intentionally conservative. It proves repository workflow, output shape, and review
readiness before chasing higher generative quality.

## Fixed Action Spec

Natural-language input may be accepted, but this route always normalizes it to:

```json
{
  "action": "walk",
  "direction": "right",
  "frame_count": 8,
  "view": "side",
  "loop": true,
  "background": "transparent"
}
```

## Hard Constraints

- Do not generate 120-frame outputs.
- Do not run Wan or other video generation.
- Do not attempt attack, hit, run, or weapon actions.
- Do not add new model integrations.
- Preserve one character silhouette and reviewable game output over realism.

## Output Contract

The adopted directory must contain:

- `frames/walk_000.png` through `frames/walk_007.png`
- `spritesheet.png`
- `preview.gif`
- `contact_sheet.png`
- `manifest.json`
- `notes.md`

`manifest.json` must mark the route as `baseline_not_production`.

## Implementation

`scripts/build_walk_8frame_baseline.py` performs a deterministic baseline:

1. Load one full-body reference image.
2. Create a transparent cutout from alpha or connected background removal.
3. Mirror the cutout to the fixed right-facing route by default.
4. Fit it to a stable game canvas.
5. Generate exactly eight frames using a small whole-body bob and lower-body offset.
6. Export frames, spritesheet, preview GIF, contact sheet, manifest, and notes.

This is not a claim of production animation quality. It is an adoptable MVP route that prevents the
project from drifting back into open-ended PDCA research before a concrete game asset exists.

## Review Bar

Acceptable means:

- exactly one character is visible;
- exactly eight frames exist;
- frame canvas size is consistent;
- PNG frame backgrounds are transparent;
- the preview GIF loops;
- the contact sheet is easy to inspect;
- no obvious duplicate body or crowd-like failure appears.

Production-grade walk art is out of scope for this route.
