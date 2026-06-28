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
- `actions/dodge_backstep/`
- `actions/parry_sword/`
- `actions/attack_sword_light/`
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
- `dodge_backstep`: cleaned and packaged from the dedicated
  `imagegen_dodge_backstep_8frame_tiles_20260615` rough sheets.
- `parry_sword`: cleaned and packaged from the dedicated body-only
  `imagegen_parry_sword_body_8frame_tiles_20260615` rough sheets plus native sword/effect layers.
- `attack_sword_light`: cleaned and packaged from the dedicated body-only
  `imagegen_attack_sword_light_body_12frame_tiles_20260615` rough sheets plus native sword/effect
  layers.

The repeatable workflow for adding actions is documented in
`docs/local_skills/route-a-action-rough-to-pack/SKILL.md`.

Future action policy:

Run, jump, hurt, dodge, parry, and attack were promoted only after they had dedicated rough sheets with
action-specific poses. Stronger actions still need authored or accepted rough frames and should not
be faked by retiming walk frames.

Built-in image generation or image-to-image is acceptable for rough source art when local generation
is not producing usable assets. In that case, record the rough creation as non-local in `prompt.md`;
the local reproducible pipeline begins from the committed rough frames.

## Runtime Import Contract

The pack now includes runtime metadata so it can be reviewed as a small game asset package rather
than only as loose images.

Generated files:

- `runtime_manifest.json`: action `fps`, loop flag, frame duration, bottom-center origin, visible
  bounding box, approximate collision box, phase events, transition notes, and action utility
  windows such as hit, invulnerable, or parry frames.
- `pack_review/all_actions_contact_sheet.png`: one side-by-side review sheet for `walk`, `idle`,
  `run`, `jump`, `hurt`, `dodge_backstep`, `parry_sword`, and `attack_sword_light`.
- `pack_review/consistency_report.json`: deterministic checks for common canvas size, runtime
  metadata presence, identity cue pass status, loop flag expectations, style consistency, frame
  density policy, and backend usage.
- `pack_review/style_consistency_report.json`: per-action deterministic style labels:
  `style_pass`, `style_review`, or `style_retake_needed`.
- `pack_review/godot_import_manifest.json`: compact import hints for Godot `AnimatedSprite2D` or
  `SpriteFrames`.
- `pack_review/aseprite_import_notes.md`: tag/import notes for Aseprite review.

Style reference set:

```text
assets/style_reference_sets/character_sprite_pack_v1/
```

This set is generated from accepted pack frames and is the primary visual target for future roughs.
The original illustration remains the identity reference, but new action roughs should be manual
edits or image-to-image against the accepted pack style before cleanup.

Layered weapon/effect extensions:

- `actions/attack_sword_light/layered_manifest.json`
- `actions/attack_sword_light/layers/body/`
- `actions/attack_sword_light/layers/weapon/`
- `actions/attack_sword_light/layers/effect/`
- `actions/parry_sword/layered_manifest.json`
- `actions/parry_sword/layers/body/`
- `actions/parry_sword/layers/weapon/`
- `actions/parry_sword/layers/effect/`

These layered outputs are extensions. The composed frames remain the compatibility output for
Godot/Aseprite import. The current promoted weapon/effect actions are marked
`native_separated_layers`. Heuristic color-based extraction from composed frames is review-only and
is rejected as a production route.

Runtime assumptions:

- Keep every frame on the same transparent canvas.
- Use `bottom_center_canvas` as the stable origin/pivot policy.
- Treat `walk`, `idle`, and `run` as loops.
- Treat `jump`, `hurt`, `dodge_backstep`, `parry_sword`, and `attack_sword_light` as one-shot
  actions.
- `dodge_backstep` exposes runtime `invulnerable_frames: [2, 3, 4]`; these are review metadata,
  not final damage-resolution logic.
- `parry_sword` exposes runtime `parry_frames: [3, 4]`; these are review metadata, not final
  defensive collision boxes.
- `attack_sword_light` exposes runtime `hit_frames: [6, 7]`; these are review metadata, not final
  combat collision boxes.
- Weapon/effect actions expose `body`, `weapon`, and `effect` layers with z-order
  `weapon -> body -> effect`, so the character body can cover part of the grip while the effect stays
  in front.
- Collision boxes are approximate review boxes, not final gameplay hitboxes.
- `jump`, `hurt`, `dodge_backstep`, `parry_sword`, and `attack_sword_light` now use dedicated
  source roughs rather than runtime-only timing expansion:
  - `jump`: 12 source frames, 12 playback frames;
  - `hurt`: 8 source frames, 8 playback frames.
  - `dodge_backstep`: 8 source frames, 8 playback frames, invulnerable frames 2, 3, and 4.
  - `parry_sword`: 8 source body frames, native sword/effect layers, 8 playback frames, parry
    frames 3 and 4.
  - `attack_sword_light`: 16 source body frames, native sword/effect layers, 16 playback frames,
    active hit frames 6 and 7.
- Playback timing expansion may still be used for runtime holds in future actions, but it must not be
  described as true inbetween art. When motion feels under-sampled, prefer an authored or I2I rough
  retake with more drawn frames.
- Dense action roughs should use multiple 2x2 source sheets instead of one crowded grid, because
  crowded grids reduce per-frame source resolution before cleanup.

Frame density review guidance:

- `idle`: 4-6 source frames.
- `walk`: 8-12 source frames.
- `run`: 8-12 source frames.
- `jump`: 12-16 source frames.
- `hurt`: 8-12 source frames.
- `dodge_backstep`: 8-12 source frames.
- `parry_sword`: 8-12 source frames.
- `attack_sword_light`: 12-18 source frames.

These ranges are review guidance, not a universal rule. Do not satisfy them with cross-fade ghosts
or blended interpolation; add or retake real source poses for anticipation, active, overshoot, and
recovery.

Spritesheet-first authoring guidance:

The repository also tracks compatible lessons from
`NO6KIKO/gorest-2d-animation-spritesheet-generator`. These do not replace Route A, but they are
useful constraints for future rough-sheet generation:

- prefer generating or authoring a complete spritesheet first, then split it into frames;
- preserve one global character scale across the sheet instead of resizing every frame independently;
- keep a stable root anchor, then expose `bottom_center_canvas` as the runtime origin;
- detect source cells/grid boundaries before falling back to proportional grid cuts;
- do not export a duplicate first frame as the last frame of a loop.

These rules fit the current pack because it is already a game-sprite redesign workflow rather than a
video-generation workflow.

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
- `dodge_backstep`
- `parry_sword`
- `attack_sword_light`

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
- `dodge_backstep.production_ready == true`;
- `parry_sword.production_ready == true`;
- `attack_sword_light.production_ready == true`;
- required identity cues pass on the reference, walk, idle, run, jump, hurt, dodge_backstep,
  parry_sword, and attack_sword_light assets;
- runtime metadata and pack review artifacts exist;
- consistency gate passes for current action coverage;
- style consistency has no `style_retake_needed` action;
- frame density is within the action-level review policy;
- no model or video backend is used.

It does not mean arbitrary future actions are complete.
It also does not mean the sprite is a faithful animated copy of the original reference illustration;
this pack is a production-ready game-sprite redesign based on the reference identity cues.

## Next Work

The next useful step is not more action sprawl. Prefer one of:

- import the current pack into Godot or Aseprite and review actual runtime feel;
- use image-to-image to improve visual consistency across existing actions without reducing source
  frame density;
- add one new action only after preparing an action-specific rough sheet and preserving the runtime
  metadata contract.
