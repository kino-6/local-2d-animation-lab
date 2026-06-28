---
name: route-a-action-rough-to-pack
description: Build adoptable 2D game sprite actions by turning artist-authored or AI-assisted rough action sheets into a local, tested character sprite asset pack. Use when adding or improving character_sprite_asset_pack actions, using built-in image generation or I2I for rough source art, preserving reference identity cues, cleaning green-key/transparent rough frames, packaging spritesheets/GIF/contact sheets, and gating production_ready action assets without returning to 120-frame, Wan, ControlNet, or broad generative research.
---

# Route A Action Rough To Pack

## Top Rule

Prioritize one reviewable 2D game asset package over broad generation research.

Use Route A:

1. Create or accept a rough action sheet.
2. Clean and normalize frames locally.
3. Package frames into `character_sprite_asset_pack`.
4. Gate the action with tests, preview artifacts, identity cues, and Agent visual review.

Do not use this skill for 120-frame generation, Wan/video generation, ControlNet pose research, rigged puppet renderers, or prompt-only animation experiments.

For weapon or visible effect actions, also use
`docs/local_skills/route-a-layered-action-to-pack/SKILL.md` so composed frames remain compatible
while `body`, `weapon`, and `effect` layers are exposed for review/runtime use.

## Scope Boundary

The rough art source may be:

- manually drawn or edited;
- built-in image generation;
- built-in image-to-image from the reference or an accepted sprite;
- another explicitly recorded non-local image source.

If built-in image generation or I2I is used, record it honestly as non-local rough creation. The local reproducible part starts after the rough/source sheet is committed under `assets/artist_authored_roughs/`.

Do not claim that a new action is locally generated unless the rough source was produced by local tools.

## Required Inputs

- Character reference: `assets/reference/Anima_00013_.png` or a documented replacement.
- Accepted base pack or walk asset:
  - `outputs/adoptable/artist_authored_8frame_walk_cleanup/production_ready/`
  - `outputs/adoptable/character_sprite_asset_pack/`
- Accepted pack style reference:
  - `assets/style_reference_sets/character_sprite_pack_v1/contact_sheet.png`
  - `assets/style_reference_sets/character_sprite_pack_v1/manifest.json`
- Action rough frames:
  - `assets/artist_authored_roughs/<source_slug>/rough_frames/<action>_000.png`
  - each frame should contain exactly one character;
  - green-key or transparent background is acceptable;
  - pose phases must be action-specific, not retimed walk.

## Action Spec Rules

Before generating or accepting roughs, write a compact fixed spec:

- `action`: explicit verb, such as `run`, `jump`, `hurt`, `crouch`, `fall`, `attack_sword`
- `direction`: `right`
- `view`: `side`
- `frame_count`: small and action-appropriate
- `loop`: true only for cyclic actions
- `background`: transparent or green-key for cleanup
- `identity_cues`: pink bob hair, side-profile anime girl, sailor white top, red tie, navy skirt, dark socks, brown shoes

Avoid vague actions. Use `hurt_light`, `hurt_heavy`, or `knockback` instead of generic `hit` when the distinction matters. Use `attack_sword`, `attack_axe`, or `attack_bow` instead of generic `attack`.
For modern action-game utility actions, prefer explicit names such as `dodge_backstep`,
`dodge_roll`, `parry_sword`, or `guard_break` instead of generic `avoid` or `defense`.

## Built-In Image Generation / I2I Guidance

Use built-in image generation or I2I when local generation is spending effort without improving the artifact.

Prompt for an action sheet, not a single illustration:

```text
Create a clean 2D game sprite rough sheet, side-view facing right, [N] frames in a [grid] layout.
Same character cues: pink bob hair, anime schoolgirl, sailor-style white top, red tie, navy skirt, dark socks, brown loafers.
Transparent or solid green background. Exactly one character per frame.
Clear [action] phases: [phase list].
No extra people, no weapons unless requested, no text labels inside the cells.
```

For I2I, provide the accepted sprite or reference as style/identity input and ask for a rough sprite sheet. I2I is preferred when identity drift is more damaging than rough pose quality.

Use the accepted pack style reference set as the primary style target. The original illustration is
only the identity reference; do not let new roughs silently become a separate redesign.

When possible, follow the compatible spritesheet-first lessons from
`NO6KIKO/gorest-2d-animation-spritesheet-generator`:

- generate or author the complete action sheet first, then split frames;
- keep one global character scale and root anchor across the sheet;
- detect the source grid/cells before proportional splitting;
- avoid exporting a final frame that is only a duplicate of the first loop frame.

Store the result as:

```text
assets/artist_authored_roughs/<source_slug>/source_sheets/
assets/artist_authored_roughs/<source_slug>/rough_frames/<action>_000.png
assets/artist_authored_roughs/<source_slug>/prompt.md
```

`prompt.md` must record:

- tool/source;
- whether the rough was local or non-local;
- input image used for I2I, if any;
- action spec;
- prompt text;
- visual acceptance notes.

## Local Packaging Workflow

Update `scripts/build_character_sprite_asset_pack.py` when adding a new accepted action.

The builder should:

- accept an explicit `--<action>-rough-frames-dir`;
- remove green-key background;
- threshold low alpha;
- keep the largest alpha component;
- normalize foreground scale from the alpha bounding box instead of resizing the whole rough cell;
- prefer one global sequence scale/root anchor when splitting from a coherent source sheet;
- align grounded actions to the accepted walk ground line;
- preserve vertical arc for airborne actions such as `jump`;
- do not preserve accidental rough-sheet horizontal offsets for reaction actions such as `hurt`;
- keep reaction action visible bounds away from canvas edges so Godot playback does not look like a
  left-right snap;
- keep all outputs under `outputs/adoptable/character_sprite_asset_pack/actions/<action>/`;
- create `frames/`, `spritesheet.png`, `preview.gif`, `contact_sheet.png`, `game_previews/`, `production_ready_report.json`, and `notes.md`;
- update pack-level `manifest.json`, `identity_report.json`, `production_gate.json`, and `notes.md`;
- update `runtime_manifest.json` and every action's `runtime` metadata;
- update `pack_review/all_actions_contact_sheet.png`;
- update `pack_review/consistency_report.json`;
- update `pack_review/style_consistency_report.json`;
- update `pack_review/godot_import_manifest.json`;
- update `pack_review/aseprite_import_notes.md`;
- for weapon/effect actions, add `layered_manifest.json` and `layers/body`, `layers/weapon`, and
  `layers/effect` outputs without replacing composed frames;
- write text artifacts with LF newlines for clean diffs.

Run:

```powershell
uv run python scripts\build_character_sprite_asset_pack.py
```

## Production Gate

An action may be marked `production_ready` only when:

- frame count matches the action spec;
- all frames share one canvas size;
- background is transparent after cleanup;
- there is exactly one readable character;
- no obvious duplicate body or crowd-like failure remains;
- core identity cues are present;
- action phases are readable in `contact_sheet.png` and `preview.gif`;
- output is game-loadable as frames, spritesheet, and GIF;
- style consistency has no `style_retake_needed` action in `pack_review/style_consistency_report.json`;
- frame density is within the action-level review policy or explicitly justified as review-only;
- no unsupported backend is invoked during packaging.

The gate may accept a game-ready redesign. It does not require faithful pixel animation of the original illustration.

## Runtime Review Contract

Every promoted action must preserve the runtime import contract:

- stable transparent canvas;
- `bottom_center_canvas` origin/pivot;
- action `fps`;
- `loop` flag;
- frame duration;
- phase events;
- approximate visible bounding box;
- approximate collision box;
- transition notes.
- hit-frame metadata for attacks or other gameplay-relevant active windows.
- invulnerable-frame metadata for dodge/evasion actions.
- parry-frame metadata for defensive timing actions.
- frame-density review metadata with source frame count, playback frame count, recommended range,
  and decision.

Expected current loop flags:

- loop: `walk`, `idle`, `run`;
- one-shot: `jump`, `hurt`, `dodge_backstep`, `parry_sword`, `attack_sword_light`.

If adding a new action, explicitly choose loop or one-shot in `ACTION_RUNTIME_SPECS` before packaging it.
Do not leave the action as loose image files without runtime metadata.
For attacks, define `hit_frames` in `ACTION_RUNTIME_SPECS`; this is review/runtime metadata and not a
final combat collision box.
For dodge/evasion, define `invulnerable_frames` in `ACTION_RUNTIME_SPECS`; this is review/runtime
metadata and not final invulnerability logic.
For parry/guard timing, define `parry_frames` in `ACTION_RUNTIME_SPECS`; this is review/runtime
metadata and not final defensive collision logic.

For runtime feel, use `playback_frame_indices` only for limited-animation timing expansion. This may
repeat source frames, but it is not a substitute for true drawn inbetweens. When motion still feels
under-sampled, retake the rough sheet with more action-specific frames rather than cross-fading
frames, because cross-fade interpolation creates ghosted game sprites.

Recommended source frame ranges:

- `idle`: 4-6.
- `walk`: 8-12.
- `run`: 8-12.
- `jump`: 12-16.
- `hurt`: 8-12.
- `dodge_backstep`: 8-12.
- `parry_sword`: 8-12.
- `attack_sword_light`: 12-18.

## Tests

Update `tests/test_build_character_sprite_asset_pack.py` for each promoted action.

Tests should verify:

- action frames exist with the expected count;
- all frames have the expected size;
- frames are transparent at the corner after cleanup;
- `preview.gif`, `spritesheet.png`, `contact_sheet.png`, `game_previews/`, and `production_ready_report.json` exist;
- manifest includes the action, phase names, frame count, and `production_ready: true`;
- manifest includes action-level `runtime` metadata;
- `runtime_manifest.json` exists and includes the action;
- `pack_review/all_actions_contact_sheet.png` exists;
- `pack_review/consistency_report.json` passes;
- `pack_review/style_consistency_report.json` exists and has no `style_retake_needed` action;
- `pack_review/godot_import_manifest.json` exists;
- `pack_review/aseprite_import_notes.md` exists;
- production gate includes `<action>_production_ready: true`;
- production gate includes `runtime_metadata_present`, `pack_review_generated`, and `consistency_gate_pass`;
- production gate includes `style_consistency_gate_pass` and `frame_density_pass`;
- backend usage remains false for ComfyUI, Wan/video, ControlNet, new model backend, and 120-frame generation.

Run focused tests:

```powershell
uv run pytest tests\test_build_character_sprite_asset_pack.py tests\test_package_artist_authored_walk_cleanup.py tests\test_build_walk_8frame_baseline.py tests\test_output_layout_policy.py
```

## Review Procedure

Open the action contact sheet and preview GIF before committing.

Look for:

- one character only;
- no green-key residue;
- no extra limbs or duplicate body;
- stable identity cues;
- readable action arc;
- plausible start/end for loops;
- no obvious foot sliding for grounded motion;
- no over-claiming in `production_ready_report.json`.

If the rough fails visually, do not tune cleanup parameters endlessly. Retake the rough sheet, preferably with a clearer phase list or I2I from the accepted sprite.

## Current Accepted Examples

- `run`: `assets/artist_authored_roughs/imagegen_run_8frame_20260614/rough_frames/`
- `jump`: `assets/artist_authored_roughs/imagegen_jump_12frame_tiles_20260615/rough_frames/`
- `hurt`: `assets/artist_authored_roughs/imagegen_hurt_8frame_tiles_20260615/rough_frames/`
- `dodge_backstep`: `assets/artist_authored_roughs/imagegen_dodge_backstep_8frame_tiles_20260615/rough_frames/`
- `parry_sword`: `assets/artist_authored_roughs/imagegen_parry_sword_body_8frame_tiles_20260615/rough_frames/`
  plus native sword/effect layers from `route-a-layered-action-to-pack`.
- `attack_sword_light`: `assets/artist_authored_roughs/imagegen_attack_sword_light_body_12frame_tiles_20260615/rough_frames/`
  plus native sword/effect layers from `route-a-layered-action-to-pack`.
- `attack_sword_light` density upgrade:
  `assets/artist_authored_roughs/route_a_attack_sword_light_body_16frame_retime_20260615/rough_frames/`
  plus native sword/effect layers from `route-a-layered-action-to-pack`.

These examples are reproducible from committed rough frames through local packaging. Their initial rough creation used AI-assisted image generation and should not be described as local-only generation.

Current density rule:

- use real source frames for action readability before adding runtime holds;
- `jump` should keep at least 12 source frames for anticipation, takeoff, airborne, landing, and recovery;
- `hurt` should keep at least 8 source frames for brace, recoil, stagger, settle, and recovery;
- `dodge_backstep` should keep at least 8 source frames for anticipation, push-off, evade, landing,
  and ready return;
- `parry_sword` should keep at least 8 source frames for guard raise, contact, deflect, recoil, and
  ready return;
- `attack_sword_light` should keep 12-18 source frames for anticipation, active slash, overshoot,
  recovery, and ready return;
- attack actions should record active hit frames in runtime metadata;
- dodge and parry actions should record their active utility windows in runtime metadata;
- weapon/effect actions should use native separated layers for production; color-based extraction
  from composed frames is review-only;
- dense action roughs should use multiple 2x2 source sheets instead of one crowded grid to protect
  per-cell resolution;
- playback holds are acceptable timing support, not production art or true interpolation.
