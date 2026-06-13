# Reference-Conditioned Regeneration PDCA

Date: 2026-06-13

## Purpose

Move away from small Wan parameter tuning and test whether final 2D game frames can be regenerated from a stable character reference plus reusable motion controls.

The tested mechanism is:

```text
full-body character start image
+ reusable walk OpenPose control frames
+ novaOrangeXL SDXL img2img
+ SDXL OpenPose ControlNet
-> per-frame regenerated sprite sequence
```

This treats Wan/video output as a motion-draft family, not as the final asset source.

## Local Environment Finding

ComfyUI exposes local SDXL OpenPose ControlNet models:

- `SDXL\OpenPoseXL2.safetensors`
- `SDXL\t2i-adapter-openpose-sdxl-1.0.safetensors`

Initial local node inspection did not show an IPAdapter-style identity reference node. There are `ReferenceLatent` and several API-style reference nodes, but no confirmed built-in local identity-lock path equivalent to IPAdapter/InstantID/PuLID.

2026-06-13 identity-lock setup:

- Installed `comfyorg/comfyui-ipadapter` into the local ComfyUI custom nodes folder.
- Downloaded `sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors` under the configured `ipadapter` model path.
- Added the expected CLIP-Vision filename `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` as a hardlink to the existing `clip_vision_h.safetensors`.
- Confirmed ComfyUI exposes `IPAdapterUnifiedLoader` and `IPAdapter`.

InstantID and PuLID remain second-line candidates. They are more face-ID oriented and require heavier face/InsightFace dependencies; the first practical full-body sprite identity-lock test uses IPAdapter Plus SDXL.

## Script

Added:

```text
scripts/regenerate_pose_sequence_controlnet.py
```

Updated:

- Optional IPAdapter identity/reference lock through `IPAdapterUnifiedLoader` + `IPAdapter`.
- `--ipadapter-preset`, `--ipadapter-weight`, `--ipadapter-weight-type`, `--ipadapter-start`, and `--ipadapter-end`.
- `--ipadapter-mode advanced` for `IPAdapterAdvanced`.
- `--ipadapter-combine-embeds`, `--ipadapter-embeds-scaling`, and `--ipadapter-attn-mask`.
- The script still writes every generated run under `outputs/<timestamp>/reference_pose_regen/<label>/`.

The script writes each run under `outputs/<timestamp>/reference_pose_regen/<label>/` with:

- `run_profile.json`
- `memo.md`
- `workflow/frame_###.json`
- `source_reference/source_image.png`
- `control_pose/*.png`
- `frames/*.png`
- `preview.gif`
- `contact_sheet.png`
- `comparison_sheet.png`
- `reference_pose_regen_report.json`

## Probe A: Conservative Source-Lock

Output:

```text
outputs/20260613_204839/reference_pose_regen/walk_ref_pose_regen_openpose_d055_8f/
```

Settings:

- source image: `outputs/20260613_185524/background_normalize/prior_best_start_background_normalize/frames/frame_000.png`
- pose indices: `0,15,30,45,60,75,90,105`
- checkpoint: `novaOrangeXL_v120.safetensors`
- controlnet: `SDXL\OpenPoseXL2.safetensors`
- denoise: `0.55`
- controlnet strength: `0.78`

Result:

- identity/color/background stability is much better than raw Wan drift;
- motion is almost static;
- frame delta: `0.389`;
- not a readable walk.

Decision: rejected as too source-locked.

## Probe B: Stronger Pose Pressure

Output:

```text
outputs/20260613_205340/reference_pose_regen/walk_ref_pose_regen_openpose_d072_s110_8f/
```

Settings:

- denoise: `0.72`
- controlnet strength: `1.10`
- other settings unchanged from Probe A.

Result:

- motion delta increased to `2.928`;
- character remains visually clean and bright;
- pose pressure mostly redraws upper body/arms rather than producing a convincing walk;
- one frame shows visible yellow guide burn-in;
- artifact gate rejected `2/8` frames for duplicate-silhouette risk.

Decision: rejected as a standalone final-frame mechanism.

## Probe C: IPAdapter Plus + Existing Walk OpenPose

Output:

```text
outputs/20260613_211402/reference_pose_regen/walk_ipadapter_openpose_d072_c110_ip065_8f/
```

Settings:

- IPAdapter preset: `PLUS (high strength)`
- IPAdapter weight: `0.65`
- IPAdapter weight type: `style transfer`
- denoise: `0.72`
- controlnet strength: `1.10`
- controlnet end: `0.82`

Result:

- identity, hair color, and outfit stability improved clearly;
- motion delta increased to `3.717`;
- visible pose-guide burn-in appeared in later frames;
- artifact gate rejected the candidate: `retake_required: 2/8`;
- existing walk OpenPose templates are too front-facing/ambiguous for side-view game-sprite walking.

Decision: rejected as an adoption candidate, but IPAdapter identity lock itself is confirmed to work.

## Probe D: IPAdapter Plus + Lower ControlNet

Output:

```text
outputs/20260613_212054/reference_pose_regen/walk_ipadapter_lower_cnet_probe_4f/
```

Settings:

- denoise: `0.68`
- controlnet strength: `0.78`
- controlnet end: `0.72`
- IPAdapter weight: `0.62`
- IPAdapter weight type: `prompt is more important`
- IPAdapter end: `0.70`

Result:

- guide burn-in reduced;
- identity stayed stable;
- motion delta dropped to `1.612`;
- walk mechanics became too static.

Decision: rejected as too source/reference locked.

## Probe E: IPAdapter Plus + Mid Control + Side-View Pose Source

Side-view control source:

```text
outputs/20260613_212800/motion_source_video_pdca/motion_sources/sideview_walk_ipadapter_probe/
```

Best short proof:

```text
outputs/20260613_212815/reference_pose_regen/walk_ipadapter_sideview_pose_mid_8f/
```

Settings:

- synthetic side-view walk control frames, 120-frame source sampled at `0,15,30,45,60,75,90,105`
- denoise: `0.78`
- controlnet strength: `0.92`
- controlnet end: `0.68`
- IPAdapter preset: `PLUS (high strength)`
- IPAdapter weight: `0.50`
- IPAdapter weight type: `prompt is more important`
- IPAdapter end: `0.62`

Result:

- motion delta increased to `4.642`;
- visual review: best result in this branch; it reads as side-view walking more than previous OpenPose-only and IPAdapter/front-pose probes;
- identity and outfit remain reasonably stable for a short proof;
- no obvious visible guide-line burn-in in the contact sheet;
- artifact gate still rejects: `retake_required: 5/8`, mostly duplicate-silhouette risk;
- region diagnostics still flag `foot_shadow_or_contact_artifact_review: 8/8`, `lower_body_pale_afterimage_review: 3/8`, and one `silhouette_redraw_jitter_review`.

Decision: `promising_probe`, not adoption OK. This proves the useful mechanism is not "OpenPose tuning" alone; it is `reference identity lock + action-specific side-view motion template + strict visual/gate review`.

## Probe F: IPAdapterAdvanced + Clean Side-View Template

Cleaner side-view control source:

```text
outputs/20260613_214207/motion_source_video_pdca/motion_sources/sideview_walk_adv_identity_lock_v2/
```

Template diagnostics passed:

- unclear ankle separation count: `0`;
- sampled minimum ankle separation: `0.082`;
- sampled indices: `0,15,30,45,60,75,90,105`.

Advanced probe matrix:

```text
outputs/20260613_214241/reference_pose_regen/walk_ipadv_comp_precise_sideview_v2_8f/
outputs/20260613_214341/reference_pose_regen/walk_ipadv_style_precise_sideview_v2_8f/
outputs/20260613_214434/reference_pose_regen/walk_ipadv_linear_short_sideview_v2_8f/
```

Result:

- `style transfer precise` was the best unmasked route;
- unmasked advanced probes still produced duplicate-silhouette or lower-body artifact failures;
- scalar/schedule changes alone were not enough.

Decision: continue into attention-mask probes rather than spend on 120 frames.

## Probe G: IPAdapterAdvanced Attention Masks

Best proof:

```text
outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/
```

Settings:

- IPAdapter mode: `advanced`
- weight type: `style transfer precise`
- weight: `0.55`
- end: `0.62`
- embeds scaling: `K+mean(V) w/ C penalty`
- attention mask: `upper_body`

Gate result:

- artifact gate: `no_repair_needed: 8/8`;
- span selection: hard failures `0`, score `0.93491`;
- region diagnostics: `foot_shadow_or_contact_artifact_review: 8/8`, `silhouette_redraw_jitter_review: 2/8`, `lower_body_pale_afterimage_review: 1/8`, region decision `retake_required: 2/8`.

Comparison probes:

- whole-character mask: `outputs/20260613_220050/reference_pose_regen/walk_ipadv_style_precise_whole_mask_sideview_v2_8f/`; stable but stiffer, region `retake_required: 3/8`.
- head/hair mask: `outputs/20260613_220147/reference_pose_regen/walk_ipadv_style_precise_head_mask_sideview_v2_8f/`; rejected, artifact `retake_required: 5/8`.

Decision: `selected_proof_only`. The upper-body mask confirms that region-limited identity lock is useful. It reduces hard failures compared with unmasked advanced probes, but it still does not meet the visual bar for an adopted 2D game walk asset.

## Interpretation

This mechanism proves one useful thing: starting every frame from the same reference image can stabilize identity/color far better than accepting Wan video frames directly.

But OpenPose-only SDXL img2img is not enough to create the final walk sequence:

- low denoise preserves identity but ignores pose;
- high denoise starts to follow control, but still does not produce leg motion reliably;
- stronger control can burn guide pixels into the output;
- frame-to-frame generation has no temporal consistency model.

IPAdapter changes the tradeoff:

- it confirms local identity/reference lock is now available;
- it improves character design consistency under larger denoise/control pressure;
- it does not solve bad or front-facing motion controls;
- if control is too strong, guide burn-in returns;
- if control is too weak, the character becomes stable but too static.

The best current identity-lock result required a side-view motion template. For 2D game assets, the action template must encode the desired camera/view and motion phase, not merely "a human walking".

The latest mask result narrows the next blocker: identity lock is no longer the main unknown. Lower-body/foot mechanics and local redraw stability now decide whether the output can become an actual game asset.

## Next Mechanism

Do not continue plain OpenPose-only per-frame regeneration by tuning denoise/strength alone.

Next useful mechanisms are:

1. Keep IPAdapter Plus SDXL as the first local identity-lock route for full-body sprite probes.
2. Use Wan/BiRefNet output only to extract non-rendered motion guides: silhouette, foot contact, bbox, or pose phase. Do not feed visible guide pixels as final image content.
3. Test a two-level strategy:
   - generate only a small set of key pose stills with strong reference lock;
   - interpolate or video-generate between already-stable keyframes.
4. Before spending on 120 frames, build or select action-specific side-view motion controls and pass an 8-17 frame proof with no guide burn-in and no duplicate lower limbs.
