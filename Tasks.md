# Tasks: Reference-Locked 2D Game Sprite Animation

Archived checkpoint:
`docs/archive/Tasks_20260613_reference_identity_lock_checkpoint.md`

Detailed evidence:

- `docs/reference_conditioned_regen_pdca.md`
- `docs/walk_candidate_comparison.md`
- `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`

## Rules

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet.
- [x] Save generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Target adopted source length is 120 frames; short probes are evidence only.
- [x] Long-running ComfyUI scripts must expose queue controls and progress visibility.
  - Use `add_queue_wait_arguments()` for `--max-queue-size` and `--queue-wait-timeout-seconds`.
  - Use `progress_iter()` for frame/batch loops.
  - Use `ProgressTimer` for ComfyUI queue/history waits.
- [x] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, or identity drift are visible.

## Current Finding

- [x] Local IPAdapter identity lock is installed and verified.
  - ComfyUI custom node: `comfyorg/comfyui-ipadapter`.
  - Model: `sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors`.
  - CLIP-Vision expected name: `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors`.
  - Script route: `scripts/regenerate_pose_sequence_controlnet.py`.
- [x] IPAdapter improves reference identity and outfit stability.
- [x] OpenPose-only or front-facing/ambiguous pose controls are not enough for 2D game walking.
- [x] Best current short proof:
  - `outputs/20260613_212815/reference_pose_regen/walk_ipadapter_sideview_pose_mid_8f/`
  - Status: `promising_probe`, not adoption OK.
  - Reason: visual direction improved, but artifact gate still reports `retake_required: 5/8`.

## Next PDCA

- [ ] Build cleaner side-view walk motion controls.
  - Reduce arm/hand ambiguity.
  - Increase readable lower-body phase separation.
  - Keep control frames clean enough to avoid guide burn-in.
- [ ] Run 8-17 frame IPAdapter + side-view pose probes before any 120-frame spend.
  - Start from the current promising settings:
    - denoise `0.78`
    - ControlNet strength `0.92`
    - ControlNet end `0.68`
    - IPAdapter preset `PLUS (high strength)`
    - IPAdapter weight `0.50`
    - IPAdapter weight type `prompt is more important`
    - IPAdapter end `0.62`
- [ ] Gate every short probe.
  - `repair_frame_artifacts.py --mask-only --weapon none`
  - `select_best_span.py --action walk --motion-metric foreground`
  - `analyze_sprite_regions.py`
  - Agent visual review of `comparison_sheet.png`, `contact_sheet.png`, and `preview.gif`.
- [ ] Promote only after a short proof passes all adoption blockers.
  - No visible guide/control burn-in.
  - No duplicate or vanishing lower limbs.
  - Feet/contact read as walking.
  - Identity, outfit, and sprite-style background remain stable.
  - Artifact hard failures `0`.
- [ ] If the side-view pose route still fails after cleaner controls, compare mechanism changes instead of more scalar tuning.
  - Try `IPAdapterAdvanced` scheduling/weight types.
  - Try InstantID/PuLID/reference-only equivalent only after pose controls are clean.
  - Consider Wan/BiRefNet output only as a non-rendered motion guide, not as final pixels.

## Status Vocabulary

- [x] `adopted_animation_candidate`: 120-frame source passes deterministic gates and Agent visual review.
- [x] `selected_proof_only`: useful short proof exists but full adoption blockers remain.
- [x] `promising_probe`: direction is better but gates still reject.
- [x] `rejected_diagnostic`: route/settings fail structurally or semantically.
