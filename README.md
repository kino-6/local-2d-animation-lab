# natural-sprite-lab

`natural-sprite-lab` is a local-first Python prototype for turning one full-body 2D character image plus a natural-language instruction into game-friendly 120-frame animation assets.

## Top-Level Rule

The project goal is to generate 2D character game assets from:

- one reference character image
- one natural-language instruction

The reference image must be interpreted as a character design, not treated only as pixels to shake, warp, or cut out. Natural language should be converted into a structured asset specification, generation controls, output files, and local evaluation metadata.

Walking animation is the first baseline workflow because it is fundamental for 2D character games. It is an example used to establish the Skill and workflow, not the final scope of the project. The same architecture should grow to support idle, attack, hit reaction, directional variants, and other game-ready character assets.

The current main path focuses on 120-frame action animation generated with `novaOrangeXL + ControlNet(OpenPose)`. Frame thinning or export to 8-12 frame sheets is intentionally a separate later workflow.

## Why Spec-Based

Natural-language prompts are flexible, but game pipelines need predictable artifacts. This project parses each prompt into an `AnimationSpec` before generation so every backend works from the same structured contract:

- action, direction, frame count, loop behavior
- tone and background preferences
- identity preservation intent
- requested output formats
- run metadata for retakes and downstream tools

That keeps the CLI, backend, postprocessing, and future integrations loosely coupled.

## MVP Scope

Current support:

- CLI input: one character image and one prompt
- Rule-based prompt parser
- Optional walk-cycle director with Ollama fallback support
- Side-view walk spec generation
- Dummy backend that creates 8 transparent PNG frames
- Prototype cutout backend that preserves source pixels with coarse walk-cycle transforms
- Prototype ComfyUI backend that generates new frames from director prompt packs
- Reusable OpenPose keypoint templates for ControlNet-driven action generation
- 120-frame ControlNet PDCA workflow with adopted/rejected candidate logs
- Prototype rigged-sprite backend that creates deterministic part-based frames for animation-mechanics validation
- Action-specific variants for sword, axe, bow, light hit, heavy hit, and knockback
- Transparent action effect layers for attack and hit readability
- Godot 4 E2E harness for loading generated manifests and validating playback
- Sprite sheet, contact sheet, preview GIF, spec JSON, and manifest JSON
- Retake-friendly run directories

Not included yet:

- GUI
- cloud API dependency
- production-grade animation quality
- production-grade rigging or character-part extraction
- hardcoded model vendor integration

## Install

Python 3.11+ is required.

```bash
uv sync
```

Or with pip:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Example CLI

Keep this README limited to stable entry points. Specific PDCA attempts, failed settings, and generated output paths belong in `docs/` reports and local Skills, not in this file.

Stable command entry points:

- Build reusable controls: `scripts/build_pose_templates.py`
- Import extracted motion-source poses: `scripts/import_motion_source_pose.py`
- Run SDXL/OpenPose PDCA: `scripts/pdca_controlnet_assets.py`
- Select usable Wan spans: `scripts/select_best_span.py`
- Export compact evidence: `scripts/export_review_package.py`
- Validate selected outputs in Godot: `scripts/godot_validate_summary.py`
- Gate local artifacts before adoption: `scripts/repair_frame_artifacts.py`
- Prepare a clean Wan start frame: `scripts/prepare_wan_start_frame.py`

```bash
python -m natural_sprite_lab \
  --input assets/reference/hero.png \
  --prompt "Create a 120-frame side-view walking animation, facing right, with transparent background."
```

Prototype character-preserving cutout walk with a planning director:

```bash
python -m natural_sprite_lab \
  --input assets/reference/Anima_00013_.png \
  --prompt "Create a 120-frame side-view walking animation, facing right, with transparent background. Preserve the character identity, outfit, hair, colors, and silhouette." \
  --backend cutout-walk \
  --director ollama
```

`--director ollama` asks a local Ollama server for compact JSON planning notes when available, then falls back to the built-in walk-cycle director if Ollama is not reachable. The generated `animation_spec.json` records identity constraints, negative prompts, frame-by-frame walk poses, and director metadata.

Prototype reference interpretation plus ComfyUI generation:

```bash
python -m natural_sprite_lab \
  --input assets/reference/Anima_00013_.png \
  --prompt "Create a 120-frame side-view walking animation, facing right. Interpret the reference as a character design and generate new full-body frames of the same character walking." \
  --backend comfy \
  --workflow-preset novaOrangeXL \
  --pose-template-root pose_templates \
  --director ollama \
  --director-timeout 60 \
  --comfy-url http://127.0.0.1:8188 \
  --comfy-checkpoint novaOrangeXL_v120.safetensors \
  --controlnet "SDXL\OpenPoseXL2.safetensors" \
  --controlnet-strength 0.75 \
  --seed 130018 \
  --seed-step 0
```

The ComfyUI prototype uses the reference image through the director-generated `CharacterProfile` and per-frame prompt pack. OpenPose ControlNet constrains the generated motion from reusable templates, while `--seed-step 0` keeps identity more stable across frames. `novaOrangeXL_v120.safetensors` is the current default because its outputs are visually clean and game-asset friendly; checkpoint sweeps can still compare it against Illustrious, Pony, and other local models. Stronger identity consistency requires a dedicated reference-guided workflow such as IP-Adapter or a character LoRA.

Build reusable OpenPose templates:

```bash
uv run python scripts/build_pose_templates.py \
  --output-root pose_templates \
  --frame-count 120
```

Run the main ControlNet PDCA proof for sword attack:

```bash
uv run python scripts/pdca_controlnet_assets.py \
  --input assets/reference/Anima_00013_.png \
  --action attack_sword \
  --output-root outputs_controlnet_pdca \
  --pose-template-root pose_templates \
  --frame-count 120 \
  --retakes 3
```

Each run also writes `evaluation_report.json` with local heuristics for foreground count, frame-to-frame center/scale stability, color consistency, and motion variation. The summary is embedded in `manifest.json`.
Current 120-frame ControlNet PDCA findings are documented in `docs/controlnet_pdca_findings.md`.
Current Wan I2V walk findings are documented in `docs/wan_i2v_walk_findings.md`.
Current Wan-to-Image2Image refinement findings are documented in `docs/img2img_refine_pdca_findings.md`.
Current artifact repair and quality-gate findings are documented in `docs/artifact_repair_pdca_findings.md`.
The local cleanup and next-task planning report is documented in `docs/local_cleanup_and_next_tasks_report.md`.

Practical animation-mechanics prototype:

```bash
uv run python scripts/pdca_rigged_assets.py \
  --input assets/reference/Anima_00013_.png \
  --output-root outputs_rigged_pdca \
  --width 512 \
  --height 512
```

The rigged-sprite route is now historical diagnostic tooling only. It is not the main generation path. The main path is reusable OpenPose templates plus `novaOrangeXL + ControlNet`.

Historical SFC-style limited-animation diagnostic:

```bash
uv run python scripts/pdca_sfc_motion_assets.py \
  --input assets/reference/Anima_00013_.png \
  --output-root outputs_sfc_motion_pdca \
  --width 512 \
  --height 512
```

This historical route plans motion internally at 120 source frames and compares limited motion with puppet-like motion. It remains useful for diagnostics, but not for final generated assets.

Generate the viability report for the adopted prototype outputs:

```bash
uv run python scripts/report_animation_viability.py \
  --summary outputs_rigged_pdca/rigged_asset_pdca_summary.json \
  --output outputs_rigged_pdca/animation_viability_report.md
```

Validate those adopted prototype outputs in Godot:

```bash
uv run python scripts/godot_validate_summary.py \
  --summary outputs_sfc_motion_pdca/sfc_motion_pdca_summary.json
```

Local PDCA sweep:

```bash
uv run python scripts/pdca_walk_cycle.py \
  --input assets/reference/Anima_00013_.png \
  --prompt "Create an 8-frame side-view walking animation, facing right. Interpret the reference as a character design and generate new full-body frames of the same character walking."
```

The PDCA criteria are documented in `docs/local_skills/reference_walk_cycle_pdca.md`.
The broader asset-generation workflow is documented in `docs/local_skills/natural-sprite-asset-pdca/SKILL.md`; the current ControlNet main path is documented in `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`, with the improvement roadmap in `docs/local_workflows/natural_sprite_asset_improvement_plan.md`.

Multi-asset PDCA sweep for the same reference character:

```bash
uv run python scripts/pdca_multi_asset.py \
  --input assets/reference/Anima_00013_.png \
  --output-root outputs_multi_asset_pdca
```

This generates walk, idle, attack, and hit-reaction candidates with local evaluation reports. Walk and idle are currently the most stable; attack and hit are useful baseline outputs but need stronger action-specific control.

Attack and hit are split into explicit semantic variants instead of being treated as generic poses:

- attacks: `attack_sword`, `attack_axe`, `attack_bow`
- hit reactions: `hit_light`, `hit_heavy`, `hit_knockback`

For attack and hit runs, the pipeline also writes transparent action cue layers and composited previews:

- `effects/*_effect.png`
- `effect_contact_sheet.png`
- `frames_with_effects/*_with_effect.png`
- `contact_sheet_with_effects.png`

Regenerate only those local effect layers for an existing output root:

```bash
uv run python scripts/regenerate_action_effects.py outputs_action_variants_effect_pdca
```

Godot E2E validation:

```bash
godot --headless --path godot --script res://tests/e2e_runner.gd -- \
  --manifest ..\outputs_action_variants_effect_pdca\anima_00013\attack\attack_bow_balanced\manifest.json
```

The Godot harness reads `manifest.json`, resolves generated PNG frames, builds an `AnimatedSprite2D`, starts playback, and prints a JSON validation result. The pytest suite also runs this path when `godot` is installed.

Validate all best candidates from a PDCA summary:

```bash
uv run python scripts/godot_validate_summary.py \
  --summary outputs_action_variants_effect_pdca/multi_asset_pdca_summary.json
```

Outputs are written under:

```text
outputs/<character_id>/<action>/<run_id>/
```

Each run contains:

- `frames/*.png`
- `effects/*.png` for attack/hit runs
- `frames_with_effects/*.png` for attack/hit runs
- `spritesheet.png`
- `contact_sheet.png`
- `contact_sheet_with_effects.png` for attack/hit runs
- `preview.gif`
- `animation_spec.json`
- `manifest.json`

`manifest.json` includes local evaluation summaries, semantic action-readability metadata, frame events, rough hitboxes/hurtboxes, frame timing, and Godot-readable frame paths.

Rigged-sprite runs also include `animation_viability` metadata for frame count, motion amplitude, loop closure, silhouette stability, frame-to-frame continuity, whether the result appears rig-driven rather than redrawn independently, and `motion_economy` data for SFC-style limited animation.

## Project Layout

```text
src/natural_sprite_lab/
  cli.py
  action_catalog.py
  models.py
  nl_parser.py
  pipeline.py
  evaluation.py
  backends/
    base.py
    comfy_backend.py
    cutout_walk_backend.py
    dummy_backend.py
    rigged_sprite_backend.py
  planning.py
  postprocess/
    action_effects.py
    gif_preview.py
    spritesheet.py
  utils/
    io.py
    paths.py
tests/
assets/
  reference/
outputs/
```

Godot E2E harness:

```text
godot/
  project.godot
  scenes/
    animation_viewer.tscn
  scripts/
    asset_manifest.gd
    animation_viewer.gd
  tests/
    e2e_runner.gd
```

## Backend Strategy

Backends implement `AnimationBackend.generate_frames(...)`. The MVP ships with `DummyBackend`, but the interface is intentionally small enough to support future implementations such as:

- `ComfyBackend`
- `FutureVideoBackend`
- `RiggedSpriteBackend`

Rigged and cutout backends are historical diagnostics only. The main generation path remains reference interpretation plus reusable action controls, currently `novaOrangeXL`, OpenPose templates, Wan video generation, and explicit local quality gates.

## Roadmap

- idle animation
- battle attack animation
- hit reaction animation
- multiple directions
- transparent character extraction
- character consistency improvements
- real backend integration
- batch asset generation
- metadata export for game engines
