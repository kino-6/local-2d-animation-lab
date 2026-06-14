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
  - `actions/run/` as a gated future action stub, not production-ready.
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
  - `run.production_ready == false`;
  - identity cue checks pass for the adopted actions;
  - no unsupported backend usage;
  - route can still honestly report that broad action coverage is incomplete.

## Documentation

- [x] Add `docs/character_identity_sprite_asset_pack.md`.
- [x] Document that `production_ready` for this pack means:
  - current walk is accepted;
  - current idle is accepted;
  - character identity cues are tracked;
  - future actions are gated instead of silently claimed.
- [x] Document that this does not solve faithful animation of arbitrary reference illustrations.

## Tests

- [x] Add `tests/test_build_character_sprite_asset_pack.py`.
- [x] Verify the output directory layout.
- [x] Verify `walk` has 8 frames and is production-ready.
- [x] Verify `idle` has 4 frames and is production-ready.
- [x] Verify `run` exists only as a non-production stub.
- [x] Verify `identity_report.json` contains all required cues.
- [x] Verify `production_gate.json` marks the pack as `production_ready`.
- [x] Verify no model/video backend is invoked.

## Completion

- [x] Generate `outputs/adoptable/character_sprite_asset_pack/`.
- [x] Agent-review the `walk` and `idle` contact sheets.
- [x] Run focused tests.
- [x] Commit and push the completed pack.
