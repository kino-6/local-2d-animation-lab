# Reference Walk Cycle PDCA Skill

Use this local skill when generating new animation frames from a character reference image.

## Top-Level Rule

The broader project goal is to generate 2D character game assets from a reference image and a natural-language instruction. The workflow should interpret the image as character design, parse the instruction into an asset specification, generate game-ready outputs, evaluate them locally, and support retakes.

Walking is the baseline example because it is fundamental for 2D character games. This skill should establish reusable control, recognition, evaluation, and retake patterns that can later support idle, attack, hit reaction, directional variants, and other character assets.

## Goal

Interpret the reference image as a character design. Generate new frames of the same character performing the requested motion. Do not warp or cut out the source pixels as the final method.

## Control

- Use a `CharacterProfile` for identity: hair, eyes, outfit, accessories, expression, palette, and style.
- Use an explicit `frame_plan` for motion: contact, down, passing, up, opposite contact, down, passing, up.
- Use OpenPose ControlNet pose maps when available.
- Use the same seed across frames when identity consistency is more important than pose diversity.
- Avoid prompt text that implies sprite sheets, panels, UI screens, props, ropes, or multiple characters.

## Recognition

- Prefer local vision interpretation through Ollama when it returns valid JSON.
- Fall back to deterministic profile extraction when vision output fails.
- Record all profile fields in `animation_spec.json`.
- Record ComfyUI prompt ids, uploaded pose maps, checkpoint, seed, ControlNet, and strength in `manifest.json`.

## Evaluation

Every run should write `evaluation_report.json` and record its summary in `manifest.json`.

Check at least:

- one foreground character
- stable center and scale across frames
- stable color statistics across frames
- visible motion variation
- no obvious multi-character frames
- no cropped feet for walk cycles

## PDCA Loop

1. Plan: choose checkpoint, ControlNet strength, seed strategy, prompt profile.
2. Do: generate frames locally through ComfyUI.
3. Check: inspect `contact_sheet.png`, `preview.gif`, and `evaluation_report.json`.
4. Act: adjust the profile, negative prompt, pose strength, or seed strategy, then regenerate.

Best-known local command:

```bash
uv run python -m natural_sprite_lab \
  --input assets/reference/Anima_00013_.png \
  --prompt "Create an 8-frame side-view walking animation, facing right. Interpret the reference as a character design and generate new full-body frames of the same character walking." \
  --backend comfy \
  --director fallback \
  --comfy-checkpoint novaOrangeXL_v120.safetensors \
  --width 768 \
  --height 768 \
  --steps 24 \
  --cfg 6.0 \
  --seed 130018 \
  --seed-step 0 \
  --controlnet "SDXL\OpenPoseXL2.safetensors" \
  --controlnet-strength 0.75
```
