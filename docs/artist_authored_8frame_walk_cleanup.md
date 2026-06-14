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
- `manifest.json`
- `cleanup_report.json`
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
- plain-background removal when the rough has a removable solid background;
- alpha normalization;
- spritesheet, contact sheet, preview GIF, manifest, and cleanup report generation.

Not allowed:

- generating new poses;
- changing frame count;
- changing walk phase order;
- ComfyUI, Wan, ControlNet, video generation, or new model integrations;
- 120-frame generation;
- claiming the output is production-ready.

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
