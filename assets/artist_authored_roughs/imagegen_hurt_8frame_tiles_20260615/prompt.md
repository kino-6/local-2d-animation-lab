# imagegen_hurt_8frame_tiles_20260615

- tool/source: built-in image generation
- locality: non-local rough creation; local reproducibility begins from committed `source_sheets/` and `rough_frames/`
- input image: current `character_sprite_asset_pack` contact sheet was used as visible identity/style reference
- action: `hurt`
- direction: `right`
- view: `side`
- frame_count: `8`
- loop: `false`
- background: green-key for local cleanup
- layout: two 2x2 source sheets, split into 8 rough frames

## Prompt Strategy

Use multiple 2x2 sheets instead of one crowded 8-frame grid so each source cell keeps enough pixel detail for cleanup and scaling.

## Phase Plan

1. brace before impact
2. impact recoil backward
3. stronger recoil leaning back
4. peak recoil with knees bent
5. stagger forward after recoil
6. crouch settle absorbing damage
7. half recovery standing up
8. full recovery standing ready pose

## Visual Acceptance Notes

- Accepted as a higher-density hurt source because it separates recoil, peak recoil, stagger, settle, and recovery.
- The builder must continue centering reaction actions and keeping visible bounds away from canvas edges to avoid Godot left-right snap.
