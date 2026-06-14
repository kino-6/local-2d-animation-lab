# Tasks: Dense Source Frames for Jump and Hurt

Archived checkpoints:

```text
docs/archive/Tasks_20260614_character_sprite_pack_polish_godot_completed.md
docs/output_cleanup_20260614_character_sprite_pack.md
```

## Upper Rule

- [ ] Do not return to 120-frame generation, Wan/video generation, ComfyUI exploration, ControlNet research, or broad model integration work.
- [ ] Keep the current adopted pack path:

```text
outputs/adoptable/character_sprite_asset_pack/
```

- [ ] Improve source-frame density for the weakest current actions:
  - `jump`
  - `hurt`
- [ ] Do not claim cross-fade or optical-flow interpolation as production art.
- [ ] Prefer Route A: denser action-specific rough sheets first, then local cleanup, scale normalization, packaging, Godot validation, and visual review.

## Current Findings

- [ ] Record that Godot viewer centering now separates review centering from runtime `bottom_center_canvas` origin.
- [ ] Record that `jump` and `hurt` were previously off-scale because whole-cell rough resize was used.
- [ ] Record that foreground alpha-bbox normalization fixed the most visible scale mismatch.
- [ ] Record that runtime `playback_frame_indices` is only timing expansion:
  - current `jump`: 6 source frames, 8 playback frames;
  - current `hurt`: 4 source frames, 6 playback frames.

## Deliverable

- [ ] Add denser rough sources:

```text
assets/artist_authored_roughs/imagegen_jump_8frame_20260614/
assets/artist_authored_roughs/imagegen_hurt_6frame_20260614/
```

- [ ] Update the adopted pack so:
  - `jump` has 8 source frames;
  - `hurt` has at least 6 source frames;
  - both keep transparent frames, spritesheets, GIFs, contact sheets, runtime metadata, and Godot playback.
- [ ] Preserve the current identity contract:
  - pink bob hair;
  - side-profile anime girl;
  - sailor-style white top;
  - red tie;
  - navy skirt;
  - dark socks;
  - brown shoes.

## Implementation

- [ ] Generate or author a new 8-frame jump rough sheet.
- [ ] Generate or author a new 6-frame hurt rough sheet.
- [ ] Store each source sheet and prompt metadata under `assets/artist_authored_roughs/`.
- [ ] Split rough sheets into `rough_frames/`.
- [ ] Update `scripts/build_character_sprite_asset_pack.py` defaults:
  - `DEFAULT_JUMP_ROUGH`;
  - `DEFAULT_HURT_ROUGH`;
  - jump frame count and phase names;
  - hurt frame count and phase names.
- [ ] Keep foreground alpha-bbox normalization for rough actions.
- [ ] Update runtime playback metadata so source-frame count and playback-frame count are not misleading.
- [ ] Regenerate `outputs/adoptable/character_sprite_asset_pack/`.
- [ ] Keep `outputs/` restricted to adopted outputs and required walk source.

## Godot Review

- [ ] Confirm `godot --path godot` opens the character sprite pack viewer.
- [ ] Confirm headless Godot pack validation passes:

```powershell
godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/character_sprite_asset_pack/manifest.json
```

- [ ] Confirm viewer centering remains correct after action switching.
- [ ] Agent-review `pack_review/all_actions_contact_sheet.png` for:
  - scale consistency;
  - action readability;
  - no duplicate character;
  - no obvious green-key residue;
  - `jump` and `hurt` benefiting from denser source frames.

## Documentation

- [ ] Update `docs/character_identity_sprite_asset_pack.md` with the denser `jump/hurt` source-frame counts.
- [ ] Update `docs/local_skills/route-a-action-rough-to-pack/SKILL.md` with the source-frame-density rule:
  - use more drawn/source frames for production motion;
  - use playback holds only as runtime timing support.
- [ ] Update `docs/output_cleanup_20260614_character_sprite_pack.md` if retained outputs change.

## Tests

- [ ] Update `tests/test_build_character_sprite_asset_pack.py`.
- [ ] Update `tests/test_godot_character_sprite_pack.py`.
- [ ] Verify:
  - `jump` source frame count is 8;
  - `hurt` source frame count is at least 6;
  - Godot playback action count remains 5;
  - loop flags remain correct;
  - production gate remains `production_ready`;
  - consistency gate remains passing.

## Completion

- [ ] Run focused tests.
- [ ] Run Godot headless validation.
- [ ] Agent-review the regenerated pack contact sheet.
- [ ] Commit and push the completed dense-frame upgrade.
