# Image2Image Refinement PDCA Findings

Date: 2026-06-11

## Purpose

After Wan-based action generation produces usable motion, use local SDXL Image2Image to improve visual quality without re-solving motion.

The tested refinement stack is:

```text
WanAnimateToVideo curated frames
-> optional near-background cleanup
-> novaOrangeXL SDXL Image2Image at 1024x1024
-> preview/contact/comparison review
```

## Script

```text
scripts/refine_wan_frames_img2img.py
```

The script writes:

- `source_frames/*.png`
- `frames/*.png`
- `preview.gif`
- `source_contact_sheet.png`
- `contact_sheet.png`
- `comparison_sheet.png`
- `workflow/*.json`
- `img2img_refine_report.json`

## Run Refinement PDCA

Source:

```text
outputs_wan_action_repro/walk_i2v_20260611_004335/curated_frames
```

### Pass 1: Conservative Denoise

```bash
uv run python scripts/refine_wan_frames_img2img.py \
  --frames-dir outputs_wan_action_repro/walk_i2v_20260611_004335/curated_frames \
  --output-root outputs_wan_img2img_refine \
  --run-label run_d025 \
  --width 1024 \
  --height 1024 \
  --steps 18 \
  --cfg 5.5 \
  --denoise 0.25 \
  --seed 808080 \
  --timeout-seconds 900
```

Result:

```text
outputs_wan_img2img_refine/run_d025_20260611_005732/
```

Findings:

- Motion was preserved.
- Face and outline improved only slightly.
- Ghost trails and pale duplicate limbs mostly remained.

### Pass 2: Moderate Denoise

```bash
uv run python scripts/refine_wan_frames_img2img.py \
  --frames-dir outputs_wan_action_repro/walk_i2v_20260611_004335/curated_frames \
  --output-root outputs_wan_img2img_refine \
  --run-label run_d038 \
  --width 1024 \
  --height 1024 \
  --steps 20 \
  --cfg 5.5 \
  --denoise 0.38 \
  --seed 808080 \
  --timeout-seconds 900
```

Result:

```text
outputs_wan_img2img_refine/run_d038_20260611_005850/
```

Findings:

- Face, outfit, and line quality improved more than `0.25`.
- Residual ghost trails still remained.
- Structural errors were not repaired.

### Pass 3: Background Cleanup Before Img2Img

```bash
uv run python scripts/refine_wan_frames_img2img.py \
  --frames-dir outputs_wan_action_repro/walk_i2v_20260611_004335/curated_frames \
  --output-root outputs_wan_img2img_refine \
  --run-label run_cleanup72_d035 \
  --width 1024 \
  --height 1024 \
  --steps 20 \
  --cfg 5.5 \
  --denoise 0.35 \
  --seed 808080 \
  --background-cleanup-threshold 72 \
  --background-cleanup-min-channel 150 \
  --timeout-seconds 900
```

Best balanced run-refine proof:

```text
outputs_wan_img2img_refine/run_cleanup72_d035_20260611_010329/
```

Observed output:

- frame count: 8
- mean frame delta: `14.507`
- mean source delta: `2.319`

Findings:

- Near-background cleanup removed much of the pale ghosting before SDXL saw the frame.
- Motion was still preserved.
- This is the best conservative refinement pass.

### Pass 4: Stronger Denoise Boundary

```bash
uv run python scripts/refine_wan_frames_img2img.py \
  --frames-dir outputs_wan_action_repro/walk_i2v_20260611_004335/curated_frames \
  --output-root outputs_wan_img2img_refine \
  --run-label run_cleanup72_d050 \
  --width 1024 \
  --height 1024 \
  --steps 22 \
  --cfg 5.5 \
  --denoise 0.50 \
  --seed 808080 \
  --background-cleanup-threshold 72 \
  --background-cleanup-min-channel 150 \
  --timeout-seconds 900
```

Result:

```text
outputs_wan_img2img_refine/run_cleanup72_d050_20260611_010733/
```

Findings:

- Visually cleaner than lower denoise.
- Identity and outfit details shift more.
- Some ghosting remains in already-broken frames.
- Treat `0.50` as a high-strength refinement boundary, not the default.

## Sword Refinement PDCA

Source:

```text
outputs_wan_action_repro/walk_i2v_20260611_004806/curated_frames
```

Command:

```bash
uv run python scripts/refine_wan_frames_img2img.py \
  --frames-dir outputs_wan_action_repro/walk_i2v_20260611_004806/curated_frames \
  --output-root outputs_wan_img2img_refine \
  --run-label sword_cleanup60_d030 \
  --width 1024 \
  --height 1024 \
  --steps 20 \
  --cfg 5.8 \
  --denoise 0.30 \
  --seed 909090 \
  --background-cleanup-threshold 60 \
  --background-cleanup-min-channel 150 \
  --positive "masterpiece, best quality, polished anime game sprite, full body young woman character holding a glowing blue sword, sword slash attack frame, sword connected to both hands, clean crisp line art, clean cel shading, stable face, stable outfit, sharp hands, sharp sword blade, bright plain white background, readable 2d game attack animation frame" \
  --negative "low quality, blurry, motion blur, ghost trail, afterimage, smeared limb, transparent limb, extra limbs, missing limbs, extra character, duplicate body, broken hands, broken feet, dark background, black background, strong cast shadow, background scenery, text, watermark, identity drift, face melting, changing outfit, broken sword, missing sword, detached sword, floating sword" \
  --timeout-seconds 900
```

Best sword-refine proof:

```text
outputs_wan_img2img_refine/sword_cleanup60_d030_20260611_010519/
```

Observed output:

- frame count: 8
- mean frame delta: `8.239`
- mean source delta: `1.487`

Findings:

- Low denoise preserved the sword.
- It lightly improved line and color stability.
- It did not repair body/weapon structural issues.
- Sword refinement should stay around `0.25-0.35` until a weapon-aware mask/control layer exists.

## Overall Verdict

Image2Image is useful as a finishing pass, but not as a motion or structure repair pass.

It helps with:

- cleaner background
- slightly sharper line work
- more stable face/outfit rendering
- 1024x1024 final-frame polish

It does not reliably fix:

- wrong pose phase
- duplicate limbs baked into the source
- detached weapons
- large ghost silhouettes
- late-frame identity collapse

## Recommended Workflow

```text
1. Generate motion with WanAnimateToVideo + pose_video.
2. Trim/select usable span.
3. Apply near-background cleanup.
4. Run SDXL/novaOrangeXL img2img at 1024x1024.
5. Review comparison_sheet, not only refined contact_sheet.
```

Recommended starting settings:

- Walk/run: `denoise 0.35`, cleanup threshold `72`
- Stronger run cleanup: `denoise 0.50`, only when identity drift is acceptable
- Sword/weapon: `denoise 0.30`, cleanup threshold `60`
- Keep `seed_step 0` during refinement unless there is a reason to deliberately vary details.

## Next Improvements

1. Add foreground/person masks so img2img can clean background without touching the character.
2. Add inpaint-only cleanup for ghost trails around limbs.
3. Add weapon masks for sword/axe/bow before higher-denoise refinement.
4. Add local metrics for ghost area, background cleanliness, and identity drift.
5. Add a batch PDCA wrapper that runs multiple denoise values and writes an adoption summary.
