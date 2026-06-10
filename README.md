# natural-sprite-lab

`natural-sprite-lab` is a local-first Python prototype for turning one full-body 2D character image plus a natural-language instruction into game-friendly animation assets.

## Top-Level Rule

The project goal is to generate 2D character game assets from:

- one reference character image
- one natural-language instruction

The reference image must be interpreted as a character design, not treated only as pixels to shake, warp, or cut out. Natural language should be converted into a structured asset specification, generation controls, output files, and local evaluation metadata.

Walking animation is the first baseline workflow because it is fundamental for 2D character games. It is an example used to establish the Skill and workflow, not the final scope of the project. The same architecture should grow to support idle, attack, hit reaction, directional variants, and other game-ready character assets.

The first MVP focuses on a single target: an 8-frame side-view walking animation. The output contract is more important than perfect image quality at this stage, so the default backend is a deterministic dummy backend that lets the whole pipeline be tested before a real image-generation system is plugged in.

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
- Sprite sheet, contact sheet, preview GIF, spec JSON, and manifest JSON
- Retake-friendly run directories

Not included yet:

- GUI
- cloud API dependency
- production-grade animation quality
- advanced rigging
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

```bash
python -m natural_sprite_lab \
  --input assets/reference/hero.png \
  --prompt "Create an 8-frame side-view walking animation, facing right, with transparent background."
```

Prototype character-preserving cutout walk with a planning director:

```bash
python -m natural_sprite_lab \
  --input assets/reference/Anima_00013_.png \
  --prompt "Create an 8-frame side-view walking animation, facing right, with transparent background. Preserve the character identity, outfit, hair, colors, and silhouette." \
  --backend cutout-walk \
  --director ollama
```

`--director ollama` asks a local Ollama server for compact JSON planning notes when available, then falls back to the built-in walk-cycle director if Ollama is not reachable. The generated `animation_spec.json` records identity constraints, negative prompts, frame-by-frame walk poses, and director metadata.

Prototype reference interpretation plus ComfyUI generation:

```bash
python -m natural_sprite_lab \
  --input assets/reference/Anima_00013_.png \
  --prompt "Create an 8-frame side-view walking animation, facing right. Interpret the reference as a character design and generate new full-body frames of the same character walking." \
  --backend comfy \
  --director ollama \
  --director-timeout 60 \
  --comfy-url http://127.0.0.1:8188 \
  --comfy-checkpoint novaOrangeXL_v120.safetensors \
  --controlnet "SDXL\OpenPoseXL2.safetensors" \
  --controlnet-strength 0.75 \
  --seed 130018 \
  --seed-step 0
```

The ComfyUI prototype uses the reference image through the director-generated `CharacterProfile` and per-frame prompt pack. OpenPose ControlNet constrains the generated motion, while `--seed-step 0` keeps identity more stable across frames. `novaOrangeXL_v120.safetensors` is the current default because its outputs are visually clean and game-asset friendly; checkpoint sweeps can still compare it against Illustrious, Pony, and other local models. Stronger identity consistency requires a dedicated reference-guided workflow such as IP-Adapter or a character LoRA.

Each run also writes `evaluation_report.json` with local heuristics for foreground count, frame-to-frame center/scale stability, color consistency, and motion variation. The summary is embedded in `manifest.json`.

Local PDCA sweep:

```bash
uv run python scripts/pdca_walk_cycle.py \
  --input assets/reference/Anima_00013_.png \
  --prompt "Create an 8-frame side-view walking animation, facing right. Interpret the reference as a character design and generate new full-body frames of the same character walking."
```

The PDCA criteria are documented in `docs/local_skills/reference_walk_cycle_pdca.md`.

Multi-asset PDCA sweep for the same reference character:

```bash
uv run python scripts/pdca_multi_asset.py \
  --input assets/reference/Anima_00013_.png \
  --output-root outputs_multi_asset_pdca
```

This generates walk, idle, attack, and hit-reaction candidates with local evaluation reports. Walk and idle are currently the most stable; attack and hit are useful baseline outputs but need stronger action-specific control.

Outputs are written under:

```text
outputs/<character_id>/<action>/<run_id>/
```

Each run contains:

- `frames/*.png`
- `spritesheet.png`
- `contact_sheet.png`
- `preview.gif`
- `animation_spec.json`
- `manifest.json`

## Project Layout

```text
src/natural_sprite_lab/
  cli.py
  models.py
  nl_parser.py
  pipeline.py
  evaluation.py
  backends/
    base.py
    comfy_backend.py
    cutout_walk_backend.py
    dummy_backend.py
  planning.py
  postprocess/
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

## Backend Strategy

Backends implement `AnimationBackend.generate_frames(...)`. The MVP ships with `DummyBackend`, but the interface is intentionally small enough to support future implementations such as:

- `ComfyBackend`
- `FutureVideoBackend`
- `FutureRigBackend`

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
