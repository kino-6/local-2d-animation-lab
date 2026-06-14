# imagegen_jump_8frame_20260614

- tool/source: built-in image generation
- locality: non-local rough creation; local reproducibility begins from this committed `source_sheet.png` and `rough_frames/`
- input image: none
- action: `jump`
- direction: `right`
- view: `side`
- frame_count: `8`
- loop: `false`
- background: green-key for local cleanup

## Prompt

Create a clean 2D game sprite rough sheet, side-view facing right, exactly 8 frames in a 4 columns x 2 rows grid.
Use the same character cues in every cell: pink bob hair, right-facing side profile, sailor-style white top, red tie, navy skirt, dark socks, brown loafers.
Action: jump, non-looping. Clear phases in reading order: anticipation crouch, takeoff, early rise, rising tuck, apex tuck, falling extend, landing contact, landing recovery.
Use hand-drawn 2D game sprite rough art with readable silhouette and clean flat colors.
Each cell must contain exactly one full-body character with generous padding, consistent scale, and consistent side-view right-facing direction.
Use a perfectly flat solid `#00ff00` chroma-key background with no shadows, no floor plane, no texture, and no gradients.
No text labels, no frame numbers, no extra people, no duplicate bodies, no weapons, no effects, no watermark.
Do not use `#00ff00` anywhere in the character.

## Visual Acceptance Notes

- Accepted as a denser jump rough because the eight frames include anticipation, takeoff, airborne tuck, falling extension, landing, and recovery.
- The committed rough frames are not final art by themselves; the local pack builder removes green-key background, keeps the largest character component, normalizes alpha-bbox scale, and writes the adopted transparent frames.
