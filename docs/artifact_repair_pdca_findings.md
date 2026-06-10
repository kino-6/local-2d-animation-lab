# Artifact Repair PDCA Findings

Date: 2026-06-11

## Purpose

Address artifacts that low-denoise Image2Image cannot reliably fix:

- duplicate legs
- strong afterimages or duplicate silhouettes
- broken weapon structure

The key finding is that these are not one class of problem. Small ghost specks and background streaks can be repaired with an explicit inpaint mask. Strong duplicate limbs, large afterimages, and fragmented weapons must be treated as retake or retrim failures.

## Script

```text
scripts/repair_frame_artifacts.py
```

The script writes:

- `source_frames/*.png`
- `masks/*.png`
- `overlays/*.png`
- `frames/*.png`
- `source_contact_sheet.png`
- `mask_contact_sheet.png`
- `overlay_contact_sheet.png`
- `contact_sheet.png`
- `comparison_sheet.png`
- `preview.gif`
- `artifact_repair_report.json`

## Method

The workflow is:

```text
source frames
-> estimate plain background
-> weak foreground mask for pale ghost traces
-> strong foreground mask for protected character body
-> repair mask = weak artifacts outside protected body + small detached components
-> local quality gate
-> masked ComfyUI inpaint only when the gate allows repair
```

ComfyUI nodes used:

- `CheckpointLoaderSimple`
- `LoadImage`
- `LoadImageMask`
- `VAEEncodeForInpaint`
- `KSampler`
- `VAEDecode`
- `ImageCompositeMasked`
- `SaveImage`

The final composite uses the mask again, so unmasked character pixels stay from the source frame.

## Issue Codes

- `masked_ghost_or_small_artifact`: small visible artifact was masked for repair.
- `strong_duplicate_silhouette_risk`: the frame has too many strong foreground fragments to fix safely.
- `double_foot_or_duplicate_leg_risk`: lower body has more than two foot/leg blobs.
- `weapon_missing`: expected weapon pixels were not found.
- `weapon_fragmented`: weapon-like pixels split into too many components.
- `weapon_not_elongated`: sword/bow shape does not read as an elongated weapon.
- `repair_mask_too_large`: the repair mask is too broad for local inpaint.

Hard issue codes block inpaint and set `gate` to `retake_required`.

## Run Repair Probe

Source:

```text
outputs_wan_img2img_refine/run_cleanup72_d035_20260611_010329/frames
```

Command:

```bash
uv run python scripts/repair_frame_artifacts.py \
  --frames-dir outputs_wan_img2img_refine/run_cleanup72_d035_20260611_010329/frames \
  --output-root outputs_artifact_repair_pdca \
  --run-label run_gate_v2_probe \
  --mask-only \
  --weapon none \
  --width 1024 \
  --height 1024
```

Result:

```text
outputs_artifact_repair_pdca/run_gate_v2_probe_20260611_013433/
```

Observed gate summary:

- `no_repair_needed`: 5 frames
- `repair_candidate`: 1 frame
- `retake_required`: 2 frames
- issue counts:
  - `masked_ghost_or_small_artifact`: 3
  - `strong_duplicate_silhouette_risk`: 1
  - `double_foot_or_duplicate_leg_risk`: 1

Conclusion:

- The run is not adoption-ready as an animation because two frames need retake/retrim.
- Inpaint should only be used for the small remaining repair candidate.
- The large duplicate silhouette cannot be accepted as a repaired frame.

## Run Masked Inpaint

Command:

```bash
uv run python scripts/repair_frame_artifacts.py \
  --frames-dir outputs_wan_img2img_refine/run_cleanup72_d035_20260611_010329/frames \
  --output-root outputs_artifact_repair_pdca \
  --run-label run_inpaint_repair \
  --weapon none \
  --width 1024 \
  --height 1024 \
  --steps 24 \
  --cfg 5.6 \
  --denoise 0.72 \
  --timeout-seconds 900
```

Result:

```text
outputs_artifact_repair_pdca/run_inpaint_repair_20260611_013307/
```

Observed output:

- frame count: 8
- inpainted frames: 2 before the stricter gate update
- source mean frame delta: `14.507`
- repaired mean frame delta: `14.528`
- the repair changed motion very little, which is good for local cleanup

Review result:

- Small specks/streaks are suitable for masked inpaint.
- The duplicate silhouette frame remained unacceptable.
- The gate was tightened after visual review so strong duplicate silhouettes now block inpaint.

## Sword Probe

Source:

```text
outputs_wan_img2img_refine/sword_cleanup60_d030_20260611_010519/frames
```

Command:

```bash
uv run python scripts/repair_frame_artifacts.py \
  --frames-dir outputs_wan_img2img_refine/sword_cleanup60_d030_20260611_010519/frames \
  --output-root outputs_artifact_repair_pdca \
  --run-label sword_mask_probe \
  --mask-only \
  --weapon sword \
  --width 1024 \
  --height 1024
```

Result:

```text
outputs_artifact_repair_pdca/sword_mask_probe_20260611_013224/
```

Observed gate summary:

- `retake_required`: 8 frames
- issue counts:
  - `weapon_fragmented`: 8
  - `weapon_not_elongated`: 3
  - `double_foot_or_duplicate_leg_risk`: 2

Conclusion:

- Weapon structure is a generation-control problem, not an inpaint polish problem.
- Next sword PDCA should add weapon-specific control or mask guidance before video generation.

## Wan Parameter Probe

A `continue_motion_max_frames` CLI option was added to:

```text
scripts/run_wan_walk_i2v.py
```

Test:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode animate_pose \
  --pose-template walk \
  --run-label walk_cmf1_noafterimage \
  --output-root outputs_wan_artifact_pdca \
  --length 17 \
  --steps 6 \
  --cfg 5.2 \
  --continue-motion-max-frames 1 \
  --post-trim-start 9 \
  --positive "anime game sprite, full body young woman character, side view running or brisk walking in place, clean alternating legs, one visible body only, stable character identity, stable camera, clean white background, crisp cel shading, sharp limbs, no motion trails, no afterimages, readable 2d game animation" \
  --negative "multiple characters, duplicate body, double exposure, onion skin, afterimage, ghost trail, transparent duplicate limbs, extra legs, extra arms, smeared limb, motion blur, broken feet, cropped feet, background scenery, changing outfit, face melting, text, watermark"
```

Result:

```text
outputs_wan_artifact_pdca/walk_cmf1_noafterimage_20260611_013616/
```

Artifact gate:

```text
outputs_artifact_repair_pdca/walk_cmf1_gate_probe_20260611_013711/
```

Findings:

- Motion increased, but background contamination and afterimage area got worse.
- Average mask coverage rose to `0.04721`.
- `continue_motion_max_frames=1` is not a reliable improvement for this character/action.

## Current Rule

Use Image2Image and masked inpaint only for local cleanup after the animation is already structurally plausible.

Do not use inpaint to hide:

- duplicate legs
- large duplicate body silhouettes
- fragmented weapons
- missing weapon-body contact

Those failures should go back to:

- retrim/select a better video span
- rerun Wan with better motion settings
- add weapon-specific control
- add action-specific mask/reference guidance

