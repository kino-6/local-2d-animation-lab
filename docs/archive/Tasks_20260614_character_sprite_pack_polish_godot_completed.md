# Tasks: Character Sprite Asset Pack Polish

Archived checkpoint:

```text
docs/archive/Tasks_20260614_character_sprite_asset_pack_actions_completed.md
```

## Upper Rule

- [x] Do not add new actions in this task.
- [x] Polish the existing `walk`, `idle`, `run`, `jump`, and `hurt` pack for practical game review.
- [x] Keep the Route A boundary: rough creation may be non-local, but committed rough-frame packaging must remain locally reproducible.
- [x] Do not return to 120-frame generation, Wan/video generation, ComfyUI exploration, ControlNet research, or broad model integration work.

## Deliverable

- [x] Keep the adopted package at:

```text
outputs/adoptable/character_sprite_asset_pack/
```

- [x] Add pack-level runtime metadata suitable for Godot/Aseprite import review:
  - action `fps`;
  - `loop` flag;
  - frame duration;
  - stable origin/pivot;
  - approximate collision box;
  - transition notes.
- [x] Add a pack-level review folder:

```text
outputs/adoptable/character_sprite_asset_pack/pack_review/
```

- [x] Include:
  - `all_actions_contact_sheet.png`;
  - `consistency_report.json`;
  - `godot_import_manifest.json`;
  - `aseprite_import_notes.md`.

## Implementation

- [x] Update `scripts/build_character_sprite_asset_pack.py`.
- [x] Generate runtime metadata for every action without invoking any model/video backend.
- [x] Generate a single all-actions contact sheet for side-by-side visual review.
- [x] Generate deterministic consistency metrics:
  - frame count by action;
  - common canvas size;
  - origin policy;
  - approximate visible bbox;
  - ground/bottom range;
  - identity cue pass status;
  - backend usage status.
- [x] Add pack-level production gate checks:
  - `runtime_metadata_present`;
  - `pack_review_generated`;
  - `consistency_gate_pass`;
  - existing action production checks still pass.
- [x] Fix rough-action scale normalization so `jump` and `hurt` do not appear off-scale in game review:
  - normalize from foreground alpha bbox, not full rough-cell resize;
  - align grounded actions to the accepted walk ground line;
  - preserve jump vertical arc.
- [x] Add runtime playback timing expansion without pretending to create true inbetween art:
  - `jump`: 6 source frames, 8 playback frames;
  - `hurt`: 4 source frames, 6 playback frames.

## Documentation

- [x] Update `docs/character_identity_sprite_asset_pack.md` with:
  - runtime metadata meaning;
  - Godot/Aseprite import assumptions;
  - current pack review artifacts;
  - the next recommended work after pack polish.
- [x] Update `docs/local_skills/route-a-action-rough-to-pack/SKILL.md` so future action work also preserves runtime metadata and pack review outputs.

## Tests

- [x] Update `tests/test_build_character_sprite_asset_pack.py`.
- [x] Verify `runtime_manifest.json` exists.
- [x] Verify every action has `runtime` metadata in `manifest.json`.
- [x] Verify loop flags:
  - `walk`, `idle`, `run` are looped;
  - `jump`, `hurt` are non-looping.
- [x] Verify `pack_review/all_actions_contact_sheet.png` exists.
- [x] Verify `pack_review/consistency_report.json` exists and passes.
- [x] Verify `pack_review/godot_import_manifest.json` exists.
- [x] Verify `pack_review/aseprite_import_notes.md` exists.
- [x] Verify production gate includes and passes the new pack polish checks.
- [x] Verify Godot pack playback uses expanded runtime frame counts for `jump` and `hurt`.

## Completion

- [x] Regenerate `outputs/adoptable/character_sprite_asset_pack/`.
- [x] Agent-review the all-actions contact sheet.
- [x] Run focused tests.
- [x] Record whether the pack is now ready for runtime import review.
