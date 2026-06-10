# Progress Summary

## Top-Level Goal

Generate 2D character game assets from:

- a reference character image
- a natural-language instruction

The image is interpreted as character design. The instruction is converted into an asset specification, generation controls, output files, and local evaluation metadata.

Walking animation is the baseline workflow because it is fundamental for 2D character games. It is not the final scope.

## Implemented Workflow

Current local pipeline:

1. Parse the natural-language prompt into `AnimationSpec`.
2. Interpret the reference image into `CharacterProfile`.
3. Build an action-specific `frame_plan`.
4. Build a per-frame `prompt_pack`.
5. Generate frames through a backend:
   - deterministic `DummyBackend`
   - prototype `CutoutWalkBackend`
   - ComfyUI `ComfyBackend`
6. Optionally generate and upload OpenPose ControlNet pose maps.
7. Save game-asset outputs:
   - `frames/*.png`
   - `spritesheet.png`
   - `preview.gif`
   - `contact_sheet.png`
   - `animation_spec.json`
   - `manifest.json`
   - `evaluation_report.json`
8. Run local heuristic evaluation for consistency, foreground structure, and motion variation.

## Key Files

- `src/natural_sprite_lab/planning.py`
- `src/natural_sprite_lab/backends/comfy_backend.py`
- `src/natural_sprite_lab/evaluation.py`
- `scripts/pdca_walk_cycle.py`
- `scripts/pdca_multi_asset.py`
- `docs/local_skills/reference_walk_cycle_pdca.md`

## Best Known Walk Setup

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

## PDCA Results

Checkpoint sweep found two useful baselines:

Visual/default working setup:

- checkpoint: `novaOrangeXL_v120.safetensors`
- reason: clean full-body character output, low background clutter, game-asset-friendly line quality

Highest heuristic score in the local evaluator:

- checkpoint: `illustriousPencilXL_v320.safetensors`
- ControlNet: `SDXL\OpenPoseXL2.safetensors`
- ControlNet strength: `0.75`
- seed: `130018`
- seed step: `0`

Representative local outputs:

- NovaOrange walk candidate: `outputs_checkpoint_sweep/anima_00013/walk/novaOrangeXL_v120_balanced/contact_sheet.png`
- Highest-score walk candidate: `outputs_checkpoint_sweep/anima_00013/walk/illustriousPencilXL_v320_balanced/contact_sheet.png`
- Multi-asset walk: `outputs_multi_asset_pdca/anima_00013/walk/walk_strong_pose/contact_sheet.png`
- Multi-asset idle: `outputs_multi_asset_pdca/anima_00013/idle/idle_strong_pose/contact_sheet.png`
- Multi-asset attack: `outputs_multi_asset_pdca/anima_00013/attack/attack_strong_pose/contact_sheet.png`
- Refined hit reaction: `outputs_multi_asset_pdca_refined/anima_00013/hit/20260610_002534_r01/contact_sheet.png`

These generated outputs are intentionally ignored by git because they are heavy and reproducible from local commands.

## Current Assessment

Stable:

- Walk animation baseline
- Idle baseline
- Local ComfyUI generation
- OpenPose ControlNet motion control
- Same-seed identity stabilization
- Local evaluation report generation
- PDCA sweeps across settings and checkpoints

Needs more work:

- Attack action needs stronger action-specific control.
- Hit reaction improved after prompt refinement but still needs better pose templates.
- Reference identity would benefit from local IP-Adapter, a character LoRA, or another reference-guided workflow.
- Evaluation still needs a semantic action recognizer, not only heuristic image statistics.
