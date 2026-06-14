# imagegen_hurt_6frame_20260614

- tool/source: built-in image generation
- locality: non-local rough creation; local reproducibility begins from this committed `source_sheet.png` and `rough_frames/`
- input image: none
- action: `hurt`
- direction: `right`
- view: `side`
- frame_count: `6`
- loop: `false`
- background: green-key for local cleanup

## Prompt

Create a clean 2D game sprite rough sheet, side-view facing right, exactly 6 frames in a 3 columns x 2 rows grid.
Use the same character cues in every cell: pink bob hair, right-facing side profile, sailor-style white top, red tie, navy skirt, dark socks, brown loafers.
Action: hurt reaction, one-shot. Clear phases in reading order: neutral brace, impact recoil backward, stagger step backward, peak stagger leaning back, settle with knees bent, recover to standing.
Use hand-drawn 2D game sprite rough art with readable silhouette and clean flat colors.
Each cell must contain exactly one full-body character with generous padding, consistent scale, and consistent side-view right-facing direction.
Use a perfectly flat solid `#00ff00` chroma-key background with no shadows, no floor plane, no texture, and no gradients.
No text labels, no frame numbers, no extra people, no duplicate bodies, no weapons, no effects, no impact stars, no watermark.
Do not use `#00ff00` anywhere in the character.

## Visual Acceptance Notes

- Accepted as a denser hurt rough because it separates brace, recoil, stagger, settle, and recovery rather than relying on repeated source frames.
- The committed rough frames are not final art by themselves; the local pack builder removes green-key background, keeps the largest character component, normalizes alpha-bbox scale, and writes the adopted transparent frames.
