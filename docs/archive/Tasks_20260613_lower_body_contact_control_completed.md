# Tasks: Reference-Locked 2D Game Sprite Animation

Archived checkpoint:
`docs/archive/Tasks_20260613_reference_identity_lock_checkpoint.md`

Detailed evidence:

- `docs/reference_conditioned_regen_pdca.md`
- `docs/reference_lock_motion_template_deep_dive.md`
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
- [x] IPAdapterAdvanced + cleaner side-view pose controls are implemented and verified.
- [x] Best current short proof from this loop:
  - `outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/`
  - Status: `selected_proof_only`, not adoption OK.
  - Reason: artifact/span gates have hard failures `0`, but Agent visual review and region diagnostics still flag foot/contact artifacts and silhouette redraw risk.
- [x] Do not spend on 120-frame promotion yet.
  - The best proof is useful evidence for the route, but it does not satisfy the project adoption rule for a 2D game asset.

## Completed PDCA: IPAdapterAdvanced + Side-View Motion Template

- [x] Add `IPAdapterAdvanced` mode to `scripts/regenerate_pose_sequence_controlnet.py`.
  - Support `weight_type`, `combine_embeds`, `embeds_scaling`, `start_at`, `end_at`.
  - Keep simple `IPAdapter` mode available as the baseline.
  - First matrix:
    - `composition precise`, weight `0.45`, end `0.60`, embeds scaling `K+mean(V) w/ C penalty`.
    - `style transfer precise`, weight `0.55`, end `0.62`, embeds scaling `K+mean(V) w/ C penalty`.
    - `linear`, weight `0.50`, end `0.52`, embeds scaling `V only`.
  - Results:
    - `composition precise`: rejected; duplicate silhouette hard failures `8/8`.
    - `style transfer precise`: best unmasked advanced probe; artifact gate `retake_required: 3/8`, span score `0.72707`.
    - `linear`: rejected; duplicate silhouette hard failures `6/8`.
- [x] Test IPAdapter attention masks because advanced-mode probes still distorted lower-body motion.
  - upper-body-heavy mask;
  - whole-character soft mask;
  - head/hair-only mask.
  - Goal: lock identity where it matters while letting lower-body motion follow the action template.
  - Results:
    - upper-body mask: best probe. Artifact gate `no_repair_needed: 8/8`, span hard failures `0`, region decision `retake_required: 2/8`.
    - whole-character mask: structurally stable but stiffer. Artifact gate `no_repair_needed: 8/8`, span hard failures `0`, region decision `retake_required: 3/8`.
    - head/hair mask: rejected; artifact gate `retake_required: 5/8`.
- [x] Build cleaner side-view walk motion controls.
  - Reduce arm/hand ambiguity.
  - Increase readable lower-body phase separation.
  - Keep control frames clean enough to avoid guide burn-in.
  - Add pre-generation diagnostics for ankle separation, stance/swing foot clarity, and sampled phase readability.
  - Result: `outputs/20260613_214207/motion_source_video_pdca/motion_sources/sideview_walk_adv_identity_lock_v2/`
  - Diagnostics: sampled ankle separation passed; unclear ankle separation count `0`.
- [x] Run 8-frame IPAdapter + side-view pose probes before any 120-frame spend.
  - Start from the current promising settings:
    - denoise `0.78`
    - ControlNet strength `0.92`
    - ControlNet end `0.68`
    - IPAdapter preset `PLUS (high strength)`
    - IPAdapter weight `0.50`
    - IPAdapter weight type `prompt is more important`
    - IPAdapter end `0.62`
- [x] Gate every short probe.
  - `repair_frame_artifacts.py --mask-only --weapon none`
  - `select_best_span.py --action walk --motion-metric foreground`
  - `analyze_sprite_regions.py`
  - Agent visual review of `comparison_sheet.png`, `contact_sheet.png`, and `preview.gif`.
- [x] Decide promotion status only after short proof gates and Agent visual review.
  - No visible guide/control burn-in.
  - No duplicate or vanishing lower limbs.
  - Feet/contact read as walking.
  - Identity, outfit, and sprite-style background remain stable.
  - Artifact hard failures `0`.
  - Decision: no 120-frame promotion. The best proof has no deterministic hard failures, but visual/region review still shows lower-body and foot/contact issues.
- [x] If the side-view pose route still fails after cleaner controls, compare mechanism changes instead of more scalar tuning.
  - Try `IPAdapterAdvanced` scheduling/weight types.
  - Try InstantID/PuLID/reference-only equivalent only after pose controls are clean.
  - Consider Wan/BiRefNet output only as a non-rendered motion guide, not as final pixels.
  - Result: IPAdapterAdvanced scheduling and attention masks were tested first. InstantID/PuLID remain second-line because the current blocker is full-body lower-limb mechanics, not face ID.

## Next Candidate Tasks

- [x] Record that the best current mechanism is `identity lock + action-specific side-view template + upper-body identity mask + strict gate`.
- [x] Record that the next route change should target lower-body/feet mechanics, not another scalar sweep.

## Active PDCA: Lower-Body And Foot Contact Control

- [x] Add explicit foot/contact metadata to synthetic side-view walk templates.
  - Record `ground_y`, `stance_foot`, `swing_foot`, per-foot `ankle`, `toe`, `heel`, `contact`, and readable `foot_box`.
  - Store metadata in each `frame_###.json` so generation, gate, and later workflow scripts can share the same source of truth.
- [x] Strengthen pre-generation diagnostics for foot/contact readability.
  - Check sampled foot separation, toe/heel separation, stance/swing balance, contact counts, foot sliding on stance frames, and ground-line consistency.
  - Fail early at the template stage when a sampled short probe cannot possibly show readable walking.
- [x] Generate lower-body/control sidecar frames from the same template metadata.
  - Write sidecar images under the timestamped motion-source run, not top-level outputs.
  - Keep the sidecar separate from visible OpenPose output so it can be used as a future ControlNet/mask input without being accidentally promoted as final artwork.
- [x] Add unit tests for the metadata, diagnostics, and sidecar image output.
- [x] Build one fresh 120-frame clean side-view template and inspect its contact sheet before any image-generation spend.
  - Best current contact-control source:
    - `outputs/20260613_222505/motion_source_video_pdca/motion_sources/sideview_walk_foot_contact_v3/`
  - Diagnostics:
    - `sampled_min_ankle_x_separation: 0.204`
    - `sampled_min_foot_box_x_gap: 0.11352`
    - `unclear_ankle_separation_count: 0`
    - `unclear_foot_box_count: 0`
    - `max_stance_slide_delta: 0.00345`
    - `passes_min_ankle_x_separation: true`
    - `passes_foot_box_separation: true`
- [x] Update the reference-lock report and Skill with the new lower-body/contact control rule.

## Status Vocabulary

- [x] `adopted_animation_candidate`: 120-frame source passes deterministic gates and Agent visual review.
- [x] `selected_proof_only`: useful short proof exists but full adoption blockers remain.
- [x] `promising_probe`: direction is better but gates still reject.
- [x] `rejected_diagnostic`: route/settings fail structurally or semantically.
