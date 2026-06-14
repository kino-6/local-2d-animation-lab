# Tasks: Character Identity Sprite Asset Pack MVP

Archived checkpoint:

```text
docs/archive/Tasks_20260614_walk_production_ready_completed.md
```

## Upper Rule

- [x] Keep the current `walk` production-ready output as a valid result, but do not pretend it solves every action.
- [x] Address the two remaining risks explicitly:
  - source-reference drift, where the game sprite becomes almost a different character;
  - action coverage, where only `walk` exists.
- [x] Stay scoped to a small adoptable 2D game asset pack.
- [x] Do not return to 120-frame generation, Wan/video generation, ComfyUI exploration, ControlNet research, or broad model integration work.

## Deliverable

- [x] Create one adopted package:

```text
outputs/adoptable/character_sprite_asset_pack/
```

- [x] Include a character identity contract derived from the reference:
  - pink bob hair;
  - side-profile anime girl;
  - sailor-style white top;
  - red tie;
  - navy skirt;
  - dark socks;
  - brown shoes.
- [x] Include action folders:
  - `actions/walk/` copied from the current production-ready walk package;
  - `actions/idle/` as the first additional production-ready action;
  - `actions/run/` as a dedicated production-ready run action from an accepted rough.
  - `actions/jump/` as a dedicated production-ready jump action from an accepted rough.
  - `actions/hurt/` as a dedicated production-ready small-damage reaction from an accepted rough.
- [x] Include:
  - `manifest.json`;
  - `identity_report.json`;
  - `production_gate.json`;
  - `notes.md`;
  - action-level `preview.gif`, `spritesheet.png`, `contact_sheet.png`, and frames where applicable.

## Implementation

- [x] Add `scripts/build_character_sprite_asset_pack.py`.
- [x] The script must consume:
  - `assets/reference/Anima_00013_.png`;
  - `outputs/adoptable/artist_authored_8frame_walk_cleanup/production_ready/`.
- [x] The script must consume the accepted run rough when available:
  - `assets/artist_authored_roughs/imagegen_run_8frame_20260614/rough_frames/`.
- [x] The script must consume accepted jump and hurt roughs when available:
  - `assets/artist_authored_roughs/imagegen_jump_6frame_20260614/rough_frames/`;
  - `assets/artist_authored_roughs/imagegen_hurt_4frame_20260614/rough_frames/`.
- [x] The script must not call model or video backends.
- [x] Build `walk` by copying the accepted production-ready walk output.
- [x] Build `idle` deterministically from the accepted walk character art:
  - exactly 4 frames;
  - transparent background;
  - consistent canvas;
  - one character only;
  - stable ground;
  - subtle idle motion only.
- [x] Add reference identity checks for required color/costume cues.
- [x] Add pack-level production gate:
  - `walk.production_ready == true`;
  - `idle.production_ready == true`;
  - `run.production_ready == true`;
  - `jump.production_ready == true`;
  - `hurt.production_ready == true`;
  - identity cue checks pass for the adopted actions;
  - no unsupported backend usage;
  - route can still honestly report that broad action coverage is incomplete.

## Documentation

- [x] Add `docs/character_identity_sprite_asset_pack.md`.
- [x] Document that `production_ready` for this pack means:
  - current walk is accepted;
  - current idle is accepted;
  - current run is accepted;
  - current jump is accepted;
  - current hurt is accepted;
  - character identity cues are tracked;
  - future stronger actions are gated instead of silently claimed.
- [x] Document that this does not solve faithful animation of arbitrary reference illustrations.

## Tests

- [x] Add `tests/test_build_character_sprite_asset_pack.py`.
- [x] Verify the output directory layout.
- [x] Verify `walk` has 8 frames and is production-ready.
- [x] Verify `idle` has 4 frames and is production-ready.
- [x] Verify `run` has 8 frames and is production-ready.
- [x] Verify `jump` has 6 frames and is production-ready.
- [x] Verify `hurt` has 4 frames and is production-ready.
- [x] Verify `identity_report.json` contains all required cues.
- [x] Verify `production_gate.json` marks the pack as `production_ready`.
- [x] Verify no model/video backend is invoked.
- [x] Generate a dedicated run rough sheet with built-in image generation and store it under:

```text
assets/artist_authored_roughs/imagegen_run_8frame_20260614/
```

- [x] Split the run rough sheet into 8 frames.
- [x] Remove the green key background, trim alpha noise, keep the largest character component, and package run previews.
- [x] Generate dedicated jump and hurt rough sheets with built-in image generation and store them under:

```text
assets/artist_authored_roughs/imagegen_jump_6frame_20260614/
assets/artist_authored_roughs/imagegen_hurt_4frame_20260614/
```

- [x] Split the jump rough sheet into 6 frames.
- [x] Split the hurt rough sheet into 4 frames.
- [x] Remove the green key background, trim alpha noise, keep the largest character component, and package jump/hurt previews.

## Completion

- [x] Generate `outputs/adoptable/character_sprite_asset_pack/`.
- [x] Agent-review the `walk`, `idle`, `run`, `jump`, and `hurt` contact sheets.
- [x] Run focused tests.
- [x] Commit and push the completed pack.
