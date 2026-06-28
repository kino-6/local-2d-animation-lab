# Artist-Authored 8-Frame Walk Cleanup

This is the Route A implementation target from `docs/next_asset_generation_routes.md`.

## Purpose

Package a human-authored 8-frame side-view walk rough into a reviewable 2D game asset package.

This route is deliberately different from `walk_8frame_sideview_baseline`:

- the human controls pose and silhouette;
- the script only cleans and packages frames;
- no geometric puppet renderer is used;
- no video or broad generative workflow is used.

## Input Contract

Provide exactly 8 PNG frames:

```text
rough_frames/
  walk_000.png
  walk_001.png
  walk_002.png
  walk_003.png
  walk_004.png
  walk_005.png
  walk_006.png
  walk_007.png
```

The frames should already contain the intended walk poses. A reference image may be supplied only
as metadata for review.

## Output Contract

Default output:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/
```

The package contains:

- `frames/walk_000.png` through `frames/walk_007.png`
- `spritesheet.png`
- `preview.gif`
- `contact_sheet.png`
- `game_previews/height_128/`
- `game_previews/height_192/`
- `game_previews/height_256/`
- `manifest.json`
- `cleanup_report.json`
- `production_review.json`
- `production_review.md`
- `production_polish/`
- `production_candidate/`
- `production_ready/` when finalized with `--mark-production-ready`
- `notes.md`

## Command

```powershell
uv run python scripts\package_artist_authored_walk_cleanup.py `
  --rough-frames-dir path\to\rough_frames `
  --output-dir outputs\adoptable\artist_authored_8frame_walk_cleanup `
  --reference-image assets\reference\Anima_00013_.png
```

## Scope

Allowed:

- transparent-background cleanup;
- green-dominant chroma cleanup and despill for generated rough sheets;
- plain-background removal when the rough has a removable solid background;
- alpha normalization;
- automatic ground-line alignment for a `production_polish/` candidate;
- stable shared-canvas trimming for a `production_candidate/` folder;
- spritesheet, contact sheet, preview GIF, game-size previews, manifest, cleanup report, polish report, and production review generation.
- explicit `production_ready/` finalization after the candidate passes the production gate and visual review.

Not allowed:

- generating new poses;
- changing frame count;
- changing walk phase order;
- ComfyUI, Wan, ControlNet, video generation, or new model integrations;
- 120-frame generation;
- claiming the output is production-ready without the explicit `--mark-production-ready` finalization flag.

## Review

The output should be reviewed in Aseprite or Godot. Failures should be recorded per frame in
`cleanup_report.json` or fixed directly in the rough frames.

## Generated Rough Candidate

A first AI-generated rough candidate is stored as a Route A input experiment:

```text
assets/artist_authored_roughs/imagegen_walk_8frame_20260614/
```

The current stronger candidate is:

```text
assets/artist_authored_roughs/imagegen_walk_8frame_20260614_v2/
```

Packaged review output:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/
```

This candidate is useful because it avoids the geometric puppet failure mode and produces a
reviewable anime-style 8-frame side-view walk sheet. It is still not production art, and it should
not be treated as proof that fully automated generation is solved. The manifest marks it as
`source_kind: ai_generated_rough_for_route_a_v2` for honesty.

v2 required a cleanup improvement: the generated green background looked uniform but contained
enough variation that distance-threshold chroma removal either left green panels or damaged the
character. The cleanup script now also recognizes green-dominant connected background regions.

The current packaged output also includes game-size previews at 128, 192, and 256 px height. These
are for reviewing whether the motion still reads at practical 2D game sizes before doing any manual
Aseprite cleanup.

## Production Gate

The current v2 package passes the mechanical production gate and has been explicitly finalized:

```text
decision: production_ready
blocking_issues: none
production_ready: true
```

This means the current MVP route has an accepted production-ready package. It does not mean the
workflow can produce arbitrary production art automatically; it means this specific 8-frame
side-view walk package passed the local gate and Agent visual review at 128px and 192px.

Finalization is intentionally explicit: run the packaging command with `--mark-production-ready`.

## Production Polish Candidate

The package now writes an automatic polish candidate:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/production_polish/
```

This candidate keeps the same 8 frames and only applies conservative post-processing:

- ground-line alignment;
- tiny alpha-component cleanup;
- regenerated spritesheet, preview GIF, contact sheet, and 128/192/256 px game previews.

Current polish metrics:

```text
ground_y_range_before: 9
ground_y_range_after: 0
max_abs_y_shift: 9
```

Use `production_polish/` as the base for human review and final Aseprite cleanup. It is still
`auto_polished_candidate_not_final`, not production art.

## Production Candidate

The current best game-loadable folder is:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/production_candidate/
```

It is generated from `production_polish/` with a stable shared crop:

```text
frame_size: 352x480
crop_rect: [45, 6, 397, 486]
ground_y_range: 0
alpha_edge_touch_frames: []
```

Compared with the 448x512 review canvas, this candidate removes excess empty space while keeping all
8 frames on the same canvas. Use this folder first for Godot/Aseprite review.

## Production Ready Output

The current accepted MVP asset package is:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/production_ready/
```

It is copied from `production_candidate/` after all production gate checks passed and Agent visual
review accepted the 128px and 192px contact sheets.

```text
frame_count: 8
frame_size: 352x480
ground_y_range: 0
alpha_edge_touch_frames: []
production_gate.decision: production_ready
review.production_ready: true
```

Use `production_ready/preview.gif`, `production_ready/spritesheet.png`, and the
`production_ready/game_previews/` folders as the current best game-loadable 2D walk asset.
