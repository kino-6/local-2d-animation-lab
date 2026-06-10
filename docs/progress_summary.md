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
   - deterministic `RiggedSpriteBackend` for animation-mechanics validation
6. Optionally generate and upload OpenPose ControlNet pose maps.
7. Save game-asset outputs:
   - `frames/*.png`
   - `effects/*.png` for attack/hit action cues
   - `frames_with_effects/*.png` for composited preview frames
   - `spritesheet.png`
   - `preview.gif`
   - `contact_sheet.png`
   - `contact_sheet_with_effects.png` for attack/hit runs
   - `animation_spec.json`
   - `manifest.json`
   - `evaluation_report.json`
8. Run local heuristic evaluation for consistency, foreground structure, and motion variation.
9. Validate generated manifests in Godot as an E2E game-engine playback check.

## Key Files

- `src/natural_sprite_lab/planning.py`
- `src/natural_sprite_lab/action_catalog.py`
- `src/natural_sprite_lab/backends/comfy_backend.py`
- `src/natural_sprite_lab/backends/rigged_sprite_backend.py`
- `src/natural_sprite_lab/postprocess/action_effects.py`
- `src/natural_sprite_lab/evaluation.py`
- `scripts/pdca_rigged_assets.py`
- `scripts/pdca_sfc_motion_assets.py`
- `scripts/report_animation_viability.py`
- `scripts/pdca_walk_cycle.py`
- `scripts/pdca_multi_asset.py`
- `scripts/regenerate_action_effects.py`
- `godot/project.godot`
- `godot/tests/e2e_runner.gd`
- `docs/local_skills/reference_walk_cycle_pdca.md`
- `docs/local_skills/natural-sprite-asset-pdca/SKILL.md`
- `docs/local_workflows/natural_sprite_asset_improvement_plan.md`

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

Action-variant PDCA with NovaOrangeXL:

- command: `uv run python scripts/pdca_multi_asset.py --input assets/reference/Anima_00013_.png --output-root outputs_action_variants_effect_pdca`
- checkpoint: `novaOrangeXL_v120.safetensors`
- ControlNet: `SDXL\OpenPoseXL2.safetensors`
- best walk: `outputs_action_variants_effect_pdca/anima_00013/walk/walk_strong_pose/contact_sheet.png`, score `0.881`
- best idle: `outputs_action_variants_effect_pdca/anima_00013/idle/idle_balanced/contact_sheet.png`, score `0.944`
- best sword attack: `outputs_action_variants_effect_pdca/anima_00013/attack/attack_sword_balanced/contact_sheet_with_effects.png`, score `0.901`
- best axe attack: `outputs_action_variants_effect_pdca/anima_00013/attack/attack_axe_balanced/contact_sheet_with_effects.png`, score `0.924`
- best bow attack: `outputs_action_variants_effect_pdca/anima_00013/attack/attack_bow_balanced/contact_sheet_with_effects.png`, score `0.969`
- best light hit: `outputs_action_variants_effect_pdca/anima_00013/hit/hit_light_balanced/contact_sheet_with_effects.png`, score `0.929`
- best heavy hit: `outputs_action_variants_effect_pdca/anima_00013/hit/hit_heavy_balanced/contact_sheet_with_effects.png`, score `0.946`
- best knockback hit: `outputs_action_variants_effect_pdca/anima_00013/hit/hit_knockback_balanced/contact_sheet_with_effects.png`, score `0.924`

PDCA finding: generic `attack` and `hit` are too underspecified. The workflow now treats weapon category and damage reaction as first-class variants. OpenPose improves pose, while separate transparent action cue layers make attack arcs, arrows, axe impact, and hit direction readable as game assets.

Godot E2E validation:

- platform: Godot `4.6.3`
- command: `godot --headless --path godot --script res://tests/e2e_runner.gd -- --manifest ..\outputs_action_variants_effect_pdca\anima_00013\attack\attack_bow_balanced\manifest.json`
- result: loaded `attack_bow_balanced` as `AnimatedSprite2D`, frame count `8`, frame size `768x768`, using composited effect frames
- automated test: `tests/test_godot_e2e.py`

These generated outputs are intentionally ignored by git because they are heavy and reproducible from local commands.

Rigged animation-mechanics PDCA:

- command: `uv run python scripts/pdca_rigged_assets.py --input assets/reference/Anima_00013_.png --output-root outputs_rigged_pdca --width 512 --height 512`
- report: `outputs_rigged_pdca/animation_viability_report.md`
- summary: `outputs_rigged_pdca/rigged_asset_pdca_summary.json`
- adopted walk prototype: `outputs_rigged_pdca/anima_00013/walk/walk_rigged/contact_sheet.png`
- adopted bow attack prototype: `outputs_rigged_pdca/anima_00013/attack/attack_bow_rigged/contact_sheet_with_effects.png`
- adopted knockback prototype: `outputs_rigged_pdca/anima_00013/hit/hit_knockback_rigged/contact_sheet_with_effects.png`
- Godot batch validation: all best rigged candidates loaded as 512x512 animations; attack and hit variants use composited effect frames.

Agent review finding: these outputs are acceptable as a technical rig prototype, but not yet as player-facing final animation. The rigged path is now the practical workflow baseline because it preserves part continuity, loop behavior, prop readability, and hit/attack timing better than independent ComfyUI frame generation. The next step is replacing procedural parts with reference-derived or generated character parts while keeping the same rig and viability gates.

SFC-style limited-animation PDCA:

- command: `uv run python scripts/pdca_sfc_motion_assets.py --input assets/reference/Anima_00013_.png --output-root outputs_sfc_motion_pdca --width 512 --height 512`
- rule: plan from high-density motion first, hold nonessential body parts still, then sample game-ready frames.
- adopted summary: `outputs_sfc_motion_pdca/sfc_motion_pdca_summary.json`
- report: `outputs_sfc_motion_pdca/animation_viability_report.md`
- adopted walk: `outputs_sfc_motion_pdca/anima_00013/walk/walk_sfc_120/contact_sheet.png`
- adopted sword attack: `outputs_sfc_motion_pdca/anima_00013/attack/attack_sword_sfc_120/contact_sheet_with_effects.png`
- adopted bow attack: `outputs_sfc_motion_pdca/anima_00013/attack/attack_bow_sfc_120/contact_sheet_with_effects.png`
- adopted knockback: `outputs_sfc_motion_pdca/anima_00013/hit/hit_knockback_sfc_120/contact_sheet_with_effects.png`
- Godot batch validation: all adopted SFC candidates loaded as 512x512 animations; attack and hit variants use composited effect frames.

Agent review finding: SFC-style limited animation reduces puppet-like motion compared with a full-body rig because nonessential body parts are held. It is acceptable as a technical prototype. Remaining issues are contact/weight, force transfer through shoulder/torso/head, and sharper frame selection for anticipation/impact/recovery.

## Current Assessment

Stable:

- Walk animation baseline
- Idle baseline
- Local ComfyUI generation
- OpenPose ControlNet motion control
- Same-seed identity stabilization
- Local evaluation report generation
- PDCA sweeps across settings and checkpoints
- Explicit attack variants: sword, axe, bow
- Explicit hit variants: light stagger, heavy damage, knockback
- Local transparent action effect layers for attack/hit readability
- Godot headless E2E validation for manifest loading and animation playback
- Semantic action-readability metadata in local evaluation reports
- Frame events plus rough hitbox/hurtbox metadata in manifests
- Batch Godot validation for best candidates in a PDCA summary
- Rigged-sprite backend for deterministic animation-mechanics prototypes
- Animation viability metrics for loop closure, motion amplitude, silhouette stability, and rig-like frame continuity
- Motion economy metrics for SFC-style limited animation, including source frame count, sampled source frames, and active part count

Needs more work:

- The rigged prototype is puppet-like and not final visual quality.
- Walk loop closure is improved, but contact/weight still needs stronger polish.
- Bow, sword, and axe attacks are readable as technical prototypes, but need better shoulder/torso force transfer.
- Hit reactions need displacement, weight, and recovery polish before player-facing use.
- Weapon continuity still drifts across frames, especially sword and axe.
- Hit reaction body poses still need stronger action-specific pose templates.
- Effect layers now use frame metadata anchors, but should eventually anchor to detected/generated pose keypoints or masks.
- Reference identity would benefit from local IP-Adapter, a character LoRA, or another reference-guided workflow.
- Evaluation now has semantic metadata checks, but still needs a true local vision semantic recognizer.

See `docs/local_workflows/natural_sprite_asset_improvement_plan.md` for the staged improvement plan.
