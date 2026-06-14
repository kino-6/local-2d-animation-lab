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
3. Derive a simple identity palette from the reference.
4. Render a stylized right-facing 8-phase sprite walk cycle from a small explicit skeleton model.
5. Export frames, spritesheet, preview GIF, contact sheet, manifest, and notes.

This is not a claim of production animation quality. It is an adoptable MVP route that prevents the
project from drifting back into open-ended PDCA research before a concrete game asset exists.

## Quality Pass Finding

The first cutout-shift baseline was not evaluation-worthy: it produced a valid package, but the
preview looked like a cutout wobble rather than a walk cycle. A second cutout-preserving attempt
with synthetic legs improved motion readability but the legs did not match the source art style.

The current default route therefore uses a stylized reference-derived renderer. It keeps visible
identity cues from the reference, such as pink hair, side-view profile, sailor uniform, red tie,
skirt trim, dark socks, and brown shoes. This is less faithful to the source image, but it is more
game-friendly and reviewable as an 8-frame walk MVP.

The latest quality pass keeps that scope and adds explicit skeleton metadata for:

- stable ground line;
- contact foot by frame;
- small hip bob;
- mostly stable head position;
- bent knees;
- right-facing heel/toe foot shapes;
- opposite arm swing.

`manifest.json` records these checks under `walk_readability`.

The current shape polish pass keeps the same skeleton and adds filled tapered limb segments for
arms and legs, a small waist/hip block under the sailor top, and compact right-facing shoes. This
reduces the stick-puppet impression without changing the route scope or claiming production art
quality.

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
