# Wan I2V Walk Findings

Date: 2026-06-11

## Main Finding

The best current local video path for walk animation is:

```text
reference character image
+ reusable walk pose template rendered as pose video
+ WanAnimateToVideo
+ TrimVideoLatent
+ post-trim quality selection
```

This worked better than still-frame ControlNet generation because the video model supplies temporal continuity. It worked better than plain image-to-video because the pose video supplies an explicit walk-phase guide.

Best current proof:

```text
outputs_wan_walk_i2v/walk_i2v_20260610_215019/
```

Important files:

- `preview.gif`
- `contact_sheet.png`
- `workflow/wan_walk_i2v_api.json`
- `wan_walk_i2v_report.json`
- `curated_frames/*.png`

## Reproduction Command

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode animate_pose \
  --width 512 \
  --height 512 \
  --length 17 \
  --steps 12 \
  --cfg 3.0 \
  --seed 424242 \
  --post-trim-start 9 \
  --timeout-seconds 1800
```

Observed output:

- generated frames before post-trim: 17
- curated frames after post-trim: 8
- mean frame delta: `13.534`
- max frame delta: `17.961`
- min frame delta: `8.961`

## Why This Worked

### Video Prior

Wan I2V has a temporal prior. It tends to maintain one moving subject across adjacent frames better than generating independent still frames. That matters for walk cycles because the user judges continuity, not just per-frame beauty.

### Pose Video Control

Natural language alone is too weak for walk mechanics. Phrases such as `walking in place` and `legs alternating clearly` helped a little, but did not reliably produce walk phases.

The reusable `pose_templates/walk` frames gave the model an explicit motion scaffold. This is aligned with the project direction: common keypoints should be reusable across character designs, while the input image supplies identity.

### WanAnimateToVideo Separation

`WanAnimateToVideo` has separate inputs for:

- `reference_image`
- `pose_video`
- optional `background_video`
- optional `character_mask`

That separation matters. It lets the character image remain the identity source while the pose video acts as motion guidance.

By contrast, `WanFunControlToVideo` with `control_video` generated the pose-stick figure itself. In the tested setup, it treated the control video as visual content rather than only motion guidance.

### TrimVideoLatent

`WanAnimateToVideo` returns `trim_latent` / `trim_image` metadata. Without trimming, reference or transition frames can leak into the decoded output. Connecting:

```text
KSampler -> TrimVideoLatent(trim_amount = WanAnimateToVideo.trim_latent) -> VAEDecodeTiled
```

made the frame count and content more usable.

### Post-Trim Quality Selection

The generated sequence had a better stable region after the early transition frames. `--post-trim-start 9` selected the usable walking segment. This is not a final production answer, but it is a practical quality-gate step: keep only the frames that are visually coherent enough to inspect as an asset candidate.

## What Failed

### Plain I2V

`WanImageToVideo` from one start image produced stable identity but weak walk motion. With higher motion seeds it produced stronger movement, but also face drift, limb smearing, and ghost trails.

### First/Last Frame

`WanFirstLastFrameToVideo` pulled too hard toward the end pose. The tested run caused exposure/background drift and did not produce a clean game-asset sequence.

### WanFunControlToVideo

`WanFunControlToVideo` with OpenPose-style control frames generated the control skeleton itself. This was a bad path for this checkpoint/node combination.

### White Background Video

Adding a white `background_video` to `WanAnimateToVideo` reduced dark background drift, but overconstrained the generation and caused the character to fade out. Do not use it as the default.

### Portrait Canvas

`480x832` looked conceptually attractive for full-body characters, but the tested Wan 480p workflow drifted in exposure/background and did not improve motion quality. Current default should stay `512x512` until a better portrait workflow is proven.

## Current Quality Gate

The current best result is improved, but not adopted as final game-ready output.

Accept as an experimental proof when:

- character remains a single readable subject
- legs show clear alternating walk phases
- arms move in the opposite rhythm
- output is visually coherent after post-trim

Reject or retake when:

- early transition frames dominate
- black background or exposure drift hides the character
- pose sticks become the rendered subject
- face identity changes strongly
- arms, legs, or hands become ghost trails
- foot contact is unclear

## Next Improvements

1. Add a `character_mask` input for `WanAnimateToVideo` so the model has a clearer subject region.
2. Build a pose-video renderer tuned for Wan, not just ControlNet: less neon stick contrast, less black background pull, and clearer side-view limb separation.
3. Add automated contact-sheet scoring for dark-frame ratio, subject visibility, pose-video leakage, and usable-frame span.
4. Try longer source generation and automatically select the best contiguous walk segment.
5. Re-test with a model/checkpoint specialized for Wan animate or character animation if available locally.

## Reproducibility Check: Run And Sword

Date: 2026-06-11

The walk finding partly generalizes, but not uniformly. `WanAnimateToVideo + pose_video + TrimVideoLatent + post-trim` is a useful base workflow for other actions, but each action still needs an action-specific pose template and action-specific reference/control assets.

### Run From Walk Pose

There is no dedicated `run` pose template yet. The first test reused `pose_templates/walk` with a running prompt:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode animate_pose \
  --output-root outputs_wan_action_repro \
  --pose-template walk \
  --width 512 \
  --height 512 \
  --length 17 \
  --steps 12 \
  --cfg 3.0 \
  --seed 515151 \
  --post-trim-start 9 \
  --positive "anime game sprite, full body young woman character, side view running in place, energetic run cycle, long stride, legs alternating clearly, arms pumping opposite to legs, stable character identity, stable camera, clean plain background, single character, crisp cel shading, readable 2d game animation" \
  --timeout-seconds 1800
```

Result:

```text
outputs_wan_action_repro/walk_i2v_20260611_003915/
```

The motion read as running, but the background became too dark and ghosted.

The PDCA retake strengthened bright-background guidance and added negative terms against dark silhouettes:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode animate_pose \
  --output-root outputs_wan_action_repro \
  --pose-template walk \
  --width 512 \
  --height 512 \
  --length 17 \
  --steps 12 \
  --cfg 3.0 \
  --seed 424242 \
  --post-trim-start 9 \
  --positive "anime game sprite, full body young woman character, side view running in place, energetic run cycle, long stride, legs alternating clearly, arms pumping opposite to legs, stable character identity, stable camera, bright white background, evenly lit, single character, crisp cel shading, readable 2d game animation" \
  --negative "multiple characters, duplicate body, extra limbs, missing limbs, broken legs, broken feet, weapon, sword, bow, text, watermark, heavy camera motion, zoom, blur, cropped feet, motion blur, ghost trail, afterimage, smeared limb, transparent limb, dark background, black background, silhouette, strong cast shadow, background scenery, changing outfit, face melting" \
  --timeout-seconds 1800
```

Best current run proof:

```text
outputs_wan_action_repro/walk_i2v_20260611_004335/
```

Observed output:

- curated frames: 8
- mean frame delta: `16.624`
- max frame delta: `20.437`
- min frame delta: `7.198`

Interpretation:

- The walk finding transfers to run at the workflow level.
- Reusing `walk` pose video can produce a run-like result when the prompt is strong.
- Quality is still below adoption level because run has stronger limb acceleration and more residual ghosting.
- A dedicated `run` pose template should be added instead of relying on prompt pressure over a walk template.

### Sword Attack

Sword required an image that already contained a sword. Starting from the original non-weapon reference is not enough for stable weapon continuity. The test used:

```text
outputs_controlnet_pdca/anima_00013/attack/attack_sword_identity_lock/frames/anima_00013_attack_r03_043.png
```

Baseline command:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode animate_pose \
  --output-root outputs_wan_action_repro \
  --start-image outputs_controlnet_pdca/anima_00013/attack/attack_sword_identity_lock/frames/anima_00013_attack_r03_043.png \
  --pose-template attack_sword \
  --width 512 \
  --height 512 \
  --length 17 \
  --steps 12 \
  --cfg 3.2 \
  --seed 616161 \
  --positive "anime game sprite, full body young woman character holding a glowing blue sword, side view quick sword slash attack, clear windup active slash and recovery, sword stays in both hands, slash arc motion, stable character identity, stable camera, clean plain background, single character, crisp cel shading, readable 2d game attack animation" \
  --negative "multiple characters, duplicate body, extra limbs, missing limbs, broken legs, broken feet, text, watermark, heavy camera motion, zoom, blur, cropped feet, motion blur, ghost trail, afterimage, smeared limb, transparent limb, background scenery, changing outfit, face melting, broken sword, missing sword" \
  --timeout-seconds 1800
```

Result:

```text
outputs_wan_action_repro/walk_i2v_20260611_004054/
```

The sword remained visible and shifted through the slash, but the body was too static.

The PDCA retake strengthened torso rotation, forward step, hand grip, and detached-sword negatives:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode animate_pose \
  --output-root outputs_wan_action_repro \
  --start-image outputs_controlnet_pdca/anima_00013/attack/attack_sword_identity_lock/frames/anima_00013_attack_r03_043.png \
  --pose-template attack_sword \
  --width 512 \
  --height 512 \
  --length 17 \
  --steps 14 \
  --cfg 3.4 \
  --seed 616161 \
  --positive "anime game sprite, full body young woman character holding a glowing blue sword, side view quick sword slash attack, clear windup active slash and recovery, torso twists, shoulders rotate, forward step, both hands grip the sword, sword stays connected to hands, wide slash arc motion, stable character identity, stable camera, clean plain background, single character, crisp cel shading, readable 2d game attack animation" \
  --negative "multiple characters, duplicate body, extra limbs, missing limbs, broken legs, broken feet, text, watermark, heavy camera motion, zoom, blur, cropped feet, motion blur, ghost trail, afterimage, smeared limb, transparent limb, background scenery, changing outfit, face melting, broken sword, missing sword, detached sword, floating sword" \
  --timeout-seconds 1800
```

Result:

```text
outputs_wan_action_repro/walk_i2v_20260611_004507/
```

The retake produced a more readable slash, but later frames drifted in face and body quality. The current best sword artifact is the curated first 8 frames:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode animate_pose \
  --output-root outputs_wan_action_repro \
  --start-image outputs_controlnet_pdca/anima_00013/attack/attack_sword_identity_lock/frames/anima_00013_attack_r03_043.png \
  --pose-template attack_sword \
  --width 512 \
  --height 512 \
  --length 17 \
  --steps 14 \
  --cfg 3.4 \
  --seed 616161 \
  --post-trim-end 8 \
  --positive "anime game sprite, full body young woman character holding a glowing blue sword, side view quick sword slash attack, clear windup active slash and recovery, torso twists, shoulders rotate, forward step, both hands grip the sword, sword stays connected to hands, wide slash arc motion, stable character identity, stable camera, clean plain background, single character, crisp cel shading, readable 2d game attack animation" \
  --negative "multiple characters, duplicate body, extra limbs, missing limbs, broken legs, broken feet, text, watermark, heavy camera motion, zoom, blur, cropped feet, motion blur, ghost trail, afterimage, smeared limb, transparent limb, background scenery, changing outfit, face melting, broken sword, missing sword, detached sword, floating sword" \
  --timeout-seconds 1800
```

Best current sword proof:

```text
outputs_wan_action_repro/walk_i2v_20260611_004806/
```

Observed output:

- curated frames: 8
- mean frame delta: `9.151`
- max frame delta: `15.537`
- min frame delta: `3.162`

Interpretation:

- The workflow transfers to sword slash only when the reference image already contains the sword.
- The pose template alone controls body phase, not weapon geometry.
- Prompt changes can increase sword motion, but cannot fully solve weapon attachment and later-frame identity drift.
- Sword needs an explicit weapon-control layer, weapon mask, or separate sword/reference asset, not just body OpenPose.

## Generalization Verdict

`WanAnimateToVideo + pose_video + TrimVideoLatent + post-trim` is reproducible as a motion workflow:

- walk: useful, best current proof
- run: useful but needs a dedicated run pose template and better anti-ghosting
- sword: useful only with weapon-bearing reference; needs weapon-specific control

The reusable lesson is not "one prompt works for every action." The reusable lesson is:

```text
reference image controls identity
pose video controls gross motion phase
action-specific visual controls are still needed for fast limbs, weapons, effects, and contact events
post-trim selects the stable span
```

Next workflow improvements:

1. Add `pose_templates/run` rather than forcing `run` through `walk`.
2. Add action-specific `weapon_video` or weapon mask support for sword/axe/bow.
3. Add automatic selection of the best contiguous span instead of manually choosing `post-trim-start` / `post-trim-end`.
4. Add local quality checks for dark-frame ratio, ghost trails, detached weapons, and face drift.
5. Rename old experimental output directories or use `--run-label` for future runs so outputs are not all named `walk_i2v_*`.
