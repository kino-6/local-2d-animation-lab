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

Store the result as:

```text
assets/artist_authored_roughs/<source_slug>/source_sheet.png
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
- normalize to the accepted pack frame size;
- keep all outputs under `outputs/adoptable/character_sprite_asset_pack/actions/<action>/`;
- create `frames/`, `spritesheet.png`, `preview.gif`, `contact_sheet.png`, `game_previews/`, `production_ready_report.json`, and `notes.md`;
- update pack-level `manifest.json`, `identity_report.json`, `production_gate.json`, and `notes.md`;
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
- no unsupported backend is invoked during packaging.

The gate may accept a game-ready redesign. It does not require faithful pixel animation of the original illustration.

## Tests

Update `tests/test_build_character_sprite_asset_pack.py` for each promoted action.

Tests should verify:

- action frames exist with the expected count;
- all frames have the expected size;
- frames are transparent at the corner after cleanup;
- `preview.gif`, `spritesheet.png`, `contact_sheet.png`, `game_previews/`, and `production_ready_report.json` exist;
- manifest includes the action, phase names, frame count, and `production_ready: true`;
- production gate includes `<action>_production_ready: true`;
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
- `jump`: `assets/artist_authored_roughs/imagegen_jump_6frame_20260614/rough_frames/`
- `hurt`: `assets/artist_authored_roughs/imagegen_hurt_4frame_20260614/rough_frames/`

These examples are reproducible from committed rough frames through local packaging. Their initial rough creation used AI-assisted image generation and should not be described as local-only generation.
