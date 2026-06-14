# Output Cleanup: Character Sprite Pack

Date: 2026-06-14

## Keep

The current adopted asset is:

```text
outputs/adoptable/character_sprite_asset_pack/
```

This folder is retained because it is the current best game-loadable package:

- `walk`, `idle`, `run`, `jump`, and `hurt` actions;
- Godot `AnimatedSprite2D` pack playback support;
- `runtime_manifest.json`;
- `pack_review/all_actions_contact_sheet.png`;
- `pack_review/consistency_report.json`;
- `pack_review/godot_import_manifest.json`;
- source/action frames, spritesheets, GIFs, and review metadata.

The walk production-ready source is also retained:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/production_ready/
```

`scripts/build_character_sprite_asset_pack.py` consumes that folder as the accepted walk source.

## Delete

The following are safe to remove from `outputs/` after this report:

```text
outputs/adoptable/walk_8frame_sideview_baseline/
outputs/adoptable/artist_authored_8frame_walk_cleanup/frames/
outputs/adoptable/artist_authored_8frame_walk_cleanup/game_previews/
outputs/adoptable/artist_authored_8frame_walk_cleanup/production_candidate/
outputs/adoptable/artist_authored_8frame_walk_cleanup/production_polish/
```

Reasons:

- `walk_8frame_sideview_baseline` is a technical baseline only, superseded by the adopted pack.
- `frames/` and `game_previews/` under `artist_authored_8frame_walk_cleanup` are intermediate review outputs.
- `production_candidate/` and `production_polish/` are superseded by `production_ready/`.
- The accepted result and the knowledge needed to reproduce it remain in docs, scripts, tests, rough assets, and the retained production-ready folder.

## Current Findings

- Godot viewer must separate runtime origin from review centering. Use `bottom_center_canvas` for game import, but center the selected action's `visible_bbox` in the review viewport.
- `jump` and `hurt` looked off-scale because rough cleanup resized the whole rough cell, not the foreground character. The fix is alpha-bbox foreground normalization against the accepted walk scale.
- Runtime playback timing expansion is useful for review, but it is not true inbetween art:
  - `jump`: 6 source frames, 8 playback frames;
  - `hurt`: 4 source frames, 6 playback frames.
- For production-quality motion, the next source-level step is to generate or author denser rough sheets:
  - `jump`: 8-10 source frames;
  - `hurt`: 6-8 source frames;
  - future action attacks: 8-12 source frames.
- Dense-frame implementation target:
  - `jump`: 8 source frames with anticipation, takeoff, rise, tuck, fall, landing, and recovery;
  - `hurt`: 6 source frames with brace, recoil, stagger, settle, and recovery.
- 2026-06-15 follow-up: use multiple 2x2 source sheets for higher-density actions to avoid
  crowded-grid resolution loss:
  - `jump`: 12 source frames;
  - `hurt`: 8 source frames.

## Next Direction

Do not rely on cross-fade or optical-flow interpolation for sprite frames because it tends to create ghosting and double limbs.

Prefer:

1. I2I or artist-authored rough sheets with more source frames.
2. Foreground bbox scale normalization.
3. Godot pack playback validation.
4. Agent visual review against pack-level contact sheets.
