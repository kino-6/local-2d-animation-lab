---
name: natural-sprite-controlnet-pdca
description: Local-first workflow for generating 120-frame 2D character game animation assets from a reference image plus natural-language action request using novaOrangeXL and ControlNet OpenPose templates. Use when working on ControlNet pose templates, ComfyUI novaOrangeXL generation, breakage evaluation, retake decisions, PDCA logs, Godot playback validation, or action variants such as walk, idle, sword/axe/bow attacks, and hit reactions.
---

# Natural Sprite ControlNet PDCA

## Top Rule

Use `novaOrangeXL + ControlNet(OpenPose)` as the main generation path. Treat the input image as a character design reference. Do not make rigged puppet animation, cutout shaking, or random independent still generation the primary workflow.

## Output Target

Generate 120-frame action assets. Do not downsample to 8-12 frames in this workflow. Frame reduction belongs to a separate thinning/export skill.

Each adopted run must produce:

- `frames/*.png`
- `contact_sheet.png`
- `preview.gif`
- `spritesheet.png`
- `manifest.json`
- `evaluation_report.json`
- `controlnet_pose/*.png`
- `comfy_workflows/*.json`
- `pdca_log.json` or a summary that points to it

## Required Defaults

- Checkpoint: `novaOrangeXL_v120.safetensors`
- ControlNet: `SDXL\OpenPoseXL2.safetensors`
- Frame count: `120`
- Output policy: preserve all 120 frames as the main asset
- Downsampling policy: use a separate thinning/export workflow
- Seed strategy: fixed seed with `seed_step=0`
- Baseline steps: `24`
- Baseline CFG: `6.0`
- Baseline ControlNet strength: `0.75`
- Strong pose retake: ControlNet strength `0.90`

## Pose Templates

Use `pose_templates/<action>/frame_000.json` through `frame_119.json` as first-class source assets. Render them to `pose_templates/<action>/controlnet/*.png` before generation.

Template frames must include:

- `action`
- `variant`
- `frame_index`
- `phase`
- `keypoints`
- `notes`

Shared phases:

- Walk: `contact`, `down`, `passing`, `up`
- Run: `contact`, `drive`, `flight`, `recover`
- Attack: `ready`, `anticipation`, `active`, `follow_through`, `recover`
- Hit: `neutral`, `impact`, `recoil`, `peak`, `recover`

Weapon actions also have reusable guide assets under `weapon_guides/<weapon>/`. Build them with:

```bash
uv run python scripts/build_weapon_guides.py --output-root weapon_guides --frame-count 120
```

Current guides encode:

- sword: hand anchor, blade line, slash arc
- axe: grip anchor, shaft line, head region, heavy swing arc
- bow: bow curve, string lines, arrow line, draw hand

These are control assets for the next weapon PDCA. Body OpenPose alone is not enough for weapon continuity.

When hand-authored templates still produce broken motion, switch to a motion-capture style control source before doing more prompt or seed search:

- Extract DWPose/OpenPose keypoints from a clean source action video.
- Align the extracted keypoints to the target character's full-body start-frame scale, hip height, shoulder width, and foot-contact baseline.
- Keep source-video confidence as a control signal where available. Stronger/confident lower-body and contact keypoints should render brighter or clearer than uncertain limbs.
- Convert the aligned keypoints into the same `pose_templates/<action>/frame_000.json` through `frame_119.json` format so the rest of the local pipeline remains unchanged.
- Use text prompts for framing, identity, and clean-background stability; do not ask text to invent the motion that should come from pose.

External rationale: current successful dance-style systems such as MusePose, Animate Anyone, and MimicMotion rely on reference-image preservation plus dense pose guidance, often with DWPose extraction, pose alignment, confidence-aware pose guidance, and temporal modeling. They are not primarily prompt-only animation systems.

Import an extracted motion source into the local template format:

```bash
uv run python scripts/import_motion_source_pose.py \
  --source extracted_openpose/run_source_json \
  --output-root pose_templates \
  --action run \
  --frame-count 120 \
  --target-template-root pose_templates \
  --target-template-name run \
  --render-style wan_confidence_lower \
  --source-start-index 2 \
  --min-frame-mean-confidence 0.4
```

Supported inputs are:

- a directory of OpenPose BODY_25 JSON files with `people[].pose_keypoints_2d`;
- a JSON file with `frames[]`;
- existing local template-style `keypoints`, optionally with per-keypoint confidence.

The script writes `frame_000.json` through `frame_119.json`, `controlnet/*.png`, `contact_sheet.png`, and `motion_source_report.json`.

For real source videos, inspect per-frame confidence before import. Drop weak startup frames or low-confidence detections with `--source-start-index`, `--source-end-index`, and `--min-frame-mean-confidence`; weak pose frames render faint controls and can poison Wan motion.

Local ComfyUI pose extraction setup:

- SDPose checkpoint: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/models/checkpoints/sdpose_wholebody_fp16.safetensors`
- JSON saver source: `comfy_custom_nodes/natural_sprite_pose_json_saver/__init__.py`
- Installed node path: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/custom_nodes/natural_sprite_pose_json_saver/__init__.py`

After restarting ComfyUI, verify `NaturalSpriteSavePoseKeypointsJSON` appears in `/object_info`. Then use:

```bash
uv run python scripts/run_sdpose_json_probe.py --check-only
```

```text
LoadVideo
-> GetVideoComponents
-> CheckpointLoaderSimple(sdpose_wholebody_fp16)
-> VAELoader(sdxl_vae)
-> SDPoseKeypointExtractor
-> NaturalSpriteSavePoseKeypointsJSON
```

Feed the saved JSON into `scripts/import_motion_source_pose.py`.

For video sources, use the dedicated probe script:

```bash
uv run python scripts/run_sdpose_video_json_probe.py \
  --video path/to/clean_walk_or_run_source.mp4 \
  --run-label clean_run_source
```

Use `--check-only` first. Do not queue the extraction while ComfyUI has active or pending jobs unless that is intentional:

```bash
uv run python scripts/run_sdpose_video_json_probe.py \
  --video path/to/clean_walk_or_run_source.mp4 \
  --check-only
```

Source-video prep findings:

- Prefer a full-body crop that makes the actor larger without clipping feet, hands, or head. A wider crop that preserves the full body is better than a tight crop that cuts the actor.
- Reject source clips that show only legs or feet. They may look like walking footage, but they cannot provide the upper-body and arm keypoints needed for reusable character action control.
- In the Mixkit walk-source trial, `crop=480:360:0:0` improved SDPose mean confidence compared with full-width padding, while `crop=360:360:0:0` clipped the actor and was rejected.
- Package each new source candidate before repeating generation. Use `scripts/export_source_probe_package.py` to bundle the source contact sheet, SDPose report, imported control contact sheet, span/gate reports, comparison sheet, and an explicit `accept`, `diagnostic_only`, or `reject` decision.
- Reject candidates that cannot keep at least 8 high-confidence, full-body pose frames after filtering. A lower-confidence import is allowed only as a diagnostic to prove whether the source is worth improving.
- Mixkit 35419 was rejected after this diagnostic path: the high-confidence import kept only 4 frames, the lower-confidence import kept 8 frames at mean confidence `0.37371`, and the Animate probe failed with `hard_failures: 5/8` plus gate `retake_required: 6/8`.
- When external source-video families stall, build a local synthetic side-view source to isolate pose-control noise from Wan generation failures:

```bash
uv run python scripts/build_synthetic_sideview_motion_source.py \
  --output-root outputs_motion_source_video_pdca \
  --template-name run_synthetic_sideview_walk_v1 \
  --action run \
  --variant synthetic_sideview_walk_v1 \
  --frame-count 120 \
  --render-style wan_confidence_lower
```

- Synthetic side-view v1 reduced selected-span structural hard failures to `0/8`, but the corrected artifact gate still rejected it with `retake_required: 3/8` because the output became dark and broad repair masks appeared. Treat this as diagnostic evidence, not an adopted asset.
- Stronger `wan_lower` control on the same synthetic source worsened the span to `hard_failures: 7/8`; stronger all-body pose lines are not automatically better.
- `wan_balanced` was added as an intermediate pose render style. It improved some appearance/background symptoms but reintroduced duplicate-leg and duplicate-silhouette failures; a 33-frame trial still failed with `retake_required: 4/8`.
- A bright appearance prompt with the original weak synthetic control made the character more readable but caused blue-gray background contamination and broad masks. Deterministic white cleanup produced white holes and still failed `retake_required: 8/8`.
- A small Wan `character_mask` trial with synthetic v1 also failed (`foreground_too_small: 8`, `retake_required: 8/8`). Do not use the current `character_mask` path as the next subject-preservation fix.
- `scripts/normalize_connected_background.py` can normalize simple border-connected backgrounds to white without using artifact masks. It did not rescue the bright-prompt synthetic output; gate stayed `retake_required: 8/8` because the contamination was entangled with the character silhouette.
- `scripts/person_cutout_background.py` can keep the largest detected subject component and white out the rest. It also did not rescue the bright-prompt synthetic output; the gray shadow/background mass stayed connected to the character and gate remained `retake_required: 8/8`.
- Next synthetic/local-control attempts should use generation-side subject/background separation rather than stronger pose lines, brighter text prompts, broad background masks, simple connected-background cleanup, largest-component cutout, or the current Wan `character_mask`.
- Auto character mask degraded the current `WanAnimateToVideo` path by fading the character and changing outfit identity. Do not make it the default until a later workflow proves otherwise.
- Stronger white-background prompting can reduce background color drift, but it does not repair leg afterimages or duplicate silhouettes. Structural ghosting must return to generation control, span selection, or a different video workflow.

VACE subject/motion split findings:

- `WanVaceToVideo` with `wan2.1_vace_1.3B_fp16.safetensors` is the current preferred local subject/motion split experiment when `WanAnimateToVideo` and FunControl stall.
- Use `scripts/run_wan_walk_i2v.py --mode vace --unet wan2.1_vace_1.3B_fp16.safetensors --weight-dtype default`.
- External workflow audit changed the planning priority. The closest outside project, `comfyui-2d-character-pipeline`, uses a staged route: single keyframe -> Wan2.2 i2v base motion -> BiRefNet/RMBG sprite sheet, while VACE is mostly reserved for masked cosmetic inpaint. Treat this as the next architecture to investigate once the missing local Wan2.2 GGUF / GGUF loader / VRAM eviction pieces are installed.
- Local audit result: `WanImageToVideo`, `WanVaceToVideo`, `WanAnimateToVideo`, video load/save nodes, `ImageStitch`, and `JoinImageWithAlpha` exist locally. Missing for a direct clone of that external route: Wan2.2 i2v GGUF high/low experts, `UnetLoaderGGUF`, `CLIPLoaderGGUF`, `VRAMUnloadModel`, ComfyUI-RMBG `BiRefNetRMBG`, and SAM3 route.
- Add pose-alignment diagnostics before generation. `src/natural_sprite_lab/pose_alignment.py` reports body envelope, hip height, shoulder width, ankle baseline, ankle separation, and facing direction. Use transforms only when the source is actually mis-scaled; the v4/v5 synthetic sources were already aligned before a naive envelope transform and became worse after forced alignment.
- Confidence-aware controls exist as `vace_walk_confidence_hint`, but the first subject-preservation retake failed. At VACE strength `0.65`, it kept motion (`mean foreground motion: 7.227`) but raised full 33 gate retakes to `15/33` with guide leakage and duplicate silhouette labels. Do not promote it as default.
- Start from the v4 edge-stride synthetic side-view motion settings before trying new proxy controls: `stride=0.083`, `lift=0.038`, `body_bob=0.012`, `--pose-render-style wan_balanced`.
- Keep `--vace-strength 1.0` as the current baseline. Raising it to `1.35` increased motion but collapsed the character into proxy-like/front-view structures in the tested run.
- Do not treat `vace_depth_proxy` or `vace_side_proxy` as adopted controls for this character/action. They are diagnostics; VACE copied their simplified structure into the output instead of only using them as motion guidance.
- The current walk-quality default is a full-body-reference VACE route, not the older bust-up-reference route:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode vace \
  --unet wan2.1_vace_1.3B_fp16.safetensors \
  --start-image outputs_fullbody_reference_cleanup/anima_00013_side_reference_bg_normalize_20260611_231757/frames/frame_000.png \
  --pose-root outputs_motion_source_video_pdca \
  --pose-template run_synthetic_sideview_walk_v4_edge_stride \
  --pose-render-style vace_walk_lower_hint \
  --output-root outputs_quality_pdca \
  --run-label phase4_ref_side_vace_walk_lower_hint_len121_768 \
  --width 768 \
  --height 768 \
  --length 121 \
  --steps 8 \
  --cfg 3.0 \
  --seed 717220
```

- Generate the full-body side-view start/reference frame before this VACE run. Use `scripts/generate_fullbody_reference_candidates.py` with `novaOrangeXL_v120.safetensors + SDXL/OpenPoseXL2`, then run start-frame artifact checks before using the selected frame as Wan/VACE input.
- Current selected full-body reference evidence: `review_packages/anima_00013_fullbody_side_reference_phase1_20260611_231836`.
- Current strongest 121-frame full-source evidence: `review_packages/phase4_ref_side_vace_walk_lower_hint_len121_full_source_review_20260611_235857`.
- Current selected-span evidence from the same 121-frame source: `review_packages/phase4_ref_side_vace_walk_lower_hint_len121_selected_review_20260612_000125`.
- Status is `selected_proof_only` / `needs_visual_quality_improvement`, not `adopted_full_source`. Full-source gate reached `retake_required: 0/121`, but the full sheet still has many small foot-shadow/contact repair candidates and the selected span is slightly below the foreground-motion target.
- A later labeled recheck made this stricter: `outputs_quality_artifact_repair/phase4_ref_side_vace_walk_lower_hint_len121_full_gate_labeled_20260612_001153` reports `retake_required: 2/121`, `candidate_status: rejected`, and review labels dominated by foot-shadow/contact artifacts and skin-colored lower-body afterimages. Treat this as the current adoption decision until a new generation beats it.
- The paired labeled span selection is `outputs_quality_span_selection/phase4_ref_side_vace_walk_lower_hint_len121_labeled_foreground_motion_gate_20260612_001054`; it reports `weak_motion_or_foot_sliding_review`.
- `vace_walk_lower_hint` is preferred over `wan_balanced`, `wan_walk_lower`, and `vace_walk_silhouette` for the next walk PDCA because it reduces copyable guide structure near arms, back, and hands. It may also reduce motion strength, so always check foreground-normalized motion and foot contact.
- Reject `vace_walk_silhouette` for this character/action unless substantially redesigned. The tested style avoided RGB OpenPose colors but VACE copied silhouette shapes into the character and increased retakes.
- When the 121-frame v4/lower-hint route is too conservative, use the v5 contact-swing motion source with lower VACE strength as the next probe:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode vace \
  --unet wan2.1_vace_1.3B_fp16.safetensors \
  --weight-dtype default \
  --vace-strength 0.55 \
  --start-image outputs_fullbody_reference_cleanup/anima_00013_side_reference_bg_normalize_20260611_231757/frames/frame_000.png \
  --pose-root outputs_motion_source_video_pdca \
  --pose-template run_synthetic_sideview_walk_v5_contact_swing \
  --pose-render-style vace_walk_lower_hint \
  --width 768 \
  --height 768 \
  --length 121 \
  --steps 8 \
  --cfg 3.0 \
  --seed 717220
```

- Short-proof evidence for this setting: `review_packages/phase3_v5_contact_swing_vace055_selected_review_20260612_003057`.
- It fixes the weak-motion label on a selected 16-frame span (`mean foreground motion: 7.695`, hard failures `0`, Godot `ok: true`) but is still only `selected_proof_only`; the full 33-frame gate has `retake_required: 2/33`.
- Full 121-frame evidence for this setting: `review_packages/phase4_v5_contact_swing_vace055_len121_selected_review_20260612_004320`.
- The full 121 source is rejected: `outputs_quality_artifact_repair/phase4_v5_contact_swing_vace055_len121_labeled_gate_20260612_004123` reports `retake_required: 51/121` dominated by `foreground_too_small`. The selected span has motion (`mean foreground motion: 5.569`) but visual review shows faint legs/feet and unstable foreground readability.
- A 1024 short probe improved density but still failed visual review: `review_packages/phase4_v5_vace055_len17_1024_selected_visual_reject_review_20260612_123057`. Heuristic gate was clean, but outfit color drift, arm/hair afterimages, and facing/identity instability were obvious. Do not run 1024 full 121 until identity/color stability is addressed.
- Current best walk route is single-keyframe Wan i2v, not VACE control video: `review_packages/phase10_single_keyframe_wan_i2v_len121_strict_selected_proof_review_20260612_130832`.
- Evidence: strict full 121 gate reports `retake_required: 0/121`, selected foreground motion `18.208`, and Godot `ok: true`.
- Do not mark it adopted yet. The strict visual labels report `lower_body_pale_afterimage_review: 12`, so it remains `selected_proof_only`.
- Lesson: removing copyable pose-control video improved identity and foreground preservation more than raising resolution or VACE strength. The next walk PDCA should reduce pale lower-body afterimages in Wan i2v without returning to VACE guide leakage.
- Next retake should preserve the subject under stronger motion. Do not send the v5 full-source result to Image2Image polish before foreground density and foot readability are fixed.
- Do not use v5 at VACE strength `1.0` as the next full-source default. It increases motion but produced hard failures and `retake_required: 7/33`.
- Do not use v6 moderate-contact as the next full-source default. It produced more hard failures than v5 and did not reduce copied artifacts.
- For small 512x512 full-body sprites, evaluate walk motion with foreground-normalized motion, not only canvas-wide pixel delta:

```bash
uv run python scripts/select_best_span.py \
  --frames-dir outputs_birefnet_foreground/<run>/frames \
  --foreground-mask-dir outputs_birefnet_foreground/<run>/foreground_masks \
  --span-length 16 \
  --motion-metric foreground \
  --min-mean-motion-delta 4.0
```

- The historical 512 baseline is the 121-frame VACE v4 edge-stride identity-prompt `wan_balanced` branch. Its full 121-frame package is `review_packages/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_full_source_review_20260611_182900`.
- Historical 512 full-source walk gate: artifact `retake_required: 0/121`, Godot validation `ok: true`.
- Selected-span evidence remains useful for comparison: foreground motion `4.993`, `hard_failures: 0/16`, artifact `retake_required: 0/16`.
- Use the same successful seed (`717220`) when comparing identity prompt changes; a different seed improved the head but reduced foreground motion to `3.213`.
- Include identity constraints that suppress the previous white headgear artifact: `uncovered brown bob hair`, `pink hair clip`, `navy sailor school uniform`, `red necktie`, plus negatives `hat`, `cap`, `hood`, `head scarf`, `white headgear`, `helmet`.
- Treat this walk route as the baseline comparator, while using the newer full-body-reference `vace_walk_lower_hint` route for quality work.
- Do not reject normal skirt plus two-foot walk frames as double-foot failures. Lower-body blob gates should count only foot-zone components; skirt/hem components that do not reach the foot zone are not duplicate feet.
- For visual quality work after the 512 walk convergence, test 768 VACE before jumping to 1024. A 768x768 121-frame `wan_walk_lower` run improved face/outfit/limb readability, but the full source still had `retake_required: 2/121`; treat it as a quality-improvement candidate, not a full-source adoption.
- `wan_walk_lower` is a lower-body-focused VACE control render style. It reduces upper-body guide leakage compared with `wan_balanced`, but does not remove every thin hand/leg guide artifact. Use it when image quality is more important than maximum whole-body pose pressure.
- When evaluating 768/1024 outputs, pass `--analysis-max-size 512` to `scripts/select_best_span.py` and `scripts/repair_frame_artifacts.py`. This keeps the original selected frames while making quality analysis tractable.
- Historical 768 quality proof package: `review_packages/walk_v4_identity_seed717220_vace_len121_768_lower_control_selected_quality_review_20260611_215932`. It is a 16-frame selected proof from a 121-frame source, with Godot `ok: true` and selected-span artifact gate `no_repair_needed: 16/16`.

Source probe package example:

```bash
uv run python scripts/export_source_probe_package.py \
  --source-label clean_walk_source_candidate \
  --source-video assets/source_motion/clean_walk_source.mp4 \
  --source-contact-sheet assets/source_motion/clean_walk_source_probe.jpg \
  --sdpose-report outputs_sdpose_video_json_probe/clean_walk_source/sdpose_video_json_probe_report.json \
  --motion-source-report outputs_motion_source_video_pdca/run_clean_walk_source/motion_source_report.json \
  --control-contact-sheet outputs_motion_source_video_pdca/run_clean_walk_source/contact_sheet.png \
  --decision diagnostic_only \
  --reason "Source has visible full-body side-view walking but needs generation proof."
```

Weapon guide handoff decision:

- Use weapon guides as line-art image sequences first.
- For Wan/video generation, pass the rendered line-art sequence as an extra local control video when the workflow supports it.
- For still-frame ControlNet start-frame generation, use the guide as a staged line-art/reference control image or mask-sidecar, not as a replacement for the body OpenPose template.
- Keep weapon masks in reports for validation and inpaint protection, but do not rely on masks alone to invent the weapon.
- Do not use a staged weapon-bearing reference frame as the only weapon control; it can help the first frame, but it does not guarantee continuity through the action.

## Generation Procedure

1. Build or update pose templates:

```bash
uv run python scripts/build_pose_templates.py --output-root pose_templates --frame-count 120
```

2. Run ControlNet PDCA for the target action:

```bash
uv run python scripts/pdca_controlnet_assets.py \
  --input assets/reference/Anima_00013_.png \
  --action attack_sword \
  --output-root outputs_controlnet_pdca \
  --pose-template-root pose_templates \
  --frame-count 120 \
  --retakes 3
```

Common actions are `walk`, `run`, `idle`, `attack_sword`, `attack_axe`, `attack_bow`, `hit_light`, `hit_heavy`, and `hit_knockback`.

3. Validate the adopted manifest in Godot:

```bash
uv run python scripts/godot_validate_summary.py \
  --summary outputs_controlnet_pdca/attack_sword_controlnet_summary.json
```

For Wan/video outputs, select the best contiguous span before Image2Image:

```bash
uv run python scripts/select_best_span.py \
  --frames-dir outputs_wan_action_repro/example/frames \
  --output-root outputs_span_selection \
  --run-label run_best_span \
  --span-length 8
```

Review `span_selection_report.json`, `span_contact_sheet.png`, and `span_preview.gif`. The report includes per-frame foreground visibility, background contamination, duplicate silhouette area, lower-body blob count, dark-frame ratio, motion continuity, and retake recommendations.

Current quality-gate thresholds:

- `foreground_coverage < 0.025`: subject too small
- `foreground_coverage > 0.35`: subject too large or merged with artifacts
- `duplicate_silhouette_area > 0.020`: duplicate body/afterimage risk
- `lower_body_blob_count > 2`: duplicate leg or foot risk
- `dark_ratio > 0.18`: dark-frame/background failure
- `background_contamination_ratio > 0.08`: background cleanup or retake needed
- `upper_body_center_shift > 0.18`: identity/camera stability risk
- `lower_body_pale_afterimage_review`: manual-review blocker for pale gray/blue-gray lower-body ghosting that is attached to the subject and can be missed by detached-artifact masks

Export a compact review package for selected frames:

```bash
uv run python scripts/export_review_package.py \
  --frames-dir outputs_span_selection/run_best_span/selected_frames \
  --output-root review_packages \
  --run-label run_review \
  --action run \
  --character-id anima_00013 \
  --source-report outputs_span_selection/run_best_span/span_selection_report.json \
  --validate-godot
```

The package writes `preview.gif`, `contact_sheet.png`, `manifest.json`, `review_summary.md`, and `godot_validation.json` when `--validate-godot` is used.

## Wan Video Workflow

Use this when a still-frame ControlNet run is too inconsistent frame-to-frame, especially for walk/run.

Stable local sequence:

```text
reference image
-> generate or extract one clean full-body side-view start frame
-> reject the start frame if it has multiple foreground components
-> prefer Wan i2v from the single keyframe for base walk motion when subject preservation matters
-> use VACE/control video only for controlled probes or action-specific experiments
-> BiRefNet foreground separation when background/contact artifacts need isolation
-> full-source artifact gate and foreground-motion span selection
-> compact selected-span and full-source review packages with Godot validation
-> low-denoise novaOrangeXL Image2Image only after the motion is structurally plausible
```

Do not pass a bust-up reference directly to Wan. Wan tends to preserve the start-image framing, so a close-up input stays close-up instead of becoming a full-body game asset.

Prepare a single-character Wan start frame from a still-frame candidate:

```bash
uv run python scripts/prepare_wan_start_frame.py \
  --input-frame outputs_next_phase_pdca_controlnet/anima_00013/run/run_strong_pose/frames/anima_00013_run_r02_000.png \
  --output-root outputs_next_phase_startframe \
  --run-label auto_cleaned_run_strong_pose \
  --width 1024 \
  --height 1024
```

Review `start_frame_report.json` and `start_frame_debug_sheet.png`. `extra_foreground_components_removed` is acceptable only when the cleaned output visibly keeps the intended main character. `missing_foreground` or a large secondary component means retake the still frame before Wan.

Legacy `WanAnimateToVideo` command shape:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode animate_pose \
  --start-image outputs_next_phase_startframe/cleaned_run_strong_pose_start.png \
  --pose-template run \
  --pose-render-style wan_lower \
  --pose-sample-span 119 \
  --run-label run_from_cleaned_single_start_probe \
  --output-root outputs_next_phase_pdca \
  --length 17 \
  --steps 6 \
  --cfg 3.0 \
  --seed 717173 \
  --post-trim-start 0
```

Recommended run settings from the 2026-06-11 PDCA:

- SDXL start frame: generate at `1024x1024`.
- Do not feed the original bust-up reference directly to Wan/VACE for full-body game assets. First generate or curate a clean 1024 full-body side-view reference.
- Wan/VACE walk probe: prefer `768x768` for quality work after a 512 baseline exists. Use `1024x1024` only as a short probe after the 768 route has a stable selected proof.
- Wan/VACE walk pose rendering: prefer `--pose-render-style vace_walk_lower_hint` for the current full-body-reference route. `wan_balanced` is useful as a comparator but can leak guide-like lines around hands and sides.
- Wan pose sampling: default behavior samples the full 120-frame pose template across the requested clip. `--pose-sample-span` can limit that range for experiments, but the 2026-06-11 `pose-sample-span=32` source-video run reduced motion delta while causing identity fading. Do not default to a narrow span without a passing quality gate.
- Wan `character_mask`: supported by `scripts/run_wan_walk_i2v.py`, but keep it off by default. The 2026-06-11 mask probes worsened run quality in this setup.
- Wan `continue_motion_max_frames=1` is a promising but not adopted setting for the current best walk source. One trial reached span score `0.83364` and gate `retake_required: 1/8` with small masks, but a seed repeat failed with `hard_failures: 6/8`. Use it as a controlled comparison setting, not as a default.
- Wan action prompts: keep text broad and stability-focused. Let the pose template carry action-specific motion. In the run PDCA, explicitly over-specifying separated legs made duplicate/ghost silhouettes worse, while the broader walk-cycle prompt plus `run` pose template produced the best span.
- Image2Image finish: denoise `0.20` to `0.30`, seed fixed with `--seed-step 0`.
- Block Image2Image and inpaint as adoption paths when the gate reports `duplicate_silhouette_area_high`, `double_foot_or_duplicate_leg_risk`, or `lower_body_blob_count_high`.
- Block adoption when full-source preview/contact sheets still show recurring guide-line leakage, strong afterimage, duplicate legs, headgear drift, or weak foot-contact readability, even if the artifact gate has `retake_required: 0`.

BiRefNet foreground separation findings from the 2026-06-11 PDCA:

- ComfyUI native BiRefNet can be used locally when `birefnet.safetensors` is installed under `ComfyUI/models/background_removal/`.
- Use it when the main failure is background drift, blue-gray haze, or character-connected background contamination that simple border cleanup cannot isolate.

```bash
uv run python scripts/birefnet_foreground_masks.py \
  --frames-dir outputs_span_selection/run_synthetic_sideview_walk_v1_bright_prompt_cont1_span_20260611_143816/selected_frames \
  --output-root outputs_birefnet_foreground \
  --run-label synthetic_sideview_walk_v1_bright_prompt_birefnet \
  --background white \
  --mask-grow 1 \
  --mask-blur 1 \
  --fps 8
```

- Follow with the normal artifact gate:

```bash
uv run python scripts/repair_frame_artifacts.py \
  --frames-dir outputs_birefnet_foreground/synthetic_sideview_walk_v1_bright_prompt_birefnet_YYYYMMDD_HHMMSS/frames \
  --output-root outputs_artifact_repair \
  --run-label synthetic_sideview_walk_v1_bright_prompt_birefnet_gate \
  --mask-only \
  --fps 8
```

- Positive result to remember: the synthetic bright-prompt walk span improved from broad background failure to `no_repair_needed: 8/8` after BiRefNet white compositing, with `mask_ok: 8/8`.
- Negative result to remember: the Mixkit clean-source baseline still retained leg/arm afterimages because those artifacts were inside the foreground mask. BiRefNet does not repair body-internal duplicate limbs.
- Do not adopt purely from `no_repair_needed`. Review playback/contact sheets for motion readability. A visually clean but low-travel 8-frame span is a candidate, not a 120-frame game asset.
- Feed BiRefNet mask stability and motion readability into span selection before refinement:

```bash
uv run python scripts/select_best_span.py \
  --frames-dir outputs_birefnet_foreground/synthetic_sideview_walk_v1_bright_prompt_birefnet_YYYYMMDD_HHMMSS/frames \
  --foreground-mask-dir outputs_birefnet_foreground/synthetic_sideview_walk_v1_bright_prompt_birefnet_YYYYMMDD_HHMMSS/foreground_masks \
  --min-mean-motion-delta 4.0 \
  --max-mean-foreground-mask-delta 0.12
```

- The first BiRefNet candidate had hard failures `0/8` but was flagged with `mean_motion_delta_too_low`; this is the correct outcome for a clean but weak-motion span.
- The 121-frame bright-prompt trial solved the low-motion issue but still failed visual adoption. The best 16-frame span had `mean_motion_delta: 7.484`, `hard_failures: 0/16`, and Godot `ok: true`, but visual review showed mesh-like legs and bag-like lower-body silhouettes.
- `scripts/birefnet_foreground_masks.py` now reports foreground-structure gates. Treat `review_sparse_foreground_bbox` and `review_lower_body_silhouette_wide` as manual-review blockers before refinement.
- Important: if broken legs or afterimages are inside the BiRefNet foreground mask, BiRefNet has done its job and the failure must go back to generation control. Do not refine or inpaint that candidate as if it were only a background problem.
- Lower-stride synthetic control is the current best research direction:

```bash
uv run python scripts/build_synthetic_sideview_motion_source.py \
  --output-root outputs_motion_source_video_pdca \
  --template-name run_synthetic_sideview_walk_v2_lower_stride \
  --action run \
  --variant synthetic_sideview_walk_v2_lower_stride \
  --frame-count 120 \
  --render-style wan_confidence_lower \
  --stride 0.075 \
  --lift 0.035 \
  --body-bob 0.012
```

- Do not pair this lower-stride source with weak `wan_confidence_lower` and expect a change; the 2026-06-11 v1/v2 long runs were byte-identical under the same seed/settings.
- Pairing the lower-stride source with `wan_balanced` produced the current best synthetic/local control branch:
  - Review package: `review_packages/synthetic_sideview_walk_v2_lower_stride_wan_balanced_review_20260611_154913`
  - Mean motion delta: `4.919`
  - Artifact gate: `no_repair_needed: 16/16`
  - BiRefNet structure gate: `mask_ok: 9`, `review_sparse_foreground_bbox: 7`
  - Godot validation: `ok: true`
- Treat it as `needs_manual_review`, not `adoptable`. It improves leg readability but still has sparse lower-body silhouettes and small residual foot/hand artifacts.
- Do not use the BiRefNet start-frame mask as `WanAnimateToVideo` `character_mask` in this workflow. The diagnostic branch:
  - Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_wan_balanced_birefnet_char_mask_len33_20260611_155309`
  - Review package: `review_packages/synthetic_sideview_walk_v2_wan_balanced_birefnet_char_mask_reject_review_20260611_155811`
  - Result: blurry silhouette-like frames, brown/yellow background drift, and `mean_motion_delta_too_low`.
- Use BiRefNet masks after generation for background separation and review gates; do not treat them as a proven generation-time subject/motion split.
- Next preferred integration is to strengthen lower-body structure without reintroducing duplicate silhouettes, or add a generation-time subject/motion split stronger than current WanAnimate pose input. Then apply the same BiRefNet, motion-readability, structure-review, artifact, and Godot gates.

FunControl recovery findings from the 2026-06-11 PDCA:

- Audit local Wan node/model capability before switching routes:

```bash
uv run python scripts/audit_comfy_wan_nodes.py --comfy-url http://127.0.0.1:8188
```

- Do not judge `WanFunControlToVideo` or `Wan22FunControlToVideo` without a Fun-Control diffusion model. With only the normal `wan2.1_i2v_480p_14B_fp16.safetensors`, FunControl routes reproduced pose/control lines rather than a usable character.
- The first local FunControl model installed for comparison was `Wan2.1-Fun-1.3B-Control.safetensors` under ComfyUI `models/diffusion_models`.
- Best FunControl probe so far:

```bash
uv run python scripts/run_wan_walk_i2v.py \
  --mode fun_control \
  --unet Wan2.1-Fun-1.3B-Control.safetensors \
  --pose-render-style controlnet \
  --pose-template run_mixkit_walk_source_filtered \
  --pose-root outputs_motion_source_video_pdca \
  --length 17 \
  --steps 8 \
  --cfg 3.0 \
  --seed 717193
```

- Result: `review_packages/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_review_20260611_131553` passed Godot loading, but the artifact gate still reported `retake_required: 5/8`. Treat this as research evidence, not adoption output.
- In this run, `controlnet` pose rendering beat `wan_confidence_lower` and `wan_line` for FunControl. `pose-sample-span=32` looked cleaner in isolated frames but still failed the gate.
- `controlnet_thin` was tested to reduce control-video carryover. It worsened the selected span and should not replace normal `controlnet` for this source.
- `--min-ankle-x-separation 0.06` was tested to remove leg-crossing source frames. It did not reduce retakes for the current Mixkit walk source.
- `Wan2.1-Fun-14B-Control.safetensors` was installed and tested. It did not beat the 1.3B `controlnet` candidate for the current source; gate stayed at `retake_required: 5/8`.
- Lower-stride synthetic source was also tested with FunControl 1.3B:
  - `controlnet` output: `review_packages/synthetic_sideview_walk_v2_fun_control_1p3b_controlnet_reject_review_20260611_160739`
  - `wan_balanced` output: `review_packages/synthetic_sideview_walk_v2_fun_control_1p3b_wan_balanced_reject_review_20260611_161208`
  - Result: both rejected. `controlnet` looked attractive as still frames but had `retake_required: 16/16` and `mean_motion_delta_too_low`; `wan_balanced` reduced artifact counts but became front-facing/static.
- Do not prefer FunControl only because the contact sheet has clean still frames. Walk adoption requires motion readability, not just frame beauty.
- Current implication: for walking, the next meaningful improvement is likely a cleaner full-body side-view source video with less lower-body occlusion/crossing, or a workflow with stronger subject/motion separation. Do not keep spending cycles on prompt-only tuning, more steps, or weaker control lines for this source.

Clean-source walk 0-retake evidence:

- Rechecked package: `review_packages/mixkit_walk_cont1_birefnet_0retake_manual_review_20260611_161805`
- Artifact gate after BiRefNet: `retake_required: 0/8`
- Motion gate: mean motion delta `6.001`
- Godot validation: `ok: true`
- Status: `manual_review`, not `adoptable`
- Reason: foreground-internal leg/arm afterimages remain visible in the contact sheet. BiRefNet removed background drift, but it cannot repair artifacts already inside the foreground silhouette.
- Do not promote a candidate to adoption solely because artifact `retake_required` is zero. Check BiRefNet structure gates and contact sheets.

Dedicated reports:

- `docs/wan_i2v_walk_findings.md`
- `docs/run_template_vs_walk_template_report.md`
- `docs/next_phase_run_generation_pdca_report.md`

## Breakage Evaluation

Reject or retake when any of these are visible in contact sheets, side-by-side sheets, evaluation reports, or Godot playback:

- Extra character or split foreground
- Missing/tiny/cropped full-body character
- Background clutter instead of transparent/plain game asset framing
- Character identity drift across frames
- Size, center, or color jitter across frames
- Pose does not follow the OpenPose template phase
- Weapon, hand, bow, string, or arrow breaks
- Hit reaction has weak recoil or unclear impact
- Animation reads as unrelated still images

Do not adopt a candidate just because the heuristic score is high. Treat `quality_gate.status == needs_retake_or_manual_review` as blocking until the side-by-side sheet and full contact sheet have been reviewed.

## Artifact Repair Gate

After Wan/Image2Image produces plausible motion, run explicit artifact repair before adoption:

```bash
uv run python scripts/repair_frame_artifacts.py \
  --frames-dir outputs_wan_img2img_refine/run_cleanup72_d035_20260611_010329/frames \
  --output-root outputs_artifact_repair_pdca \
  --run-label run_artifact_repair \
  --weapon none \
  --width 1024 \
  --height 1024
```

Use `--mask-only` first when tuning thresholds. Review `comparison_sheet.png`, `overlay_contact_sheet.png`, and `artifact_repair_report.json`.

Repair is allowed only for small masked artifacts such as pale ghost specks, background streaks, or detached tiny fragments. Do not use inpaint to hide structural failures. If the mask resembles a limb-shaped silhouette, leg, hand, weapon, or large shadow, review before repair; the 2026-06-11 run reproduction showed low-denoise inpaint can add a worse gray duplicate silhouette.

`scripts/apply_mask_cleanup.py` can deterministically paint mask pixels white for debugging or tiny background specks. It is not an adoption path for broad masks: the Mixkit walk trial turned broad cleanup masks into visible white holes and still failed duplicate-leg gates.

The artifact gate writes:

- `person_masks/*.png`
- `background_cleanup_masks/*.png`
- `masks/*.png`
- `person_mask_contact_sheet.png`
- `background_cleanup_mask_contact_sheet.png`
- `mask_contact_sheet.png`

The repair mask must not overlap the protected person mask. If a cleanup would touch the main character body, treat it as a retake or a more explicit foreground segmentation problem.

Treat these issue codes as retake/retrim blockers:

- `strong_duplicate_silhouette_risk`
- `double_foot_or_duplicate_leg_risk`
- `weapon_missing`
- `weapon_fragmented`
- `weapon_not_elongated`
- `weapon_detached`
- `repair_mask_too_large`

Broad repair masks are blockers even in `--mask-only` quality-gate runs. If `repair_mask_too_large` appears, the recommendation should be `retake_or_retrim_span_before_refine`; do not interpret a broad mask-only result as a polishable frame.

For sword, axe, and bow outputs, pass `--weapon sword`, `--weapon axe`, or `--weapon bow`. If the weapon gate fails, return to weapon-specific generation control instead of polishing the broken frame.

## Retake Policy

- Pose/action mismatch: revise keypoint template first.
- Weak action readability: increase pose contrast or ControlNet strength.
- Identity drift: strengthen identity prompt, lower CFG, lock seed, or add reference guidance.
- Extra characters/background clutter: strengthen negative prompt and full-body solo framing.
- Weapon breakage: add weapon-specific prompt/control guidance.
- Frame jitter: keep `seed_step=0`, reduce stochastic variation, and compare side-by-side sheets.
- Loop issue: revise first and last pose templates.
- Small ghost artifacts: use explicit masked inpaint after the motion already reads correctly.
- Duplicate legs, large afterimages, or broken weapons: retrim, retake, or add action-specific control.

Record every rejected candidate with failure reasons in the PDCA log.

## Known 2026-06-10 Findings

- `attack_sword` is the best current proof, but still needs weapon continuity and foreground cleanup.
- `attack_bow` is not acceptable from body OpenPose alone; add bow/string/arrow-specific guidance or a line-art/reference control layer.
- `hit_knockback` can create extra face or character fragments; foreground segmentation cleanup is needed.
- `walk` and `idle` generate E2E assets, but full contact sheets must be checked for duplicate/crowd-like frames.

## Non-Goals

- Do not make rig output the main deliverable.
- Do not use high heuristic score alone as adoption evidence.
- Do not adopt without contact sheet review.
- Do not adopt without Godot playback validation.
- Do not downsample 120-frame outputs in this workflow.
- Do not switch away from `novaOrangeXL` as default without a checkpoint comparison.
