# Tasks: Attack Sword Light 12-Frame MVP

Archived checkpoints:

```text
docs/archive/Tasks_20260615_higher_density_jump_hurt_completed.md
docs/output_cleanup_20260615_high_density_actions.md
```

## Upper Rule

- [x] Keep the project focused on one adoptable 2D game sprite pack.
- [x] Do not return to 120-frame generation, Wan/video generation, ComfyUI exploration, ControlNet research, or broad model integration work.
- [x] Do not attempt a generic attack system yet.
- [x] Implement one constrained action first:

```text
attack_sword_light
```

- [x] Keep the adopted output path:

```text
outputs/adoptable/character_sprite_asset_pack/
```

## Current Findings

- [x] Record that dense action roughs should use multiple 2x2 source sheets.
- [x] Record that attack is harder than locomotion because hand, arm, weapon, and active timing must stay connected.
- [x] Record that weapon consistency is a new gate, separate from character identity.
- [x] Keep previous fixes:
  - source frame count must be real source art, not playback holds;
  - action visible bounds must stay away from canvas edges;
  - one-shot actions must not loop in Godot.

## Action Spec

- [x] Define `attack_sword_light`:
  - direction: `right`;
  - view: `side`;
  - frame_count: `12`;
  - loop: `false`;
  - weapon: simple one-handed short sword;
  - background: transparent after cleanup;
  - active hit frames: `[5, 6]`.
- [x] Use phase names:
  - `ready`;
  - `anticipation`;
  - `draw_back`;
  - `windup`;
  - `slash_start`;
  - `active_slash`;
  - `active_follow_through`;
  - `overshoot`;
  - `recoil`;
  - `settle`;
  - `recover`;
  - `ready_return`.

## New Rough Source

- [x] Create a high-resolution tiled rough source:

```text
assets/artist_authored_roughs/imagegen_attack_sword_light_12frame_tiles_20260615/
```

- [x] Use three 2x2 sheets:
  - sheet 0: ready, anticipation, draw back, windup;
  - sheet 1: slash start, active slash, active follow-through, overshoot;
  - sheet 2: recoil, settle, recover, ready return.
- [x] Store every source sheet, prompt metadata, and split `rough_frames/`.
- [x] Record that built-in image generation is non-local rough creation; the local reproducible pipeline begins from committed rough frames.

## Builder Updates

- [x] Add `DEFAULT_ATTACK_SWORD_LIGHT_ROUGH`.
- [x] Add `--attack-sword-light-rough-frames-dir`.
- [x] Add `attack_sword_light` to `ACTION_RUNTIME_SPECS`.
- [x] Add `hit_frames: [5, 6]` and expose it in runtime metadata.
- [x] Build and package `actions/attack_sword_light/`.
- [x] Include the action in:
  - manifest;
  - runtime manifest;
  - identity report;
  - production gate;
  - pack review contact sheet;
  - Godot import manifest;
  - Aseprite notes.

## Review

- [x] Agent-review `actions/attack_sword_light/contact_sheet.png` for:
  - one character only;
  - sword is visible and connected to hand;
  - clear anticipation, active, follow-through, recover sequence;
  - active frames are readable;
  - no edge clipping;
  - no obvious green-key residue.
- [x] Agent-review `pack_review/all_actions_contact_sheet.png`.
- [x] Mark known limits honestly if weapon consistency or pose drift remains.

## Documentation

- [x] Update `docs/character_identity_sprite_asset_pack.md`.
- [x] Update `docs/local_skills/route-a-action-rough-to-pack/SKILL.md`.
- [x] Record the attack route as `review_ready_attack_mvp` if visual quality is not as strong as locomotion.

## Tests

- [x] Update `tests/test_build_character_sprite_asset_pack.py`.
- [x] Update `tests/test_godot_character_sprite_pack.py`.
- [x] Verify:
  - action count is 6;
  - `attack_sword_light` frame count is 12;
  - `attack_sword_light.loop == false`;
  - source frame count equals playback frame count;
  - hit frames are `[5, 6]`;
  - visible bbox stays inside the canvas with margin;
  - production gate remains passing for the pack;
  - unsupported backend flags remain false.

## Completion

- [x] Run focused Python tests.
- [x] Run Godot headless E2E validation.
- [x] Run `git diff --check`.
- [x] Commit and push the completed attack MVP if validation passes.
