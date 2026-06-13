# Tasks: Sidecar-Suitable Lower-Body Control Probe

Archived checkpoint:

```text
docs/archive/Tasks_20260613_lower_body_sidecar_control_probe_completed.md
```

Cleanup report:

```text
docs/output_cleanup_20260613_sidecar_probe.md
```

## Rules

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet.
- [x] Save all new generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Target adopted source length is 120 frames; short probes are evidence only.
- [x] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [x] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, shoe recolor, or identity drift are visible.

## Current Interpretation

- [x] `IPAdapterAdvanced style transfer precise + upper_body mask` remains the best reference-lock ControlNet route, but only as `selected_proof_only`.
- [x] Foot-contact metadata and foot-box diagnostics are useful before generation.
- [x] OpenPose-only does not carry toe, heel, or foot-box semantics into generated shoes/contact.
- [x] Secondary OpenPose-family sidecar is not the mainline:
  - artifact hard failures improved from `3/8` to `2/8`;
  - motion improved from `8.918` to `10.505`;
  - region retakes worsened from `2/8` to `3/8`;
  - feet/contact temporal instability worsened from `0.02694` to `0.0582`;
  - visual review found shoe/leg recolor and lower-body ghosting.

## Plan

The next mechanism is a sidecar carrier probe:

```text
main OpenPose = whole-body walk phase
IPAdapterAdvanced upper_body mask = identity/reference lock
sidecar carrier = lower-body outline/contact signal, not another OpenPose-like skeleton
gate = artifact + span + region diagnostics + Agent visual review
```

Do not assume new models work because the filename looks right. First inventory local ComfyUI models, then acquire one narrow candidate, then run a short 8-frame proof.

Primary candidate direction:

- T2I Adapter SDXL lineart/sketch, because it is closer to foot-box outline and lower-leg shape than OpenPose.

Fallback candidates:

- SDXL softedge or canny if lineart/sketch cannot be loaded.
- SDXL union only after local loader/control-type behavior is confirmed.
- If no model can be acquired or loaded, use the sidecar as a mask/evaluation channel and record the blocker.

## Active PDCA

- [x] Cleanup stale local outputs.
  - Archive old `Tasks.md`.
  - Write `docs/output_cleanup_20260613_sidecar_probe.md`.
  - Delete stale local `outputs/20260613_*` sessions after durable findings are recorded.
  - Delete stale `source_probe_packages/` unless it is needed by tracked docs.
- [x] Add model inventory support.
  - Add a small script or reusable command path that reports local ControlNet/T2I Adapter candidates.
  - Record whether lineart, sketch, canny, softedge, depth, segmentation, or union candidates are present.
- [x] Add model acquisition support for one sidecar-suitable candidate.
  - Prefer `t2i-adapter_diffusers_xl_lineart.safetensors` from `lllyasviel/sd_control_collection`.
  - Save under the existing ComfyUI controlnet model directory, preferably `SDXL/`.
  - Do not redownload if the file already exists.
  - Record source URL, target path, file size, and decision in a report.
- [x] Add or verify a lower-body sidecar render style suitable for lineart/sketch.
  - It should be grayscale/outline-oriented, not colored pose bones.
  - It should encode hip/knee/ankle leg line, shoe boxes, toe/heel direction, and contact line.
  - Add unit coverage for the new render mode.
- [x] Generate a fresh 8-frame sidecar-carrier diagnostic.
  - Rebuild the synthetic side-view walk source from code, do not depend on deleted `outputs/`.
  - Use 8 sampled frames: `0,15,30,45,60,75,90,105`.
  - Main ControlNet: `SDXL\OpenPoseXL2.safetensors`.
  - Sidecar candidate: the newly acquired lineart/sketch/softedge/canny model.
  - Use `IPAdapterAdvanced style transfer precise`, `upper_body` mask.
  - Check ComfyUI `/queue` before submitting.
- [x] Gate and visually review the diagnostic.
  - `repair_frame_artifacts.py --mask-only --weapon none`.
  - `select_best_span.py --action walk --motion-metric foreground --allow-hard-failures`.
  - `analyze_sprite_regions.py`.
  - Agent visual review of `comparison_sheet.png`, `contact_sheet.png`, and `sidecar_contact_sheet.png`.
- [x] Decide whether the sidecar-suitable model route is worth deeper PDCA.
  - Continue only if it improves foot/contact readability without guide leakage, recolor, or lower-body ghosting.
  - Reject if it behaves like the OpenPose-family sidecar or causes visible line/control leakage.
- [x] Update durable knowledge.
  - `docs/reference_lock_motion_template_deep_dive.md`.
  - `docs/walk_candidate_comparison.md`.
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`.
  - `Tasks.md` with final result and next mechanism.

## Success Criteria

- [x] Script/test changes pass local tests.
- [x] Generated diagnostic exists under one timestamped `outputs/<timestamp>/...` session.
- [x] No stale pre-plan local outputs remain after durable knowledge was recorded.
- [x] Result is labeled honestly as one of:
  - `selected_proof_only`;
  - `rejected_diagnostic`;
  - `blocked_model_compatibility`.

## Result

- [x] Added model management:
  - `scripts/manage_sidecar_control_models.py`
  - inventory report before download:
    - `outputs/20260613_234244/model_management/sidecar_control_model_inventory/model_inventory_report.json`
  - acquisition report:
    - `outputs/20260613_234258/model_management/t2i_lineart_sdxl_acquisition/model_acquisition_report.json`
  - inventory report after download:
    - `outputs/20260613_234308/model_management/sidecar_control_model_inventory_after_download/model_inventory_report.json`
- [x] Downloaded model:
  - `C:\LocalWork\StabilityMatrix\Data\Packages\ComfyUI\models\controlnet\SDXL\t2i-adapter_diffusers_xl_lineart.safetensors`
  - bytes: `158060416`
  - ComfyUI `ControlNetLoader` listed the model after download.
- [x] Added lower-body sidecar style:
  - `foot_contact_lineart`
  - output source:
    - `outputs/20260613_234318/motion_source_video_pdca/motion_sources/sideview_walk_lineart_sidecar_v1/`
  - diagnostics passed:
    - `sampled_min_ankle_x_separation: 0.1205`
    - `sampled_min_foot_box_x_gap: 0.03002`
    - `unclear_ankle_separation_count: 0`
    - `unclear_foot_box_count: 0`
- [x] Probe A: original `Anima_00013_.png` reference + lineart sidecar strength `0.35`.
  - output: `outputs/20260613_234423/reference_pose_regen/walk_ipadv_upper_mask_lineart_sidecar035_8f/`
  - gates: `outputs/20260613_234634/`
  - artifact: `retake_required: 8/8`
  - span hard failures: `8/8`
  - region retake decisions: `7/8`
  - visual decision: `rejected_diagnostic`
  - reason: guide/line leakage, duplicate-silhouette risk, tiny character fragments, and no usable walk asset.
- [x] Probe B: `ComfyUI2025_131891_trim.png` reference + lineart sidecar strength `0.15`.
  - output: `outputs/20260613_234732/reference_pose_regen/comfy2025_walk_ipadv_upper_mask_lineart_sidecar015_8f/`
  - gates: `outputs/20260613_234839/`
  - artifact: `retake_required: 8/8`
  - span hard failures: `8/8`
  - region retake decisions: `8/8`
  - mean lower-body temporal delta: `0.06158`
  - mean feet/contact temporal delta: `0.01064`
  - visual decision: `rejected_diagnostic`
  - reason: fewer explicit line leaks than Probe A, but not a readable 2D walk asset; composition/action collapses around the reference instead of becoming a sprite walk.
- [x] Decision:
  - `rejected_diagnostic`
- [x] Interpretation:
  - The lineart model is installable and loadable.
  - A lineart sidecar is not automatically a better foot/contact carrier in this reference-locked img2img workflow.
  - The current failure is no longer only "OpenPose cannot carry foot boxes"; it is also "the reference image and identity lock can dominate the action composition".
  - The next mainline should generate or select a walk-ready full-body side-view start/reference first, then use sidecar controls only after the reference already has sprite-compatible framing.
