---
name: natural-sprite-controlnet-pdca
description: Local-first workflow for generating 120-frame 2D character game animation assets from a reference image plus natural-language action request using novaOrangeXL and ControlNet OpenPose templates. Use when working on ControlNet pose templates, ComfyUI novaOrangeXL generation, breakage evaluation, retake decisions, PDCA logs, Godot playback validation, or action variants such as walk, idle, sword/axe/bow attacks, and hit reactions.
---

# Natural Sprite ControlNet PDCA

## Top Rule

Use `novaOrangeXL + ControlNet(OpenPose)` as the main generation path. Treat the input image as a character design reference. Do not make rigged puppet animation, cutout shaking, or random independent still generation the primary workflow.

## Output Target

Generate 120-frame action assets. Do not downsample to 8-12 frames in this workflow. Frame reduction belongs to a separate thinning/export skill.

Each adopted run must produce:

- `frames/*.png`
- `contact_sheet.png`
- `preview.gif`
- `spritesheet.png`
- `manifest.json`
- `evaluation_report.json`
- `controlnet_pose/*.png`
- `comfy_workflows/*.json`
- `pdca_log.json` or a summary that points to it

## Required Defaults

- Checkpoint: `novaOrangeXL_v120.safetensors`
- ControlNet: `SDXL\OpenPoseXL2.safetensors`
- Frame count: `120`
- Output policy: preserve all 120 frames as the main asset
- Downsampling policy: use a separate thinning/export workflow
- Seed strategy: fixed seed with `seed_step=0`
- Baseline steps: `24`
- Baseline CFG: `6.0`
- Baseline ControlNet strength: `0.75`
- Strong pose retake: ControlNet strength `0.90`

## Pose Templates

Use `pose_templates/<action>/frame_000.json` through `frame_119.json` as first-class source assets. Render them to `pose_templates/<action>/controlnet/*.png` before generation.

Template frames must include:

- `action`
- `variant`
- `frame_index`
- `phase`
- `keypoints`
- `notes`

Shared phases:

- Walk: `contact`, `down`, `passing`, `up`
- Attack: `ready`, `anticipation`, `active`, `follow_through`, `recover`
- Hit: `neutral`, `impact`, `recoil`, `peak`, `recover`

## Generation Procedure

1. Build or update pose templates:

```bash
uv run python scripts/build_pose_templates.py --output-root pose_templates --frame-count 120
```

2. Run ControlNet PDCA for the target action:

```bash
uv run python scripts/pdca_controlnet_assets.py \
  --input assets/reference/Anima_00013_.png \
  --action attack_sword \
  --output-root outputs_controlnet_pdca \
  --pose-template-root pose_templates \
  --frame-count 120 \
  --retakes 3
```

Common actions are `walk`, `idle`, `attack_sword`, `attack_axe`, `attack_bow`, `hit_light`, `hit_heavy`, and `hit_knockback`.

3. Validate the adopted manifest in Godot:

```bash
uv run python scripts/godot_validate_summary.py \
  --summary outputs_controlnet_pdca/attack_sword_controlnet_summary.json
```

## Breakage Evaluation

Reject or retake when any of these are visible in contact sheets, side-by-side sheets, evaluation reports, or Godot playback:

- Extra character or split foreground
- Missing/tiny/cropped full-body character
- Background clutter instead of transparent/plain game asset framing
- Character identity drift across frames
- Size, center, or color jitter across frames
- Pose does not follow the OpenPose template phase
- Weapon, hand, bow, string, or arrow breaks
- Hit reaction has weak recoil or unclear impact
- Animation reads as unrelated still images

Do not adopt a candidate just because the heuristic score is high. Treat `quality_gate.status == needs_retake_or_manual_review` as blocking until the side-by-side sheet and full contact sheet have been reviewed.

## Retake Policy

- Pose/action mismatch: revise keypoint template first.
- Weak action readability: increase pose contrast or ControlNet strength.
- Identity drift: strengthen identity prompt, lower CFG, lock seed, or add reference guidance.
- Extra characters/background clutter: strengthen negative prompt and full-body solo framing.
- Weapon breakage: add weapon-specific prompt/control guidance.
- Frame jitter: keep `seed_step=0`, reduce stochastic variation, and compare side-by-side sheets.
- Loop issue: revise first and last pose templates.

Record every rejected candidate with failure reasons in the PDCA log.

## Known 2026-06-10 Findings

- `attack_sword` is the best current proof, but still needs weapon continuity and foreground cleanup.
- `attack_bow` is not acceptable from body OpenPose alone; add bow/string/arrow-specific guidance or a line-art/reference control layer.
- `hit_knockback` can create extra face or character fragments; foreground segmentation cleanup is needed.
- `walk` and `idle` generate E2E assets, but full contact sheets must be checked for duplicate/crowd-like frames.

## Non-Goals

- Do not make rig output the main deliverable.
- Do not use high heuristic score alone as adoption evidence.
- Do not adopt without contact sheet review.
- Do not adopt without Godot playback validation.
- Do not downsample 120-frame outputs in this workflow.
- Do not switch away from `novaOrangeXL` as default without a checkpoint comparison.
