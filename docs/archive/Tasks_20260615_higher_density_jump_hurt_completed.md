# Tasks: Higher-Density Jump and Hurt Source Frames

## Upper Rule

- [x] Keep the project focused on the adoptable 2D game sprite pack.
- [x] Do not return to 120-frame generation, Wan/video generation, ComfyUI exploration, ControlNet research, or broad model integration work.
- [x] Keep the adopted output path:

```text
outputs/adoptable/character_sprite_asset_pack/
```

- [x] Improve real source-frame density, not just runtime playback holds.
- [x] Keep `walk`, `idle`, and `run` unchanged unless a regression is found.
- [x] Treat the previous `hurt` left-right snap and `jump` low-resolution look as explicit quality risks.

## Current Findings

- [x] Record that Godot E2E already supports variable action frame counts.
- [x] Record that `hurt.loop=false` was correct; the visible issue was source-frame horizontal offset and edge clipping.
- [x] Record that `jump` low-resolution look came from enlarging low-cell-resolution rough art.
- [x] Record that one large dense grid is risky because each cell becomes too small.
- [x] Prefer multiple 2x2 high-resolution rough sheets over one crowded sheet.

## Target Frame Counts

- [x] Upgrade `jump` from 8 source frames to 12 source frames.
- [x] Upgrade `hurt` from 6 source frames to 8 source frames.
- [x] Keep runtime playback count equal to source frame count for these actions.
- [x] Keep `jump` and `hurt` one-shot actions:
  - `jump.loop == false`
  - `hurt.loop == false`

## New Rough Sources

- [x] Create high-resolution tiled rough sources:

```text
assets/artist_authored_roughs/imagegen_jump_12frame_tiles_20260615/
assets/artist_authored_roughs/imagegen_hurt_8frame_tiles_20260615/
```

- [x] Use three 2x2 sheets for `jump`:
  - sheet 0: crouch, deep crouch, takeoff, early rise
  - sheet 1: rise, apex approach, apex hold, falling extend
  - sheet 2: landing stretch, landing contact, settle, recover
- [x] Use two 2x2 sheets for `hurt`:
  - sheet 0: brace, impact, recoil, peak recoil
  - sheet 1: stagger, crouch settle, recover half, recover
- [x] Store every source sheet, prompt metadata, and split `rough_frames/`.
- [x] Record that built-in image generation is non-local rough creation; the local reproducible pipeline begins from committed rough frames.

## Builder Updates

- [x] Update `scripts/build_character_sprite_asset_pack.py` defaults:
  - `DEFAULT_JUMP_ROUGH`
  - `DEFAULT_HURT_ROUGH`
- [x] Update `ACTION_RUNTIME_SPECS` phase names for:
  - 12-frame `jump`
  - 8-frame `hurt`
- [x] Update the build calls for `jump` and `hurt` frame counts and source slugs.
- [x] Keep current fixes:
  - preserve jump vertical arc;
  - avoid over-enlarging jump rough art;
  - sharpen jump after resize;
  - center reaction actions such as `hurt`;
  - keep `hurt` visible bounds away from canvas edges.
- [x] Regenerate `outputs/adoptable/character_sprite_asset_pack/`.

## Review

- [x] Agent-review the new `jump` contact sheet for:
  - better resolution/readability than the 8-frame version;
  - clear crouch, takeoff, rise, apex, fall, landing, recover sequence;
  - no obvious duplicate character or green-key residue.
- [x] Agent-review the new `hurt` contact sheet for:
  - no left-right snap;
  - no edge clipping;
  - clear impact, recoil, stagger, settle, recover sequence.
- [x] Agent-review `pack_review/all_actions_contact_sheet.png`.

## Documentation

- [x] Update `docs/character_identity_sprite_asset_pack.md`.
- [x] Update `docs/local_skills/route-a-action-rough-to-pack/SKILL.md`.
- [x] Update or add a short note documenting the 2x2 tiled-source rule for dense actions.

## Tests

- [x] Update `tests/test_build_character_sprite_asset_pack.py`.
- [x] Update `tests/test_godot_character_sprite_pack.py`.
- [x] Verify:
  - `jump` frame count is 12;
  - `hurt` frame count is 8;
  - source frame count equals playback frame count for both;
  - `hurt` visible bbox stays inside the canvas with margin;
  - Godot action count remains 5;
  - production gate remains `production_ready`;
  - consistency gate remains passing.

## Completion

- [x] Run focused Python tests.
- [x] Run Godot headless E2E validation.
- [x] Run `git diff --check`.
- [x] Summarize whether frame count increase improved the Godot review result and what still needs a better art-source retake.
