# imagegen_jump_12frame_tiles_20260615

- tool/source: built-in image generation
- locality: non-local rough creation; local reproducibility begins from committed `source_sheets/` and `rough_frames/`
- input image: current `character_sprite_asset_pack` contact sheet was used as visible identity/style reference
- action: `jump`
- direction: `right`
- view: `side`
- frame_count: `12`
- loop: `false`
- background: green-key for local cleanup
- layout: three 2x2 source sheets, split into 12 rough frames

## Prompt Strategy

Use multiple 2x2 sheets instead of one crowded 12-frame grid so each source cell keeps enough pixel detail for cleanup and scaling.

## Phase Plan

1. neutral crouch anticipation
2. deeper crouch compression
3. explosive takeoff with legs extending
4. early rise leaving the ground
5. rising upward with knees bent
6. apex approach with tucked knees
7. apex hold compact tuck
8. beginning to fall with legs extending forward
9. falling with legs reaching toward ground
10. landing contact with bent knees
11. landing settle absorbing impact
12. recover to standing ready pose

## Visual Acceptance Notes

- Accepted as a higher-density jump source because it provides more actual drawn phases than the 8-frame rough.
- Known risk: rough-sheet identity and proportions still vary by sheet; local cleanup normalizes scale and canvas but cannot fully redraw inconsistent art.
