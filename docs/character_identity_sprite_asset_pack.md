# Character Identity Sprite Asset Pack

This route follows the accepted `walk` production-ready output with a small pack-level contract.
It exists to address two open risks:

- the sprite can drift away from the reference and become a different character;
- a single accepted walk cycle does not mean other actions are solved.

## Output

```text
outputs/adoptable/character_sprite_asset_pack/
```

The package contains:

- `actions/walk/`
- `actions/idle/`
- `actions/run/`
- `actions/jump/`
- `actions/hurt/`
- `manifest.json`
- `runtime_manifest.json`
- `identity_report.json`
- `production_gate.json`
- `notes.md`
- `pack_review/`

## Identity Contract

The character must preserve these source-reference cues before an action can be accepted:

- pink bob hair;
- right-facing side-profile anime girl;
- sailor-style white top;
- red tie;
- navy skirt;
- dark socks;
- brown shoes.

The current sprite is accepted as a reference-derived game sprite design. It is not a faithful copy
of the original illustration. The contract prevents future action work from silently dropping the
important character cues.

## Action Scope

Current production-ready actions:

- `walk`: copied from `artist_authored_8frame_walk_cleanup/production_ready/`;
- `idle`: deterministic subtle-idle action derived from the accepted walk sprite.
- `run`: cleaned and packaged from the dedicated `imagegen_run_8frame_20260614` rough sheet.
- `jump`: cleaned and packaged from the dedicated `imagegen_jump_12frame_tiles_20260615` rough sheets.
- `hurt`: cleaned and packaged from the dedicated `imagegen_hurt_8frame_tiles_20260615` rough sheets.

The repeatable workflow for adding actions is documented in
`docs/local_skills/route-a-action-rough-to-pack/SKILL.md`.

Future action policy:

Run, jump, and hurt were promoted only after they had dedicated rough sheets with action-specific
poses. Stronger actions still need authored or accepted rough frames and should not be faked by
retiming walk frames.

Built-in image generation or image-to-image is acceptable for rough source art when local generation
is not producing usable assets. In that case, record the rough creation as non-local in `prompt.md`;
the local reproducible pipeline begins from the committed rough frames.

## Runtime Import Contract

The pack now includes runtime metadata so it can be reviewed as a small game asset package rather
than only as loose images.

Generated files:

- `runtime_manifest.json`: action `fps`, loop flag, frame duration, bottom-center origin, visible
  bounding box, approximate collision box, phase events, and transition notes.
- `pack_review/all_actions_contact_sheet.png`: one side-by-side review sheet for `walk`, `idle`,
  `run`, `jump`, and `hurt`.
- `pack_review/consistency_report.json`: deterministic checks for common canvas size, runtime
  metadata presence, identity cue pass status, loop flag expectations, and backend usage.
- `pack_review/godot_import_manifest.json`: compact import hints for Godot `AnimatedSprite2D` or
  `SpriteFrames`.
- `pack_review/aseprite_import_notes.md`: tag/import notes for Aseprite review.

Runtime assumptions:

- Keep every frame on the same transparent canvas.
- Use `bottom_center_canvas` as the stable origin/pivot policy.
- Treat `walk`, `idle`, and `run` as loops.
- Treat `jump` and `hurt` as one-shot actions.
- Collision boxes are approximate review boxes, not final gameplay hitboxes.
- `jump` and `hurt` now use denser source roughs rather than runtime-only timing expansion:
  - `jump`: 12 source frames, 12 playback frames;
  - `hurt`: 8 source frames, 8 playback frames.
- Playback timing expansion may still be used for runtime holds in future actions, but it must not be
  described as true inbetween art. When motion feels under-sampled, prefer an authored or I2I rough
  retake with more drawn frames.
- Dense action roughs should use multiple 2x2 source sheets instead of one crowded grid, because
  crowded grids reduce per-frame source resolution before cleanup.

## Godot Viewer

The Godot project includes a pack viewer at:

```text
godot/scenes/character_sprite_pack_viewer.tscn
```

It loads:

```text
outputs/adoptable/character_sprite_asset_pack/manifest.json
```

and registers each action as an `AnimatedSprite2D` animation:

- `walk`
- `idle`
- `run`
- `jump`
- `hurt`

The viewer applies the `bottom_center_canvas` origin from runtime metadata so scale and foot/ground
alignment are reviewed in the same coordinate system a game import should use.

Run it from the repository root with:

```powershell
godot --path godot
```

Headless validation is available with:

```powershell
godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/character_sprite_asset_pack/manifest.json
```

## Production Ready Meaning

`production_ready` for this pack means:

- `walk.production_ready == true`;
- `idle.production_ready == true`;
- `run.production_ready == true`;
- `jump.production_ready == true`;
- `hurt.production_ready == true`;
- required identity cues pass on the reference, walk, idle, run, jump, and hurt assets;
- runtime metadata and pack review artifacts exist;
- consistency gate passes for current action coverage;
- no model or video backend is used.

It does not mean arbitrary future actions are complete.

## Next Work

The next useful step is not more action sprawl. Prefer one of:

- import the current pack into Godot or Aseprite and review actual runtime feel;
- use image-to-image to improve visual consistency across existing actions without reducing source
  frame density;
- add one new action only after preparing an action-specific rough sheet and preserving the runtime
  metadata contract.
