# Tasks: Native Layered Weapon And Effect Regeneration

## Upper Rule

- [x] Stop using color-based extraction from composed frames as a production path.
- [x] Regenerate or create native separated sources for `body`, `weapon`, and `effect`.
- [x] Preserve composed-frame compatibility for Godot/Aseprite.
- [x] Scope this pass to:
  - `attack_sword_light`;
  - `parry_sword`.
- [x] Do not add new model backends, 120-frame generation, Wan/video, ComfyUI, or ControlNet work.

## Native Layer Contract

- [x] Use `body` as generated body-only rough art.
- [x] Use `weapon` as a separate sword layer generated independently from the body layer.
- [x] Use `effect` as a separate slash/parry effect layer generated independently from the body layer.
- [x] Compose production frames from:

```text
body -> weapon -> effect
```

- [x] Mark extraction source as:

```text
native_separated_layers
```

- [x] Remove/avoid `heuristic_split_from_composed_frames` as the accepted production route.

## Regenerated Sources

- [x] Add body-only rough source folders:

```text
assets/artist_authored_roughs/imagegen_attack_sword_light_body_12frame_tiles_20260615/
assets/artist_authored_roughs/imagegen_parry_sword_body_8frame_tiles_20260615/
```

- [x] Store:
  - source sheets;
  - split body rough frames;
  - rough contact sheets;
  - prompt metadata.
- [x] Ensure prompts explicitly say:
  - no weapon;
  - no effects;
  - one character only;
  - side-view right-facing;
  - same character identity cues.

## Builder Changes

- [x] Add default body rough paths for native layered attack/parry.
- [x] Build `attack_sword_light` from native body rough + separate weapon/effect layers.
- [x] Build `parry_sword` from native body rough + separate weapon/effect layers.
- [x] Generate per-layer:
  - frames;
  - spritesheet;
  - preview.gif;
  - contact_sheet.
- [x] Compose final action frames from the generated layers.
- [x] Write `layered_manifest.json` with:
  - `source: native_separated_layers`;
  - `layers`;
  - `z_order`;
  - `weapon_visible_frames`;
  - `effect_visible_frames`;
  - timing windows.
- [x] Update runtime and Godot import manifests to point to native layered metadata.

## Production Review

- [x] Review composed attack contact sheet.
- [x] Review attack body/weapon/effect layer sheets.
- [x] Review composed parry contact sheet.
- [x] Review parry body/weapon/effect layer sheets.
- [x] Verify weapon/effect layers are not extracted from body art.
- [x] Mark remaining limits honestly if body-only generation drifts or weapon anchors are approximate.

## Skill And Docs

- [x] Update `docs/local_skills/route-a-layered-action-to-pack/SKILL.md`.
- [x] Update `docs/character_identity_sprite_asset_pack.md`.
- [x] State that native separated layers are the production route.
- [x] State that heuristic extraction is review-only and rejected for production.

## Tests

- [x] Update `tests/test_build_character_sprite_asset_pack.py`.
- [x] Verify `attack_sword_light.layered.source == native_separated_layers`.
- [x] Verify `parry_sword.layered.source == native_separated_layers`.
- [x] Verify all layer outputs exist.
- [x] Verify composed frames still exist.
- [x] Verify action count stays 8.

## Completion

- [x] Run focused Python tests.
- [x] Run Godot headless E2E validation.
- [x] Run `git diff --check`.
