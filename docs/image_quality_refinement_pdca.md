# Image Quality Refinement PDCA

This note records still-image quality refinement after action/keyframe generation. It is separate from motion control quality.

## Probe: 1024 Img2Img Regeneration

Source frames:

- `outputs_general_action_quality/action_keyframes_refcond_lower_body/ComfyUI2025_131891_trim_run_keyframes_20260612_233937/cleaned`

Problem:

- The source endpoint frames were rejected by the artifact gate.
- Main issues: `duplicate_silhouette_area_high: 2`, `lower_body_pale_afterimage_review: 2`.
- Visual issue: the lower-body masked endpoint localized the edit, but the still image had noise, outfit redraw artifacts, and a beige background panel.

Trials:

| Trial | Output | Gate result | Visual decision |
|---|---|---|---|
| low denoise `0.18` | `outputs_image_quality_pdca/run_endpoint_quality_d018_20260612_234600` | not fully gated in final comparison | Too conservative. It preserves the source but barely improves the visible drawing. |
| medium denoise `0.35` | `outputs_image_quality_pdca/run_endpoint_quality_d035_20260612_234612` | `selected_proof_only`, no hard issue codes, `lower_body_pale_afterimage_review: 2` | Improves face, line quality, and fill stability. Does not fix background panel. |
| medium denoise `0.35` + bg cleanup `95` | `outputs_image_quality_pdca/run_endpoint_quality_d035_bgclean_20260612_234724` | `selected_proof_only`, no hard issue codes, `lower_body_pale_afterimage_review: 2` | Similar to plain `0.35`; cleanup threshold was too low to remove the beige panel. |
| high denoise `0.50` + bg cleanup `95` | `outputs_image_quality_pdca/run_endpoint_quality_d050_bgclean_20260612_234737` | `selected_proof_only`, no hard issue codes, `lower_body_pale_afterimage_review: 2` | More polished but begins changing outfit details. Use only when identity drift is acceptable for a still retake. |
| medium denoise `0.35` + bg cleanup `160` | `outputs_image_quality_pdca/run_endpoint_quality_d035_bgclean160_20260612_234849` | `adopted_full_source`, no hard issue codes, no review labels | Best still-image refinement. It removes the beige panel and improves line/color polish while keeping identity reasonably stable. |

Best current still-image quality recipe:

```bash
uv run python scripts/refine_wan_frames_img2img.py \
  --frames-dir <candidate_frames> \
  --output-root outputs_image_quality_pdca \
  --run-label <label> \
  --width 1024 \
  --height 1024 \
  --steps 24 \
  --cfg 5.4 \
  --denoise 0.35 \
  --background-cleanup-threshold 160 \
  --background-cleanup-min-channel 170 \
  --positive "masterpiece, best quality, polished anime game sprite keyframe, one full-body character, clean crisp line art, clean cel shading, stable face, stable outfit, sharp hands, sharp legs, complete shoes, pure white background, readable 2d game animation frame" \
  --negative "low quality, blurry, motion blur, ghost trail, afterimage, smeared limb, transparent limb, extra limbs, missing limbs, duplicate body, duplicate legs, broken hands, broken feet, distorted outfit, beige panel, gray panel, dark background, black background, strong cast shadow, background scenery, text, watermark, identity drift, face melting, changing outfit"
```

Then gate it:

```bash
uv run python scripts/repair_frame_artifacts.py \
  --frames-dir <refined_frames> \
  --output-root outputs_image_quality_pdca \
  --run-label <label>_quality_gate \
  --width 1024 \
  --height 1024 \
  --mask-only
```

## Decision

1024 img2img regeneration is useful for still-image polish:

- noise cleanup
- cleaner face and line art
- small missing/detail defects
- background panel cleanup when paired with `--background-cleanup-threshold 160`

It should not be treated as motion/action control:

- It does not turn a neutral endpoint into a readable run pose.
- It does not repair semantic failures such as weak hit reaction, missing weapon intent, or wrong pose.
- Higher denoise can improve polish but starts changing outfit/identity.

Use this as a post-generation quality pass after the frame already has acceptable pose/action semantics.
