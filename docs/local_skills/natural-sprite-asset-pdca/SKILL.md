---
name: natural-sprite-asset-pdca
description: Generate and improve local-first 2D character game assets from a reference image plus natural-language instruction. Use when working in natural-sprite-lab on asset generation, action variants, ComfyUI/Ollama planning, ControlNet pose control, effect layers, local evaluation, Godot E2E validation, or PDCA improvement loops for walk, idle, attack, hit, and future game animation assets.
---

# Natural Sprite Asset PDCA

## Top Rule

Treat the input image as a character design reference and the prompt as an asset request. Do not reduce the task to shaking, warping, or copying the source pixels. Convert the request into a structured asset spec, generation controls, output artifacts, local evaluation, and a retake plan.

## Core Workflow

1. Parse the prompt into `AnimationSpec`.
2. Interpret the reference into `CharacterProfile`.
3. Select or add an asset recipe in `src/natural_sprite_lab/action_catalog.py`.
4. Build an action-specific `frame_plan` and per-frame `prompt_pack`.
5. Generate frames locally. Use ComfyUI/NovaOrangeXL for visual target exploration, and use `rigged-sprite` for animation-mechanics validation.
6. Use OpenPose ControlNet for body pose control when running ComfyUI.
7. Add separate effect/action cue layers for attacks and hit reactions.
8. Save game-ready outputs and metadata, including frame events, rough hitboxes/hurtboxes, and animation viability metrics.
9. Validate with local heuristics, Godot headless playback, and visual/Agent review.
10. Record findings and apply the smallest useful control change before regenerating.

## Stable Defaults

- Checkpoint: `novaOrangeXL_v120.safetensors`
- ControlNet: `SDXL\OpenPoseXL2.safetensors`
- Seed: `130018`
- Seed step: `0`
- Balanced config: steps `24`, cfg `6.0`, controlnet strength `0.75`
- Strong pose config: steps `24`, cfg `6.0`, controlnet strength `0.9`
- Animation-mechanics backend: `rigged-sprite`
- Adopted prototype output root: `outputs_rigged_pdca`

## Action Semantics

Do not use vague generic `attack` or `hit` requests for quality assessment. Choose explicit variants:

- Attack: `attack_sword`, `attack_axe`, `attack_bow`
- Hit: `hit_light`, `hit_heavy`, `hit_knockback`
- Baseline movement: `walk`, `idle`

When a new action is needed, add it first to `action_catalog.py`, then add or update:

- planning frame templates in `planning.py`
- pose-control handling in `backends/comfy_backend.py`
- optional effect layers in `postprocess/action_effects.py`
- local tests for catalog detection and output contract

## Evaluation Gates

Every candidate should pass these checks before being treated as a useful asset:

- `evaluation_report.json` exists and has no severe foreground or stability issue.
- `contact_sheet.png` is visually inspectable.
- Attack/hit runs have `contact_sheet_with_effects.png`.
- Godot headless validation can load the manifest and start animation playback.
- PDCA summary validation passes for all best candidates when a summary exists.
- `evaluation_report.json` includes semantic action-readability metadata for attack/hit.
- `evaluation_report.json` includes `animation_viability` with acceptable loop closure, frame-to-frame continuity, and rig-like stability.
- Human or Agent review agrees that the sequence reads as animation, not just separate still images.
- The output still matches the top rule: image interpreted as character design, prompt interpreted as asset request.

Passing these gates means "technical rig prototype", not "player-facing final animation". Do not claim production quality until the procedural parts are replaced with reference-derived or generated character parts and the motion still passes the same checks.

## Commands

Run multi-asset PDCA:

```bash
uv run python scripts/pdca_multi_asset.py \
  --input assets/reference/Anima_00013_.png \
  --output-root outputs_action_variants_effect_pdca
```

Run adopted rigged animation-mechanics PDCA:

```bash
uv run python scripts/pdca_rigged_assets.py \
  --input assets/reference/Anima_00013_.png \
  --output-root outputs_rigged_pdca \
  --width 512 \
  --height 512
```

Write the animation viability report:

```bash
uv run python scripts/report_animation_viability.py \
  --summary outputs_rigged_pdca/rigged_asset_pdca_summary.json \
  --output outputs_rigged_pdca/animation_viability_report.md
```

Regenerate only local action cue layers:

```bash
uv run python scripts/regenerate_action_effects.py outputs_action_variants_effect_pdca
```

Validate a generated asset in Godot:

```bash
godot --headless --path godot --script res://tests/e2e_runner.gd -- \
  --manifest ..\outputs_action_variants_effect_pdca\anima_00013\attack\attack_bow_balanced\manifest.json
```

Validate all best candidates in a PDCA summary:

```bash
uv run python scripts/godot_validate_summary.py \
  --summary outputs_action_variants_effect_pdca/multi_asset_pdca_summary.json
```

Run local tests:

```bash
uv run pytest
```

## Improvement Heuristics

- If identity drifts, prefer reference-guided control such as IP-Adapter, character LoRA, or stronger profile constraints before tuning action prompts.
- If an action is unreadable, make the action more specific before increasing pose strength.
- If weapon continuity drifts, split prop/weapon guidance from body generation or add weapon-specific control images.
- If hit reactions look like ordinary poses, add impact source, reaction direction, and effect layers.
- If heuristic scores are high but the action is semantically wrong, trust visual/Godot review and strengthen the semantic evaluator.

For the full local workflow and improvement plan, read `docs/local_workflows/natural_sprite_asset_improvement_plan.md`.
