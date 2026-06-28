# Nun Skirt Boots Action Pack PDCA

## Goal

Create a Godot-loadable 2D game sprite pack from the accepted Nun + skirt + boots design source.

Target actions:

- `idle`
- `walk`
- `run`
- `jump`
- `hurt`
- `attack_sword_light`

## Adopted Design Source

- Design sheet: `outputs/20260616_design_sheet_pdca/20260616_0820_nun_skirt_boots_design_sheet/design_sheet_v4_nun_skirt_boots.png`
- Side-view source: `outputs/20260616_design_sheet_pdca/20260616_0820_nun_skirt_boots_design_sheet/side_view_v4_nun_skirt_boots/side_view_v4_nun_skirt_boots.png`

The design intentionally keeps legs and boots readable instead of using a long robe-only silhouette.

## Production Route

The adopted route is `scripts/build_imagegen_action_pack.py`.

It converts action sprite sheets into:

- transparent per-frame PNGs
- action spritesheets
- preview GIFs
- contact sheets
- `manifest.json`
- `runtime_manifest.json`
- `production_gate.json`
- Godot review metadata

The route is local packaging/post-processing after image generation. It does not use ComfyUI, Wan/video generation, ControlNet, or 120-frame generation.

## PDCA Findings

- Sheet-first generation works better than generating individual loose frames, but only when the generated sheet has enough spacing.
- Projection-based slicing alone is unsafe for dense sheets because neighboring feet, swords, or hair can leak into adjacent frames.
- Connected-component extraction is reliable when the source sheet contains exactly the expected number of separated full-body figures.
- For motion-heavy actions, the production frame count should follow the actual usable generated poses. The light sword attack retake yielded 11 clean poses, so the pack adopts 11 frames instead of forcing a broken 12th frame.
- Walk/run/jump/hurt are reviewable as game actions after transparent extraction and stable canvas normalization.
- Attack is currently a composed character+sword action. Larger slash effects should be added as a separate effect layer in a later pass, not baked into the source sheet.

## Current Output

Adopted package:

`outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/`

Primary review files:

- `pack_review/all_actions_contact_sheet.png`
- `manifest.json`
- `production_gate.json`
- `runtime_manifest.json`

Godot demo default:

`godot/scenes/character_sprite_pack_viewer.tscn`

The viewer now opens this pack by default through:

`outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json`

## Production Decision

Current decision: `production_ready` for this MVP game asset pack route.

Meaning:

- The asset is loadable in Godot.
- All frames are transparent PNGs on a stable canvas.
- Basic actions are present and reviewable.
- No obvious duplicate character/crowd failure remains in the adopted contact sheet.
- It is suitable for game-side timing, scale, and action preview.

Limit:

- This is not proof that arbitrary new actions can be generated automatically.
- Composed sword attack is acceptable for this pass, but separated weapon/effect layers remain the better production architecture for richer combat actions.
