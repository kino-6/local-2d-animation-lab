# Next-Phase Run Generation PDCA Report

Date: 2026-06-11
Branch: `codex/next-asset-quality-plan`

## Purpose

Run an actual local generation pass for the new `run` pose template and verify the result through span selection, low-denoise `novaOrangeXL` Image2Image refinement, artifact gating, and Godot review packaging.

This was an execution check, not an adoption claim.

## Commands And Outputs

### Attempt 1: Direct reference image to Wan

- Source: `assets/reference/Anima_00013_.png`
- Command family: `scripts/run_wan_walk_i2v.py --mode animate_pose --pose-template run`
- Output: `outputs_next_phase_pdca/run_template_probe_20260611_025948`
- Review package: `review_packages/run_template_probe_review_20260611_030108`
- Godot validation: `ok=true`
- Span score: `0.0`
- Verdict: `research_only`

Result: Wan preserved the input framing too strongly. Because the reference image is a close-up/bust image, the output stayed close-up and never became a full-body game asset. This confirms that the reference image must not be used directly as the Wan start image when it is not already a valid full-body animation frame.

### Attempt 2: Generated full-body start frame to Wan

- Start frame source: `outputs_next_phase_startframe/anima_00013/hit/20260611_030331_r01/frames/anima_00013_hit_r01_000.png`
- Wan output: `outputs_next_phase_pdca/run_from_fullbody_start_probe_20260611_030450`
- Review package: `review_packages/run_from_fullbody_start_review_20260611_030623`
- Godot validation: `ok=true`
- Span score: `0.11168`
- Verdict: `research_only`

Result: Full-body framing was preserved, which is better than attempt 1. However, the generated start frame lost character identity and became a front-facing metallic suit character, so the motion result was not useful as the target asset.

### Attempt 3: Cropped single-character ControlNet start frame to Wan

- ControlNet source: `outputs_next_phase_pdca_controlnet/anima_00013/run/run_strong_pose/frames/anima_00013_run_r02_000.png`
- Cleaned start image: `outputs_next_phase_startframe/cleaned_run_strong_pose_start.png`
- Wan output: `outputs_next_phase_pdca/run_from_cleaned_single_start_probe_20260611_030927`
- Span selection: `outputs_span_selection/run_from_cleaned_single_start_span_20260611_031024`
- Review package before refinement: `review_packages/run_from_cleaned_single_start_review_20260611_031102`
- `novaOrangeXL` img2img output: `outputs_wan_img2img_refine/run_cleaned_start_low_denoise_20260611_031209`
- Artifact gate: `outputs_artifact_repair/run_cleaned_start_artifact_gate_20260611_031332`
- Artifact gate with person/background masks: `outputs_artifact_repair/run_cleaned_start_person_mask_gate_20260611_032336`
- Final review package: `review_packages/run_cleaned_start_refined_review_20260611_031442`
- Three-way comparison: `review_packages/run_cleaned_start_refined_review_20260611_031442/source_refined_repair_comparison_sheet.png`
- Godot validation: `ok=true`
- Span score: `0.1644`
- Verdict: `needs_retake`

Result: This is the best local run from this PDCA. It produced a recognizable side-view running motion, but it is still not adoption-grade.

## Final Quality Gate

Final candidate status: `needs_retake`

Blocking artifact gate summary:

- `retake_required`: 8 / 8 frames
- `duplicate_silhouette_area_high`: 8 / 8 frames
- `double_foot_or_duplicate_leg_risk`: 6 / 8 frames
- `lower_body_blob_count_high`: 6 / 8 frames
- Recommendation: `retake_or_retrim_span_before_refine`

The follow-up person-mask gate produced:

- `person_mask_contact_sheet.png`
- `background_cleanup_mask_contact_sheet.png`
- per-frame `person_mask` and `background_cleanup_mask` paths in `artifact_repair_report.json`

This makes the foreground protection step explicit before any future background cleanup or masked inpaint.

The low-denoise img2img pass was intentionally conservative:

- Denoise: `0.25`
- Steps: `18`
- CFG: `5.5`
- Seed: `817173`
- Seed step: `0`
- Mean source delta: `1.346`

It slightly polished color and line quality but did not repair the structural leg/afterimage failures. This matches the standing rule that Image2Image is a finishing pass, not a structural repair path.

## Findings

- Direct Wan from the provided reference image is invalid when the reference is not already a full-body start frame.
- Wan works better after a single-character full-body start frame is supplied.
- The current still-frame generation path can produce a usable side-view full-body seed, but it can also create extra mini-characters or conflicting multi-pose artifacts.
- Cropping out the extra character improved the Wan result, but manual crop is not a repeatable Skill. The workflow needs automatic single-character extraction or an explicit inpaint cleanup step before video generation.
- `run` pose control influenced motion, but the lower body still collapses into white/ghosted legs. This must be handled before img2img refinement.
- Godot validation confirms frame loading/playback plumbing, not visual adoption quality.

## Recommended Settings From This PDCA

- Use 1024x1024 for SDXL still-frame start generation.
- Do not send bust-up reference images directly to Wan.
- Use `novaOrangeXL_v120.safetensors` for start-frame generation and low-denoise finishing.
- Use best-span selection before any img2img pass.
- Keep img2img denoise low, around `0.20` to `0.30`, only after the motion span is structurally plausible.
- Keep refinement seed fixed with `--seed-step 0` unless intentionally testing variation.
- Treat `duplicate_silhouette_area_high`, `double_foot_or_duplicate_leg_risk`, and `lower_body_blob_count_high` as retake triggers before inpaint.

## Cleanup Checklist

- Keep compact review packages under `review_packages/` while actively comparing runs.
- Treat these generated folders as cleanup candidates after this report is committed:
  - `outputs_next_phase_pdca/`
  - `outputs_next_phase_pdca_controlnet/`
  - `outputs_next_phase_startframe/`
  - `outputs_span_selection/`
  - `outputs_wan_img2img_refine/`
  - `outputs_artifact_repair/`
- Do not commit raw generated frames unless explicitly requested.
- Preserve only reports, scripts, tests, pose templates, and Skill documentation in git.

## Next Control Point

The next improvement should not be another prompt-only Wan run. The next control should be:

1. Generate or extract a single clean side-view full-body start frame automatically.
2. Reject start frames with more than one foreground component before Wan.
3. Add a start-frame cleanup step for small extra characters before video generation.
4. Strengthen run pose/video control specifically for lower-body leg separation.
5. Only then rerun Wan and low-denoise img2img.

## Follow-Up: Automatic Start-Frame Cleaner

Implemented `scripts/prepare_wan_start_frame.py` and `natural_sprite_lab.quality.start_frame` to replace the manual crop used in attempt 3.

Evidence:

- Input: `outputs_next_phase_pdca_controlnet/anima_00013/run/run_strong_pose/frames/anima_00013_run_r02_000.png`
- Cleaner output: `outputs_next_phase_startframe/auto_cleaned_run_strong_pose_20260611_032832/start_frame.png`
- Cleaner report: `outputs_next_phase_startframe/auto_cleaned_run_strong_pose_20260611_032832/start_frame_report.json`
- Cleaner debug sheet: `outputs_next_phase_startframe/auto_cleaned_run_strong_pose_20260611_032832/start_frame_debug_sheet.png`
- Wan output: `outputs_next_phase_pdca/run_from_auto_cleaned_start_probe_20260611_032902`
- Span selection: `outputs_span_selection/run_from_auto_cleaned_start_span_20260611_033004`
- Artifact gate: `outputs_artifact_repair/run_auto_cleaned_start_person_mask_gate_20260611_033029`
- Review package: `review_packages/run_auto_cleaned_start_review_20260611_033123`

Cleaner result:

- Detected components: `2`
- Removed issue: `extra_foreground_components_removed`
- Main foreground coverage: `0.1118`
- Largest secondary ratio: `0.21956`

Generation result:

- Best span moved to frames `9..16`
- Span score improved from `0.1644` to `0.34216`
- `double_foot_or_duplicate_leg_risk` improved from `6/8` to `4/8`
- `lower_body_blob_count_high` improved from `6/8` to `4/8`
- `duplicate_silhouette_area_high` remains `8/8`
- Final verdict remains `needs_retake`

Conclusion: automatic start-frame cleaning is a real improvement and should become part of the Wan workflow. It does not fully solve the run action because Wan still overexposes/ghosts fast legs in several frames. The next control point is exposure/background consistency and lower-body separation during Wan generation, not Image2Image.

## Follow-Up: Wan Lower-Body Pose Rendering

Implemented `--pose-render-style wan_lower` in `scripts/run_wan_walk_i2v.py`. This keeps the normal black-background ControlNet pose renderer intact, but lets Wan receive a white-background pose video with muted upper-body lines and stronger lower-body leg colors.

Evidence:

- Start frame: `outputs_next_phase_startframe/auto_cleaned_run_strong_pose_20260611_032832/start_frame.png`
- Wan output: `outputs_next_phase_pdca/run_wan_lower_pose_probe_20260611_033539`
- Span selection: `outputs_span_selection/run_wan_lower_pose_span_20260611_033631`
- Artifact gate: `outputs_artifact_repair/run_wan_lower_pose_person_mask_gate_20260611_033657`
- Permitted inpaint: `outputs_artifact_repair/run_wan_lower_pose_inpaint_allowed_20260611_033832`
- Review package: `review_packages/run_wan_lower_pose_inpaint_review_20260611_033957`

Quality changes versus the auto-cleaned start-frame run:

- Span score improved from `0.34216` to `0.67728`
- Span hard failures improved from `8/8` to `3/8`
- Artifact gate improved from `retake_required: 8/8` to `retake_required: 3/8`
- `double_foot_or_duplicate_leg_risk` improved from `4/8` to `1/8`
- `lower_body_blob_count_high` improved from `4/8` to `1/8`
- `duplicate_silhouette_area_high` improved from `8/8` to `3/8`
- `inpainted_frames`: `3`
- Godot validation: `ok=true`

Verdict: still `needs_retake`, but this is the strongest run candidate in the branch. The remaining problem is not E2E plumbing; it is residual skirt/leg afterimage and exposure ghosting in several fast-motion frames.

Recommended next attempt:

1. Keep `prepare_wan_start_frame.py`.
2. Keep `--pose-render-style wan_lower`.
3. Try a longer Wan source generation, then select the best span from later frames.
4. Try slightly lower CFG or more steps before any Image2Image pass.
5. Proceed to weapon PDCA only after run/walk have a span with no retake-required structural failures.

## Follow-Up: Longer/Lower-CFG Wan Checks

Two additional checks were run to see whether the `wan_lower` improvement could reach a no-retake span.

### Longer Source Probe

- Output: `outputs_next_phase_pdca/run_wan_lower_long_probe_20260611_034250`
- Length: `33`
- Steps: `8`
- CFG: `2.6`
- Seed: `717176`
- Span report: `outputs_span_selection/run_wan_lower_long_span_20260611_034430`
- Artifact gate: `outputs_artifact_repair/run_wan_lower_long_person_mask_gate_20260611_034512`

Result:

- Span score: `0.60248`
- Hard failures: `3/8`
- Gate: `retake_required: 3/8`, `repair_candidate: 4/8`, `no_repair_needed: 1/8`
- New problems: `foreground_too_large` and `background_contamination_high`

Verdict: worse than the shorter `wan_lower` proof. Longer generation increased motion, but it also increased background/scale instability.

### Alternate Seed Probe

- Output: `outputs_next_phase_pdca/run_wan_lower_seed_probe_20260611_034631`
- Length: `17`
- Steps: `8`
- CFG: `2.8`
- Seed: `717177`
- Span report: `outputs_span_selection/run_wan_lower_seed_span_20260611_034726`
- Artifact gate: `outputs_artifact_repair/run_wan_lower_seed_person_mask_gate_20260611_034752`

Result:

- Span score: `0.59648`
- Hard failures: `5/8`
- Gate: `retake_required: 4/8`, `repair_candidate: 1/8`, `no_repair_needed: 3/8`
- Motion became too weak: mean selected-frame delta `4.574`

Verdict: worse than the shorter `wan_lower` proof. The best current run remains `review_packages/run_wan_lower_pose_inpaint_review_20260611_033957`.

Current best run settings:

- start frame: `outputs_next_phase_startframe/auto_cleaned_run_strong_pose_20260611_032832/start_frame.png`
- pose render style: `wan_lower`
- length: `17`
- steps: `6`
- CFG: `3.0`
- seed: `717175`
- best span score: `0.67728`
- retake_required: `3/8`

Conclusion: the next meaningful improvement should not be random seed search. It should add stronger structural control for the lower body or a generation-time character/foreground mask. Weapon PDCA remains gated until walk/run can produce a no-retake structural span.

## Follow-Up: Wan Character Mask Checks

`WanAnimateToVideo` exposes an optional `character_mask` input. `scripts/run_wan_walk_i2v.py` now supports:

- `--auto-character-mask`
- `--character-mask`
- `--character-mask-threshold`
- `--character-mask-grow`
- `--character-mask-blur`
- `--invert-character-mask`

### Normal Character Mask

- Output: `outputs_next_phase_pdca/run_wan_lower_mask_probe_20260611_035333`
- Span report: `outputs_span_selection/run_wan_lower_mask_span_20260611_035421`
- Artifact gate: `outputs_artifact_repair/run_wan_lower_mask_person_gate_20260611_035452`

Result:

- Span score: `0.58477`
- Hard failures: `5/8`
- Gate: `retake_required: 7/8`, `repair_candidate: 1/8`
- Mean repair mask coverage: `0.48721`

Verdict: worse. The mask constrained or confused generation and produced large lower-body mask failures.

### Inverted Character Mask

- Output: `outputs_next_phase_pdca/run_wan_lower_inverted_mask_probe_20260611_035657`
- Span report: `outputs_span_selection/run_wan_lower_inverted_mask_span_20260611_035816`

Result:

- Span score: `0.0`
- Hard failures: `8/8`
- Mean frame delta included a large spike: `max_frame_delta=123.15`

Verdict: failed. Inverted mask is not usable for this WanAnimateToVideo setup.

Decision: keep character-mask support in the script because the node supports it and future workflows may need it, but do not enable it by default for the current run path. The best current proof remains the no-character-mask `wan_lower` run.

## Follow-Up: Default-Prompt Run Reproduction

Additional real generation was run to check whether the previous `wan_lower` result depended on the action prompt or on pose control.

### Failed Prompt/Phase Probes

- Output: `outputs_next_phase_pdca/run_wan_lower_leg_separation_probe_20260611_074918`
- Span report: `outputs_span_selection/run_wan_lower_leg_separation_span_20260611_075024`
- Gate: `outputs_artifact_repair/run_wan_lower_leg_separation_gate_20260611_075100`
- Result: span score `0.24874`, hard failures `8/8`, gate `retake_required: 7/8`

The stronger prompt that explicitly asked for separated legs made the result worse. Wan appeared to interpret the extra lower-body language as duplicate/ghost silhouettes.

Two pose/control probes also failed to beat the current best:

- `run_wan_lower_phase30_probe_20260611_075211`: span score `0.34655`, hard failures `7/8`, gate `retake_required: 5/8`
- `run_wan_lower_phase60_probe_20260611_075420`: same score and failure pattern as phase30
- `run_wan_lower_continue1_probe_20260611_075620`: same score and failure pattern as phase30

### Improved Default-Prompt Reproduction

- Output: `outputs_next_phase_pdca/run_wan_lower_default_prompt_repro_20260611_075739`
- Span report: `outputs_span_selection/run_wan_lower_default_prompt_repro_span_20260611_075937`
- Gate: `outputs_artifact_repair/run_wan_lower_default_prompt_repro_gate_20260611_080002`
- Review package: `review_packages/run_wan_lower_default_prompt_source_review_20260611_080321`
- Inpaint experiment: `outputs_artifact_repair/run_wan_lower_default_prompt_repro_inpaint_20260611_080110`
- Rejected inpaint review package: `review_packages/run_wan_lower_default_prompt_repro_review_20260611_080236`
- Godot validation: `ok=true`

Result:

- Span score improved from `0.67728` to `0.80297`
- Span hard failures improved from `3/8` to `1/8`
- Gate summary: `repair_candidate: 4/8`, `retake_required: 1/8`, `no_repair_needed: 3/8`
- Remaining issue: `duplicate_silhouette_area_high: 1`

Visual review:

- The selected source span is the current best run candidate and reads as a side-view moving animation.
- It is still not adoption-grade because thin leg/hand afterimages remain in several frames.
- The low-denoise inpaint pass was rejected. It repaired four candidate frames but added a large gray silhouette on frame 00, so the source span is the better artifact.

Updated decision:

1. Current best review package is `review_packages/run_wan_lower_default_prompt_source_review_20260611_080321`.
2. For this WanAnimate path, keep the prompt broad and stable. Do not over-specify lower-body anatomy in text.
3. Let reusable pose templates carry the action-specific motion. Use text mostly for character/framing/stability.
4. Do not run Image2Image/Inpaint automatically when the mask covers a meaningful limb-shaped silhouette. Require visual review or a stricter mask gate first.
5. Weapon PDCA remains gated because the run candidate still has `retake_required: 1/8`.

## Follow-Up: Longer Default-Prompt Reproduction

A longer default-prompt run was tested to see whether generating more frames could provide a cleaner selectable span.

- Output: `outputs_next_phase_pdca/run_wan_lower_default_prompt_long_repro_20260611_081118`
- Span report: `outputs_span_selection/run_wan_lower_default_prompt_long_repro_span_20260611_081616`
- Gate: `outputs_artifact_repair/run_wan_lower_default_prompt_long_repro_gate_20260611_081818`

Result:

- Span score: `0.52136`
- Span hard failures: `5/8`
- Gate: `retake_required: 7/8`, `repair_candidate: 1/8`
- Issues: `duplicate_silhouette_area_high: 6`, `double_foot_or_duplicate_leg_risk: 5`, `lower_body_blob_count_high: 5`, `strong_duplicate_silhouette_risk: 1`

Verdict: worse than the 17-frame default-prompt run. Longer generation did not solve the residual afterimage problem; it amplified duplicate lower-body artifacts. The current best remains `review_packages/run_wan_lower_default_prompt_source_review_20260611_080321`.

## External Workflow Lessons

External character-animation systems that show strong dance results do not mainly rely on prompt-only motion. The common pattern is:

- preserve the reference image with a dedicated reference path;
- drive motion with dense pose video;
- align the pose sequence to the subject's body scale and screen position;
- use temporal modeling or segment fusion for smoothness;
- use confidence/region weighting so reliable joints guide strongly and uncertain joints do not corrupt the frame.

Examples reviewed:

- MusePose uses pose-driven image-to-video with DWPose extraction, rendered DWPose videos, and a `pose_align.py` stage.
- Animate Anyone separates reference detail preservation, pose guiding, and temporal attention.
- MimicMotion emphasizes confidence-aware pose guidance, region-specific enhancement, and progressive latent fusion for long videos.

Decision for this project:

1. Stop treating more prompt tuning, random seed search, or longer Wan outputs as the main route for run stability.
2. Add a local motion-source stage: source action video -> DWPose/OpenPose extraction -> target-character pose alignment -> existing pose template format.
3. Keep the current generated run as a benchmark, not as an adopted asset.
4. Proceed to weapon PDCA only after the motion-source/pose-align path produces walk/run spans with no structural retake frames.

## Follow-Up: Motion-Source Import Scaffold

Implemented the local scaffold for the external-workflow lesson:

- Module: `src/natural_sprite_lab/motion_source.py`
- CLI: `scripts/import_motion_source_pose.py`
- Render style: `wan_confidence_lower`
- Tests: `tests/test_motion_source.py`

Capabilities:

- Read OpenPose BODY_25 JSON directories with `people[].pose_keypoints_2d`.
- Read JSON files with `frames[]`.
- Read existing local template-style `keypoints`.
- Preserve per-keypoint confidence.
- Align the source motion to a target local template's scale and foot baseline.
- Resample the source to the local 120-frame template format.
- Render confidence-aware Wan pose control frames.

Smoke check:

```text
uv run python scripts/import_motion_source_pose.py --source pose_templates/run --output-root outputs_motion_source_smoke --action run --frame-count 120 --target-template-root pose_templates --target-template-name run --render-style wan_confidence_lower
```

Result:

- Output template: `outputs_motion_source_smoke/run`
- Source frames: `120`
- Output frames: `120`
- Contact sheet: `outputs_motion_source_smoke/run/contact_sheet.png`
- Mean confidence: `1.0`

This does not yet solve run adoption quality by itself because it used the existing hand-authored run template as smoke input. It establishes the local handoff point for the next PDCA: feed it real extracted DWPose/OpenPose motion from a clean running or walking source video.

## Follow-Up: Local ComfyUI Pose Extraction Capability Probe

The local ComfyUI server at `http://127.0.0.1:8188/` was probed through `/object_info`.

Useful nodes found:

- `LoadVideo`: imports a video file.
- `GetVideoComponents`: extracts video frames, audio, and FPS.
- `SDPoseKeypointExtractor`: extracts OpenPose-frame keypoints from images.
- `SDPoseDrawKeypoints`: renders extracted keypoints to images.
- `huchenlei.LoadOpenposeJSON`: loads OpenPose JSON.

Current limitation:

- `SDPoseKeypointExtractor` requires `MODEL` and `VAE` inputs.
- The available checkpoint list did not show an obvious dedicated SDPose checkpoint.
- Therefore, direct source-video -> SDPose JSON extraction is not yet proven in this environment.

Next local setup task:

1. Install or register the Comfy-Org SDPose checkpoint if it is not already available.
2. Build a minimal ComfyUI extraction workflow:
   `LoadVideo -> GetVideoComponents -> SDPoseKeypointExtractor -> SDPoseDrawKeypoints`.
3. Add a JSON export path for the `POSE_KEYPOINT` output or use an existing OpenPose JSON saver if available.
4. Feed the exported JSON into `scripts/import_motion_source_pose.py`.
5. Run the existing Wan `wan_confidence_lower` path and compare against the current best review package.

Reference links:

- Comfy-Org SDPose checkpoints: `https://huggingface.co/Comfy-Org/SDPose/tree/main/checkpoints`
- ComfyUI SDPose video-to-pose-map workflow: `https://www.comfy.org/workflows/utility_sdpose_ood_video_to_pose_map-5fd7dc1f9db5/`
- SDPose-OOD upstream repository: `https://github.com/T-S-Liang/SDPose-OOD`

## Follow-Up: SDPose Checkpoint Installation And Pose-Map Probe

Installed the Comfy-Org SDPose checkpoint:

- Checkpoint: `sdpose_wholebody_fp16.safetensors`
- Location: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/models/checkpoints/sdpose_wholebody_fp16.safetensors`
- Size: `1916645792` bytes

ComfyUI recognized the checkpoint in `CheckpointLoaderSimple`.

Minimal API workflow:

```text
CheckpointLoaderSimple(sdpose_wholebody_fp16)
VAELoader(sdxl_vae)
LoadImage(clean start frame)
ImageScale(512x512)
SDPoseKeypointExtractor
SDPoseDrawKeypoints(draw body + feet)
SaveImage
```

Proof output:

- Report: `outputs_sdpose_probe/sdpose_start_frame_20260611_084749/sdpose_probe_report.json`
- Workflow: `outputs_sdpose_probe/sdpose_start_frame_20260611_084749/workflow/sdpose_probe_api.json`
- Pose map: `outputs_sdpose_probe/sdpose_start_frame_20260611_084749/frames/pose_000.png`

Visual result: SDPose detects a clean full-body skeleton from the current Wan start frame.

Remaining gap: ComfyUI currently exposes pose drawing, but no discovered node writes the `POSE_KEYPOINT` object to JSON. The next connector step is to add a small local ComfyUI custom node that saves `POSE_KEYPOINT` as OpenPose JSON, or find an existing installed saver node.

## Follow-Up: Pose JSON Saver Custom Node

Added a minimal ComfyUI custom node for saving `POSE_KEYPOINT` values as JSON:

- Repo source: `comfy_custom_nodes/natural_sprite_pose_json_saver/__init__.py`
- Installed copy: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/custom_nodes/natural_sprite_pose_json_saver/__init__.py`
- Probe script: `scripts/run_sdpose_json_probe.py`
- Node class: `NaturalSpriteSavePoseKeypointsJSON`
- Output JSON shape: `{ "format": "openpose_frames", "frames": [...] }`

Expected workflow after ComfyUI restart:

```text
LoadVideo
-> GetVideoComponents
-> CheckpointLoaderSimple(sdpose_wholebody_fp16)
-> VAELoader(sdxl_vae)
-> SDPoseKeypointExtractor
-> NaturalSpriteSavePoseKeypointsJSON
```

Status: node files are installed on disk, but the running ComfyUI process must be restarted or reloaded before `/object_info` can confirm the node. Verification remains pending.

Current check:

```text
uv run python scripts/run_sdpose_json_probe.py --check-only
```

Result before ComfyUI restart:

- `has_sdpose_checkpoint: true`
- `has_saver: false`
- `queue_running`: reports active ComfyUI work
- `queue_pending`: reports queued ComfyUI work

Restart decision:

- ComfyUI queue check near the 3h safety limit showed `running: 1`, `pending: 22`.
- A later check showed `running: 1`, `pending: 10`.
- The final check before the 3h safety limit showed `running: 1`, `pending: 0`.
- The saver node was therefore not verified in the running process, because restarting ComfyUI would interrupt active local work.
- The next operator action is to restart or reload ComfyUI when both `queue_running` and `queue_pending` are `0`, then run `uv run python scripts/run_sdpose_json_probe.py --check-only`.

Verification after ComfyUI restart:

```json
{
  "has_saver": true,
  "has_sdpose_checkpoint": true,
  "queue_running": 0,
  "queue_pending": 0
}
```

Minimal JSON export probe:

- Report: `outputs_sdpose_json_probe/sdpose_start_frame_json_probe_20260611_085935/sdpose_json_probe_report.json`
- Workflow: `outputs_sdpose_json_probe/sdpose_start_frame_json_probe_20260611_085935/workflow/sdpose_json_probe_api.json`
- JSON output: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/output/natural_sprite_lab/pose_keypoints/sdpose_start_frame_json_probe_00000.json`

Import probe:

```text
uv run python scripts/import_motion_source_pose.py --source C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/output/natural_sprite_lab/pose_keypoints/sdpose_start_frame_json_probe_00000.json --output-root outputs_motion_source_sdpose_probe --action run --frame-count 120 --target-template-root pose_templates --target-template-name run --render-style wan_confidence_lower
```

Result:

- Output template: `outputs_motion_source_sdpose_probe/run`
- Source frames: `1`
- Output frames: `120`
- Contact sheet: `outputs_motion_source_sdpose_probe/run/contact_sheet.png`
- Mean confidence: `0.69198`

This proves the local connector path for image-derived SDPose JSON. It is not yet a source-video-derived motion PDCA because the probe used a single start frame.

## Follow-Up: Video SDPose JSON Probe Script

Added a video-source probe script:

- Script: `scripts/run_sdpose_video_json_probe.py`
- Workflow: `LoadVideo -> GetVideoComponents -> SDPoseKeypointExtractor -> NaturalSpriteSavePoseKeypointsJSON`
- ComfyUI input staging: copies the video to `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/input/natural_sprite_lab/`

Prepared a local MP4 smoke input from the current best run preview:

- Source GIF: `review_packages/run_wan_lower_default_prompt_source_review_20260611_080321/preview.gif`
- Smoke MP4: `outputs_motion_source_video_probe/run_best_review_smoke_source.mp4`

This smoke MP4 is only a connector test input. It is generated from an already imperfect candidate and must not be treated as clean source-motion evidence.

Current video probe check:

```json
{
  "has_saver": true,
  "has_sdpose_checkpoint": true,
  "has_video_nodes": true,
  "queue_running": 1,
  "queue_pending": 9
}
```

Decision: do not queue the video extraction while ComfyUI is busy. The next action is to run the video probe when both queue counts are zero, preferably with a clean external walk/run source video rather than the smoke MP4.

## Follow-Up: Motion-Source Smoke Wan PDCA

The smoke MP4 was run through the full connector path to verify wiring:

```text
current best review preview.gif
-> smoke MP4
-> LoadVideo/GetVideoComponents
-> SDPoseKeypointExtractor
-> NaturalSpriteSavePoseKeypointsJSON
-> import_motion_source_pose.py
-> WanAnimateToVideo with wan_confidence_lower
-> best-span selection
-> artifact gate
-> review package
```

Evidence:

- Smoke MP4: `outputs_motion_source_video_probe/run_best_review_smoke_source.mp4`
- SDPose video JSON report: `outputs_sdpose_video_json_probe/sdpose_video_json_probe_20260611_115606/sdpose_video_json_probe_report.json`
- Saved JSON: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/output/natural_sprite_lab/pose_keypoints/sdpose_video_json_probe_00000.json`
- Imported template: `outputs_motion_source_video_probe/run_smoke_video`
- Wan output: `outputs_next_phase_pdca/run_motion_source_smoke_wan_probe_20260611_115800`
- Span report: `outputs_span_selection/run_motion_source_smoke_wan_span_20260611_115915`
- Artifact gate: `outputs_artifact_repair/run_motion_source_smoke_wan_gate_20260611_115948`
- Review package: `review_packages/run_motion_source_smoke_wan_review_20260611_120038`

Result:

- Imported source frames: `8`
- Imported output frames: `120`
- Imported mean confidence: `0.46661`
- Wan span score: `0.36098`
- Span hard failures: `7/8`
- Gate: `retake_required: 7/8`, `no_repair_needed: 1/8`
- Main issues: `duplicate_silhouette_area_high: 6`, `double_foot_or_duplicate_leg_risk: 3`, `lower_body_blob_count_high: 3`, `strong_duplicate_silhouette_risk: 4`
- Godot validation: `ok=true`

Verdict: connector proof only, not quality proof. The result is readable as walking, but the smoke source inherits the prior candidate's ghosting and produces too many structural retake frames. The next quality attempt must use a clean external walk/run source video, not a generated review GIF.

External source attempt:

- Candidate: Wikimedia Commons `File:Walk-Cycle.gif`
- License noted on Commons: CC BY 3.0 / GFDL
- Result: direct download from `upload.wikimedia.org` returned HTTP 429, so it was not used in this PDCA.
- Next action: acquire a clean walk/run source through a non-rate-limited route or provide a local source video under `assets/source_motion/`.

## Follow-Up: Clean External Walk Source PDCA

Downloaded and prepared a clean external walk source from Mixkit video `4855`:

- Source page cache: `assets/source_motion/mixkit_4855_page.html`
- Original downloaded video: `assets/source_motion/mixkit_4855_young_man_walk_360.mp4`
- Prepared SDPose source: `assets/source_motion/mixkit_4855_walk_source_512_8fps.mp4`
- Prep command: `ffmpeg -ss 1.0 -t 2.2 -i ... -vf "fps=8,scale=512:-2,pad=512:512:(ow-iw)/2:(oh-ih)/2:white,format=yuv420p"`
- Source properties: `512x512`, `8fps`, `18` frames, `2.25s`

SDPose extraction:

- Report: `outputs_sdpose_video_json_probe/mixkit_walk_source_20260611_120833/sdpose_video_json_probe_report.json`
- Saved JSON: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/output/natural_sprite_lab/pose_keypoints/mixkit_walk_source_00000.json`
- Initial import mean confidence: `0.56032`

New workflow improvement:

- Added source-frame filtering to `scripts/import_motion_source_pose.py`.
- Added `--source-start-index`, `--source-end-index`, and `--min-frame-mean-confidence`.
- Reason: SDPose on real video produced weak first frames. Using them made the rendered pose controls faint and poisoned Wan motion control.
- Filter used: `--source-start-index 2 --min-frame-mean-confidence 0.4`
- Retained source indices: `2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17`
- Filtered import mean confidence: `0.62806`
- Imported template: `outputs_motion_source_video_pdca/run_mixkit_walk_source_filtered`
- Contact sheet: `outputs_motion_source_video_pdca/run_mixkit_walk_source_filtered/contact_sheet.png`

Wan generation:

```text
uv run python scripts/run_wan_walk_i2v.py --mode animate_pose --start-image outputs_next_phase_startframe/auto_cleaned_run_strong_pose_20260611_032832/start_frame.png --pose-root outputs_motion_source_video_pdca --pose-template run_mixkit_walk_source_filtered --pose-render-style wan_confidence_lower --run-label run_motion_source_mixkit_walk_filtered --output-root outputs_next_phase_pdca --length 17 --steps 6 --cfg 3.0 --seed 717182 --post-trim-start 0 --timeout-seconds 1800
```

Evidence:

- Wan output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_filtered_20260611_121039`
- Span report: `outputs_span_selection/run_motion_source_mixkit_walk_filtered_span_20260611_121146/span_selection_report.json`
- Artifact gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_filtered_gate_20260611_121210/artifact_repair_report.json`
- Review package: `review_packages/run_motion_source_mixkit_walk_filtered_review_20260611_121316`
- Godot validation: `ok=true`

Result:

- Span: frames `4..11`
- Span score: `0.75525`
- Span hard failures: `0/8`
- Artifact gate: `repair_candidate: 5`, `retake_required: 1`, `no_repair_needed: 2`
- Main issues: `masked_ghost_or_small_artifact: 6`, `strong_duplicate_silhouette_risk: 1`
- Motion metrics: mean frame delta `19.917`

Comparison against previous best:

- Previous best package: `review_packages/run_wan_lower_default_prompt_source_review_20260611_080321`
- Previous best span report: `outputs_span_selection/run_wan_lower_default_prompt_repro_span_20260611_075937/span_selection_report.json`
- Previous best score: `0.80297`
- Previous best span hard failures: `1/8`
- Previous best artifact gate: `retake_required: 1`, `repair_candidate: 4`, `no_repair_needed: 3`

Verdict:

- The clean external motion source improves action readability: the result looks more like actual walking than the smoke source and preserves a clearer leg alternation.
- It is still not adoption-grade. The selected span has one retake frame, residual leg afterimages, and significant background color drift toward yellow/brown.
- This validates the direction but not the final quality. Next PDCA should keep the source-video-derived pose path and focus on pre-processing plus generation constraints:
  - tighter crop or person-scale normalization before SDPose extraction,
  - stronger white-background constraint and/or character mask during Wan,
  - rerun gates until `retake_required: 0/8`.

## Follow-Up: Clean Source Preprocess And Wan Constraint PDCA

Preprocess trial:

- Bad crop trial: `assets/source_motion/mixkit_4855_walk_source_crop_left_512_8fps.mp4`
- Result: increased person scale, but clipped the actor near the right edge. Rejected before SDPose/Wan.
- Accepted crop trial: `assets/source_motion/mixkit_4855_walk_source_crop480_512_8fps.mp4`
- Prep command: `ffmpeg -ss 1.0 -t 2.2 -i ... -vf "crop=480:360:0:0,fps=8,scale=512:-2,pad=512:512:(ow-iw)/2:(oh-ih)/2:white,format=yuv420p"`
- Probe contact sheet: `assets/source_motion/mixkit_4855_crop480_probe_contact_sheet.png`

SDPose extraction improved substantially:

- SDPose report: `outputs_sdpose_video_json_probe/mixkit_walk_source_crop480_20260611_121702/sdpose_video_json_probe_report.json`
- Saved JSON: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/output/natural_sprite_lab/pose_keypoints/mixkit_walk_source_crop480_00000.json`
- Per-frame detection: all `18` source frames had `18` readable keypoints.
- Filtered template: `outputs_motion_source_video_pdca/run_mixkit_walk_source_crop480_filtered`
- Filtered mean confidence: `0.72162`
- Earlier non-crop template mean confidence: `0.62806`

Wan constraint trials:

1. `crop480 + stronger white prompt + auto character mask`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_crop480_white_mask_20260611_121817`
   - Span report: `outputs_span_selection/run_motion_source_mixkit_crop480_white_mask_span_20260611_122136/span_selection_report.json`
   - Span score: `0.4306`
   - Span hard failures: `6/8`
   - Verdict: failed. The auto mask made the character fade into a ghost silhouette and changed the outfit near the end.

2. `crop480 + stronger white prompt + no mask`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_crop480_white_nomask_20260611_121936`
   - Span report: `outputs_span_selection/run_motion_source_mixkit_crop480_white_nomask_span_20260611_122134/span_selection_report.json`
   - Span score: `0.58568`
   - Span hard failures: `4/8`
   - Verdict: failed. White background improved, but strong leg afterimages and structural ghosting increased.

3. `crop480 + default prompt + no mask`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_crop480_default_prompt_20260611_122209`
   - Verdict from contact sheet: failed before packaging. Motion was large, but the character collapsed toward a dark silhouette and colored background panels.

Updated conclusions:

- Source-video preprocessing is useful and measurable. The crop480 source raised SDPose confidence from `0.62806` to `0.72162`.
- The next bottleneck is Wan generation stability, not pose extraction. Stronger prompt text and auto character mask did not solve structural ghosting.
- For this workflow, auto character mask should not be the next default for `WanAnimateToVideo`.
- The next useful PDCA should test generation-side changes that reduce temporal ghosting without losing identity:
  - shorter/more stable selected pose span,
  - different seed and lower motion amplitude from the same crop480 pose template,
  - first/last or reference-frame constraints if compatible with the pose workflow,
  - post-generation span selection before any img2img refinement.

## Follow-Up: Short Motion-Amplitude PDCA

Tested whether a shorter source pose span reduces residual leg afterimages:

- Imported template: `outputs_motion_source_video_pdca/run_mixkit_walk_source_crop480_short_filtered`
- Source indices: `2..9`
- Source frames: `8`
- Mean confidence: `0.67571`
- Wan output: `outputs_next_phase_pdca/run_motion_source_mixkit_crop480_short_20260611_122721`
- Span report: `outputs_span_selection/run_motion_source_mixkit_crop480_short_span_20260611_122832/span_selection_report.json`
- Artifact gate: `outputs_artifact_repair/run_motion_source_mixkit_crop480_short_gate_20260611_122902/artifact_repair_report.json`

Result:

- Motion metrics mean frame delta: `5.835`
- Span score: `0.34176`
- Span hard failures: `7/8`
- Gate: `retake_required: 6`, `repair_candidate: 1`, `no_repair_needed: 1`
- Main issues: `duplicate_silhouette_area_high: 6`, `strong_duplicate_silhouette_risk: 3`, `double_foot_or_duplicate_leg_risk: 3`, `lower_body_blob_count_high: 3`

Verdict:

- The contact sheet looked more stable at first glance because identity and background were cleaner.
- The quality gate correctly caught that pale duplicate legs remained in most frames.
- Lower motion amplitude alone is not enough. It reduces frame delta but leaves structural ghosting, so the next attempt should change generation conditioning rather than only shortening source motion.

## Follow-Up: Pose Sampling And Cleanup PDCA

Added a Wan pose sampling control:

- Script: `scripts/run_wan_walk_i2v.py`
- New option: `--pose-sample-span`
- Reason: the script previously sampled the full 120-frame template across every 17-frame Wan probe. That can create large pose jumps and may increase leg afterimages.
- Tests: `tests/test_wan_walk_i2v_script.py`

Limited-span trial:

- Output: `outputs_next_phase_pdca/run_motion_source_mixkit_crop480_span32_20260611_124116`
- Settings: `run_mixkit_walk_source_crop480_filtered`, `--pose-sample-span 32`, seed `717187`
- Motion metrics: mean frame delta `6.697`
- Verdict: failed before packaging. Motion amplitude was lower, but identity faded badly and the character became washed out through several frames.

Phase-shift trials:

- Phase 40 output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_phase40_20260611_124242`
- Phase 40 span: `outputs_span_selection/run_motion_source_mixkit_walk_phase40_span_20260611_124429/span_selection_report.json`
- Phase 40 gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_phase40_gate_20260611_124508/artifact_repair_report.json`
- Phase 40 result: span score `0.59264`, gate `retake_required: 8/8`

- Phase 80 output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_phase80_20260611_124244`
- Phase 80 span: `outputs_span_selection/run_motion_source_mixkit_walk_phase80_span_20260611_124428/span_selection_report.json`
- Phase 80 gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_phase80_gate_20260611_124507/artifact_repair_report.json`
- Phase 80 result: span score `0.54431`, gate `retake_required: 6/8`

Verdict: phase shifting did not solve the core failure. Some spans looked usable at a glance, but the gate consistently detected duplicate legs and lower-body blobs.

Deterministic mask cleanup trial:

- Script: `scripts/apply_mask_cleanup.py`
- Tests: `tests/test_mask_cleanup_script.py`
- Input: `outputs_artifact_repair/run_motion_source_mixkit_walk_filtered_gate_20260611_121210/source_frames`
- Masks: `outputs_artifact_repair/run_motion_source_mixkit_walk_filtered_gate_20260611_121210/masks`
- Output: `outputs_mask_cleanup/run_motion_source_mixkit_walk_filtered_white_cleanup_20260611_123516`
- Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_filtered_white_cleanup_gate_20260611_123534/artifact_repair_report.json`
- Result: `retake_required: 5/8`

Verdict: deterministic white-mask cleanup is not a safe adoption path for these frames. Small masks can remove specks, but broad masks turn background contamination into obvious white holes and do not fix structural leg ghosts.

Current best remains:

- Review package: `review_packages/run_motion_source_mixkit_walk_filtered_review_20260611_121316`
- Status: useful motion-source evidence, not adoption-grade.
- Best known clean-source source-video gate: `retake_required: 1/8`.

Next useful work:

- Try a different source-video family or pose-control backend before more prompt-only tuning.
- Investigate whether WanAnimateToVideo can combine pose input with a stronger first/last-frame or reference constraint.
- Keep `--pose-sample-span` as an experimental control, but do not default it to a narrow span based on this run.

## Follow-Up: Alternate Source Candidate Rejection

Downloaded a second Mixkit walking-family candidate:

- Source: `https://assets.mixkit.co/videos/23410/23410-360.mp4`
- Local file: `assets/source_motion/mixkit_23410_man_concrete_sidewalk_360.mp4`
- Probe sheet: `assets/source_motion/mixkit_23410_probe_contact_sheet.png`

Verdict: rejected before SDPose/Wan. The clip is primarily foot/leg close-up footage, not full-body profile walking. It cannot provide the full upper-body, arm, hip, and leg keypoints needed for reusable 2D character action control.

## Follow-Up: FunControl Recovery PDCA

Reason:

- Previous attempts showed that duplicate legs, strong afterimages, and background drift are generation-control failures.
- More prompt tuning, broad masks, and img2img cleanup did not solve structural walking failures.
- Local ComfyUI has `WanAnimateToVideo`, `WanFunControlToVideo`, `Wan22FunControlToVideo`, and `WanFirstLastFrameToVideo`.

Node/model audit:

- Script added: `scripts/audit_comfy_wan_nodes.py`
- Test added: `tests/test_comfy_wan_node_audit.py`
- Audit result before model install: `outputs_comfy_audit/wan_node_audit_20260611_130532/wan_node_audit_summary.md`
- `WanAnimateToVideo` has `reference_image + pose_video + character_mask`, but no `end_image`.
- `WanFunControlToVideo` and `Wan22FunControlToVideo` are available, but initially no Fun-Control UNet was installed.
- Installed local model: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/models/diffusion_models/Wan2.1-Fun-1.3B-Control.safetensors`
- Audit result after install: `outputs_comfy_audit/wan_node_audit_20260611_130916/wan_node_audit_summary.md`

Control-route trials:

1. `Wan22FunControlToVideo` with normal Wan 14B I2V model
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_wan22_fun_control_20260611_130015`
   - Span: `outputs_span_selection/run_motion_source_mixkit_walk_wan22_fun_control_span_20260611_130107`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_wan22_fun_control_gate_20260611_130138`
   - Result: failed. The generated video mostly reproduced the green control video, not the character.

2. `WanFunControlToVideo` with normal Wan 14B I2V model
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_20260611_130138`
   - Span: `outputs_span_selection/run_motion_source_mixkit_walk_fun_control_span_20260611_130258`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_gate_20260611_130325`
   - Result: failed. The generated video mostly reproduced faint pose lines and did not produce a stable character.

3. `WanFunControlToVideo` with `Wan2.1-Fun-1.3B-Control`, `wan_confidence_lower`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_1p3b_20260611_130931`
   - Span: `outputs_span_selection/run_motion_source_mixkit_walk_fun_control_1p3b_span_20260611_130958`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_1p3b_gate_20260611_131029`
   - Result: improved. The output became character animation instead of pose-line reconstruction, but gate stayed `retake_required: 8/8`.

4. `WanFunControlToVideo` with `Wan2.1-Fun-1.3B-Control`, `controlnet`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_20260611_131029`
   - Span: `outputs_span_selection/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_span_20260611_131122`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_gate_20260611_131151`
   - Gate summary: `no_repair_needed: 2`, `repair_candidate: 1`, `retake_required: 5`
   - Review package: `review_packages/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_review_20260611_131553`
   - Godot validation: `ok: true`
   - Result: best new FunControl candidate, but still below the current best `WanAnimateToVideo` walk span.

5. `WanFunControlToVideo` with `Wan2.1-Fun-1.3B-Control`, `wan_line`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_1p3b_wan_line_20260611_131151`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_1p3b_wan_line_gate_20260611_131314`
   - Result: failed with `retake_required: 8/8`.

6. `WanFunControlToVideo` with `Wan2.1-Fun-1.3B-Control`, `controlnet`, `pose-sample-span=32`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_span32_20260611_131315`
   - Span: `outputs_span_selection/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_span32_span_20260611_131414`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_span32_gate_20260611_131448`
   - Result: visually cleaner in some frames, but still `retake_required: 8/8`; the gate consistently detected duplicate silhouette artifacts.

Updated conclusion:

- FunControl should not be judged without a Fun-Control UNet. With the correct 1.3B model, it starts generating character animation.
- The current best new FunControl setting is `Wan2.1-Fun-1.3B-Control + WanFunControlToVideo + pose-render-style controlnet`.
- It is not yet adoption-grade and does not beat the previous best Animate path.
- The next PDCA should either:
  - install and compare a larger Fun-Control model if available locally,
  - improve pose/control-video rendering to reduce leg afterimage carryover,
  - or use a cleaner full-body walking source with less leg crossing before returning to generation.

External references used:

- ComfyUI Wan2.1 Fun Control guide: `https://docs.comfy.org/tutorials/video/wan/fun-control`
- Hugging Face model file used for the local 1.3B probe: `https://huggingface.co/alibaba-pai/Wan2.1-Fun-1.3B-Control/blob/main/diffusion_pytorch_model.safetensors`

## Follow-Up: FunControl Control-Rendering And 14B PDCA

Implemented controls:

- Added pose render style: `controlnet_thin`
- Files: `src/natural_sprite_lab/pose_templates.py`, `scripts/run_wan_walk_i2v.py`, `scripts/import_motion_source_pose.py`
- Added source-pose filter: `--min-ankle-x-separation`
- Reason: test whether weaker control lines or removing leg-crossing source frames reduces duplicate-leg carryover.

Trials:

1. `Wan2.1-Fun-1.3B-Control`, `controlnet_thin`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_thin_20260611_132127`
   - Span: `outputs_span_selection/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_thin_span_20260611_132155`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_thin_gate_20260611_132223`
   - Result: worsened. Span score `0.38564`, span hard failures `7/8`, gate `retake_required: 5`, `repair_candidate: 2`, `no_repair_needed: 1`.

2. `Wan2.1-Fun-1.3B-Control`, `controlnet`, `steps=16`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_steps16_20260611_132403`
   - Span: `outputs_span_selection/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_steps16_span_20260611_132435`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_steps16_gate_20260611_132501`
   - Result: worsened. Span score `0.44694`, span hard failures `7/8`, gate `retake_required: 6`, `repair_candidate: 2`.

3. Source-pose ankle-separation filter
   - Template: `outputs_motion_source_video_pdca/run_mixkit_walk_source_crop480_ankle_sep06`
   - Import setting: `--min-ankle-x-separation 0.06`
   - Retained source indices: `3, 5, 6, 7, 8, 11, 12, 14, 16`
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_1p3b_ankle_sep06_20260611_132814`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_1p3b_ankle_sep06_gate_20260611_132907`
   - Result: failed. Gate stayed `retake_required: 8/8`.

4. `Wan2.1-Fun-14B-Control`, `controlnet`
   - Installed model: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/models/diffusion_models/Wan2.1-Fun-14B-Control.safetensors`
   - Size: `32790385576` bytes
   - Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_fun_control_14b_controlnet_20260611_135226`
   - Span: `outputs_span_selection/run_motion_source_mixkit_walk_fun_control_14b_controlnet_span_20260611_135317`
   - Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_fun_control_14b_controlnet_gate_20260611_135345`
   - Result: not better than 1.3B. Span score `0.47254`, span hard failures `5/8`, gate `retake_required: 5`, `repair_candidate: 1`, `no_repair_needed: 2`.

Updated conclusion:

- The best FunControl result remains the 1.3B `controlnet` render trial: `review_packages/run_motion_source_mixkit_walk_fun_control_1p3b_controlnet_review_20260611_131553`.
- Bigger FunControl alone did not solve duplicate silhouettes for this walking source.
- Thin control lines and leg-crossing source-frame removal did not solve the current failure.
- Next likely productive branch is a cleaner full-body source-video family with less occluding/crossing lower-body motion, or a different local video workflow that separates subject appearance from motion more strongly.

Additional external reference:

- Hugging Face model file used for the local 14B probe: `https://huggingface.co/alibaba-pai/Wan2.1-Fun-14B-Control/blob/main/diffusion_pytorch_model.safetensors`

## Follow-Up: Source Probe Packaging And Mixkit 35419 Rejection

Implemented source-candidate packaging:

- Script: `scripts/export_source_probe_package.py`
- Test: `tests/test_source_probe_package.py`
- Purpose: keep each source-motion candidate reviewable before more generation cycles by bundling source contact sheet, SDPose report, imported control contact sheet, span/gate reports, comparison sheet, metrics, and accept/reject reasons.

Mixkit 35419 diagnostic:

- Source clip: `assets/source_motion/mixkit_35419_walk_source_512_8fps.mp4`
- Source probe: `assets/source_motion/mixkit_35419_walk_source_512_8fps_probe.jpg`
- SDPose report: `outputs_sdpose_video_json_probe/mixkit_35419_walk_source_20260611_135947/sdpose_video_json_probe_report.json`
- High-confidence import: `outputs_motion_source_video_pdca/run_mixkit_35419_walk_source_filtered`
- High-confidence import kept only `4` source frames, so it was too sparse for a reusable walk control.
- Lower-confidence diagnostic import: `outputs_motion_source_video_pdca/run_mixkit_35419_walk_source_conf25`
- Lower-confidence diagnostic retained source indices `12, 13, 17, 18, 19, 21, 22, 23`
- Mean confidence: `0.37371`

Generation diagnostic:

- Route: `WanAnimateToVideo`
- Output: `outputs_next_phase_pdca/run_motion_source_mixkit_35419_conf25_animate_20260611_140336`
- Span: `outputs_span_selection/run_motion_source_mixkit_35419_conf25_animate_span_20260611_140438`
- Gate: `outputs_artifact_repair/run_motion_source_mixkit_35419_conf25_animate_gate_20260611_140459`
- Source probe package: `source_probe_packages/mixkit_35419_walk_source_conf25_20260611_140714`
- Span score: `0.28623`
- Span hard failures: `5/8`
- Gate: `retake_required: 6`, `repair_candidate: 1`, `no_repair_needed: 1`
- Main issues: `masked_ghost_or_small_artifact: 7`, `duplicate_silhouette_area_high: 4`, `strong_duplicate_silhouette_risk: 3`, `double_foot_or_duplicate_leg_risk: 2`

Verdict:

- Rejected. Although the visible source video looked like a side-view walk, the pose extraction was too weak and generation produced background drift, strong lower-body afterimages, and unstable silhouette frames.
- It is worse than the current best clean-source baseline (`retake_required: 1/8`): 35419 produced `retake_required: 6/8`, so the branch is closed.
- This validates the new rule: a candidate that cannot keep enough high-confidence full-body pose frames should be packaged as negative evidence and stopped early instead of entering repeated seed/prompt search.

## Follow-Up: Wan Continue-Motion Reduction PDCA

Reason:

- The best clean-source walk baseline was close but still blocked by one structural retake frame.
- This branch tested a generation-control change rather than prompt-only tuning: reduce `WanAnimateToVideo` `continue_motion_max_frames` from the default `5` to `1`, aiming to reduce latent carryover and pale leg afterimages.

Trial 1:

- Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_cont1_20260611_141021`
- Span: `outputs_span_selection/run_motion_source_mixkit_walk_cont1_span_20260611_141103`
- Gate: `outputs_artifact_repair/run_motion_source_mixkit_walk_cont1_gate_20260611_141125`
- Review package: `review_packages/run_motion_source_mixkit_walk_cont1_review_20260611_141400`
- Godot validation: `ok: true`
- Motion metrics: mean frame delta `8.136`
- Span score: `0.83364`
- Span hard failures: `1/8`
- Gate: `no_repair_needed: 3`, `repair_candidate: 4`, `retake_required: 1`
- Mean mask coverage: `0.00089`
- Main remaining issue: `duplicate_silhouette_area_high: 1`

Trial 2:

- Output: `outputs_next_phase_pdca/run_motion_source_mixkit_walk_cont1_seed203_20260611_141250`
- Span: `outputs_span_selection/run_motion_source_mixkit_walk_cont1_seed203_span_20260611_141331`
- Motion metrics: mean frame delta `33.157`
- Span score: `0.41774`
- Span hard failures: `6/8`
- Verdict: rejected without further packaging.

Verdict:

- `continue_motion_max_frames=1` is a useful candidate setting but not a complete solution. The best trial stayed at the previous blocking level of `retake_required: 1/8`, with much smaller masks and a high span score.
- Seed sensitivity remains high. The second seed collapsed to `hard_failures: 6/8`, so this should not be treated as a robust adoption setting yet.
- Next useful branch should target the last residual duplicate silhouette directly: either stronger foreground/background separation in the start/control pair, a synthetic clean side-view pose source, or a local video workflow with stronger subject/motion separation.

## Follow-Up: Synthetic Side-View Motion Source PDCA

Reason:

- External source-video candidates can fail before generation because SDPose confidence is weak, the actor is not full-body enough, or background/occlusion leaks into motion control.
- A synthetic side-view source isolates whether residual leg artifacts come from source-pose noise or from Wan generation/appearance preservation.

Implemented:

- Script: `scripts/build_synthetic_sideview_motion_source.py`
- Test: `tests/test_synthetic_sideview_motion_source.py`
- Output template: `outputs_motion_source_video_pdca/run_synthetic_sideview_walk_v1`
- Source probe package: `source_probe_packages/synthetic_sideview_walk_v1_gate_v3_20260611_142621`
- The synthetic template writes 120 local pose frames, `controlnet/*.png`, `contact_sheet.png`, and `motion_source_report.json`.
- A test enforces that ankle X separation does not collapse below the local threshold, so the control source does not encode a leg-crossing failure.

Generation trial:

- Route: `WanAnimateToVideo`
- Pose style: `wan_confidence_lower`
- `continue_motion_max_frames`: `1`
- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v1_cont1_20260611_141825`
- Span: `outputs_span_selection/run_synthetic_sideview_walk_v1_cont1_span_20260611_141917`
- Corrected gate: `outputs_artifact_repair/run_synthetic_sideview_walk_v1_cont1_gate_v3_20260611_142509`
- Review package: `review_packages/run_synthetic_sideview_walk_v1_cont1_gate_v3_review_20260611_142608`
- Godot validation: `ok: true`

Results:

- Span score: `0.80104`
- Span hard failures before artifact gate: `0/8`
- Corrected artifact gate: `retake_required: 3`, `repair_candidate: 5`
- Main issue: `repair_mask_too_large: 3`
- Mean mask coverage: `0.24748`

Gate fix:

- Problem found: broad repair masks were only converted to retake blockers in the inpaint path. In `--mask-only` runs, broad masks could remain `repair_candidate`, making the quality gate too optimistic.
- Fix: `repair_mask_too_large` is now assigned inside `_analyze_frame` and is a hard issue code.
- Recommendation now returns `retake_or_retrim_span_before_refine` when `retake_required` appears.
- Test: `tests/test_artifact_repair_script.py`

Secondary trial:

- Route: same synthetic source, pose style `wan_lower`
- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v1_wanlower_cont1_20260611_142055`
- Span: `outputs_span_selection/run_synthetic_sideview_walk_v1_wanlower_cont1_span_20260611_142135`
- Result: rejected. Span score `0.31706`, hard failures `7/8`.

Verdict:

- Synthetic clean motion proves that cleaner lower-body control can reduce selected-span structural failures. This is useful evidence.
- It is not adoption-grade. Visual review shows a dark, silhouette-like character and broad mask failures after the corrected gate.
- The next local-control branch should preserve the lower-body cleanliness while improving appearance retention: stronger subject/reference conditioning, brighter synthetic control balance, or a workflow with stronger subject/motion separation.

## Follow-Up: Synthetic Appearance-Retention Attempts

Goal:

- Preserve the synthetic source's lower-body cleanliness while restoring character brightness, face/outfit readability, and clean white background.

Implemented:

- Added pose render style: `wan_balanced`
- Files: `src/natural_sprite_lab/pose_templates.py`, `scripts/run_wan_walk_i2v.py`, `scripts/import_motion_source_pose.py`, `scripts/build_synthetic_sideview_motion_source.py`
- Test: `tests/test_pose_templates.py`
- Purpose: create a middle route between weak `wan_confidence_lower` and over-strong `wan_lower`.

Trial 1: `wan_balanced`, 17 frames

- Template: `outputs_motion_source_video_pdca/run_synthetic_sideview_walk_v1_balanced`
- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v1_balanced_cont1_20260611_143154`
- Span: `outputs_span_selection/run_synthetic_sideview_walk_v1_balanced_cont1_span_20260611_143236`
- Gate: `outputs_artifact_repair/run_synthetic_sideview_walk_v1_balanced_cont1_gate_20260611_143314`
- Source probe package: `source_probe_packages/synthetic_sideview_walk_v1_balanced_len33_20260611_143703`
- Result: rejected. Span `hard_failures: 3/8`; gate `retake_required: 3/8`.
- Finding: brightness and mask coverage improved, but duplicate silhouette and double-foot risks returned.

Trial 2: `wan_balanced`, 33 frames

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v1_balanced_cont1_len33_20260611_143423`
- Span: `outputs_span_selection/run_synthetic_sideview_walk_v1_balanced_cont1_len33_span_20260611_143532`
- Gate: `outputs_artifact_repair/run_synthetic_sideview_walk_v1_balanced_cont1_len33_gate_20260611_143608`
- Result: rejected. Motion was numerically stable (`mean_frame_delta: 8.036`), but selected span stayed at `hard_failures: 4/8` and gate `retake_required: 4/8`.
- Finding: generating more frames did not recover a clean 8-frame contiguous span for this style.

Trial 3: bright appearance prompt with original `wan_confidence_lower`

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v1_bright_prompt_cont1_20260611_143728`
- Span: `outputs_span_selection/run_synthetic_sideview_walk_v1_bright_prompt_cont1_span_20260611_143816`
- Gate before cleanup: `outputs_artifact_repair/run_synthetic_sideview_walk_v1_bright_prompt_cont1_gate_20260611_143842`
- Cleanup: `outputs_mask_cleanup/run_synthetic_sideview_walk_v1_bright_prompt_white_cleanup_20260611_144006`
- Gate after cleanup: `outputs_artifact_repair/run_synthetic_sideview_walk_v1_bright_prompt_white_cleanup_gate_20260611_144037`
- Source probe package: `source_probe_packages/synthetic_sideview_walk_v1_bright_prompt_cleanup_20260611_144142`
- Result: rejected. Bright prompt gate was `retake_required: 8/8` with broad masks. Deterministic white cleanup created white holes and still failed `retake_required: 8/8`.

Trial 4: small `character_mask` with original `wan_confidence_lower`

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v1_mask_cont1_20260611_144343`
- Span: `outputs_span_selection/run_synthetic_sideview_walk_v1_mask_cont1_span_20260611_144433`
- Gate: `outputs_artifact_repair/run_synthetic_sideview_walk_v1_mask_cont1_gate_20260611_144459`
- Source probe package: `source_probe_packages/synthetic_sideview_walk_v1_character_mask_20260611_144558`
- Result: rejected. Span `hard_failures: 8/8`, gate `retake_required: 8/8`.
- Main issues: `foreground_too_small: 8`, `upper_body_center_shift_high: 7`, `repair_mask_too_large: 2`.
- Finding: `character_mask` again acted as a destabilizer in this setup rather than a reliable subject-preservation mechanism.

Trial 5: connected-background normalization postprocess

- Script: `scripts/normalize_connected_background.py`
- Test: `tests/test_background_normalize_script.py`
- Input: `outputs_span_selection/run_synthetic_sideview_walk_v1_bright_prompt_cont1_span_20260611_143816/selected_frames`
- Output: `outputs_background_normalize/run_synthetic_sideview_walk_v1_bright_prompt_bg_normalize_wide_20260611_145045`
- Gate: `outputs_artifact_repair/run_synthetic_sideview_walk_v1_bright_prompt_bg_normalize_wide_gate_20260611_145109`
- Source probe package: `source_probe_packages/synthetic_sideview_walk_v1_background_normalize_20260611_145225`
- Result: rejected. Gate stayed `retake_required: 8/8`.
- Main issues: `foreground_too_large: 8`, `duplicate_silhouette_area_high: 8`, `background_contamination_high: 8`, `repair_mask_too_large: 8`.
- Finding: connected-background normalization is safer than artifact-mask white cleanup for simple border-connected backgrounds, but it cannot fix this bright-prompt result because the background contamination is entangled with the character silhouette.

Trial 6: person-cutout background replacement

- Script: `scripts/person_cutout_background.py`
- Test: `tests/test_person_cutout_background_script.py`
- Input: `outputs_span_selection/run_synthetic_sideview_walk_v1_bright_prompt_cont1_span_20260611_143816/selected_frames`
- Output: `outputs_person_cutout_background/run_synthetic_sideview_walk_v1_bright_prompt_person_cutout_very_strict_20260611_145812`
- Gate: `outputs_artifact_repair/run_synthetic_sideview_walk_v1_bright_prompt_person_cutout_very_strict_gate_20260611_145844`
- Source probe package: `source_probe_packages/synthetic_sideview_walk_v1_person_cutout_background_20260611_145958`
- Result: rejected. Gate stayed `retake_required: 8/8`.
- Main issues: `foreground_too_large: 8`, `duplicate_silhouette_area_high: 8`, `background_contamination_high: 8`, `repair_mask_too_large: 8`.
- Finding: largest-person-component cutout still retains the gray character-connected shadow/background mass. Simple deterministic postprocess segmentation is not enough for this failure.

Updated conclusion:

- The next route should not simply strengthen pose lines or brighten text prompts.
- The useful target is now narrower: preserve appearance with a subject/reference mechanism other than the current Wan `character_mask`, while keeping synthetic lower-body control weak enough to avoid duplicate legs.
- Broad background cleanup remains blocked unless it is driven by a better foreground/person segmentation mask than the artifact mask, simple border-connected background estimation, or largest-component person cutout.

## Follow-Up: Local BiRefNet Foreground Separation

Reason:

- Deterministic connected-background and largest-component cutout failed on the bright-prompt synthetic walk because the blue-gray background contamination was entangled with the character silhouette.
- The next local-first recovery branch was to use a stronger local foreground segmentation model, not another broad cleanup mask.

Model setup:

- Model: `birefnet.safetensors`
- Installed path: `C:\LocalWork\StabilityMatrix\Data\Packages\ComfyUI\models\background_removal\birefnet.safetensors`
- ComfyUI nodes: `LoadBackgroundRemovalModel -> RemoveBackground -> MaskToImage`
- Source reference: ComfyUI's BiRefNet background-removal tutorial documents that the model belongs under `ComfyUI/models/background_removal/` and outputs a foreground mask.

Implemented:

- Script: `scripts/birefnet_foreground_masks.py`
- Test: `tests/test_birefnet_foreground_masks_script.py`
- Output per run: foreground masks, RGBA frames, white-composited frames, contact sheets, preview GIF, workflow JSON, and `birefnet_foreground_report.json`.

Trial 1: synthetic bright-prompt selected walk span

- Input: `outputs_span_selection/run_synthetic_sideview_walk_v1_bright_prompt_cont1_span_20260611_143816/selected_frames`
- BiRefNet output: `outputs_birefnet_foreground/synthetic_sideview_walk_v1_bright_prompt_birefnet_20260611_151117`
- Gate: `outputs_artifact_repair/synthetic_sideview_walk_v1_bright_prompt_birefnet_gate_20260611_151131`
- Review package: `review_packages/synthetic_sideview_walk_v1_bright_prompt_birefnet_review_20260611_151420`
- Godot validation: `ok: true`

Results:

- BiRefNet summary: `mask_ok: 8/8`, mean foreground coverage `0.09665`, mean mask delta `0.0027`.
- Artifact gate after white compositing: `no_repair_needed: 8/8`, no issue codes.
- Visual review: background/afterimage contamination was greatly reduced, and the contact sheet reads as a coherent side-view walk pose sequence.

Limitation:

- The selected 8-frame span has modest leg travel. It is a promising candidate/proof of segmentation quality, not yet a 120-frame adoption-grade animation asset.
- A high gate score after BiRefNet is not enough; motion readability still needs playback/contact-sheet review.

Trial 2: current Mixkit clean-source baseline

- Input: `review_packages/run_motion_source_mixkit_walk_cont1_review_20260611_141400/frames`
- BiRefNet output: `outputs_birefnet_foreground/mixkit_walk_cont1_birefnet_20260611_151245`
- Gate: `outputs_artifact_repair/mixkit_walk_cont1_birefnet_gate_20260611_151258`

Results:

- BiRefNet summary: `mask_ok: 8/8`, mean foreground coverage `0.09489`, mean mask delta `0.02998`.
- Artifact gate improved background cleanliness but still reported `repair_candidate: 1` and visual review still showed body-internal leg/arm afterimages.

Conclusion:

- BiRefNet is useful for local subject/background separation and should replace simple deterministic background cleanup when background drift is the main failure.
- BiRefNet does not solve structural duplicate limbs when the bad limb/afterimage is inside the foreground mask. Those failures must still return to motion control, source selection, span selection, or generation settings.
- Next action: integrate BiRefNet mask stability into span scoring, then run a longer 120-frame synthetic bright-prompt/BiRefNet candidate and judge motion readability before calling it an asset.

Follow-up scoring guard:

- `scripts/select_best_span.py` now accepts `--foreground-mask-dir`, `--min-mean-motion-delta`, and `--max-mean-foreground-mask-delta`.
- Re-score output: `outputs_span_selection/synthetic_sideview_walk_v1_birefnet_motion_gate_20260611_151855`
- Result: hard failures `0/8`, mean foreground mask delta `0.0027`, but mean motion delta only `1.134`.
- Selection penalty: `mean_motion_delta_too_low`.

This keeps the BiRefNet result honest: it is a clean candidate/proof, but the current 8-frame span should not be promoted to adoption-grade walking animation without a longer/more readable motion pass.

## Follow-Up: 121-Frame Synthetic Bright-Prompt/BiRefNet Trial

Reason:

- The prior 8-frame BiRefNet candidate was visually clean but failed the new motion-readability guard with `mean_motion_delta_too_low`.
- The user goal is high-quality 120-frame source generation, with thinning/export as a later Skill. This trial tested whether a longer Wan generation could provide enough motion while retaining the BiRefNet background-separation benefit.

Generation:

- Route: `WanAnimateToVideo`
- Length: `121`
- Source template: `outputs_motion_source_video_pdca/run_synthetic_sideview_walk_v1`
- Pose render style: `wan_confidence_lower`
- `continue_motion_max_frames`: `1`
- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v1_bright_prompt_cont1_len121_20260611_152136`
- Mean frame delta: `4.999`

BiRefNet foreground separation:

- Output: `outputs_birefnet_foreground/synthetic_sideview_walk_v1_bright_prompt_len121_birefnet_20260611_152636`
- Result: `mask_ok: 121/121`
- Mean foreground coverage: `0.09089`
- Mean mask delta: `0.02945`

Motion-aware span selection:

- Output: `outputs_span_selection/synthetic_sideview_walk_v1_bright_prompt_len121_birefnet_motion_gate_20260611_152759`
- Selected span: frames `88..103`
- Span length: `16`
- Score: `0.88295`
- Hard failures: `0/16`
- Mean motion delta: `7.484`
- Mean foreground mask delta: `0.02954`
- Selection penalties: none

Artifact gate:

- Output: `outputs_artifact_repair/synthetic_sideview_walk_v1_bright_prompt_len121_birefnet_gate_20260611_152958`
- Result: `no_repair_needed: 16/16`

Manual/agent visual review:

- The selected span is motion-readable, but not adoption-grade.
- Several frames show mesh-like legs, bag-like lower-body silhouettes, or internally smeared lower limbs.
- This is a foreground-internal structural failure: the broken shape is inside the BiRefNet foreground mask, so background removal cannot fix it.

Gate improvement:

- `scripts/birefnet_foreground_masks.py` now reports `foreground_bbox_fill`, `lower_body_max_width_ratio`, and `lower_body_mean_width_ratio`.
- It can return review gates such as `review_sparse_foreground_bbox` and `review_lower_body_silhouette_wide`.
- Recheck output: `outputs_birefnet_foreground/synthetic_sideview_walk_v1_len121_selected_birefnet_structure_gate_20260611_153418`
- Result: `mask_ok: 13`, `review_sparse_foreground_bbox: 3`

Review package:

- `review_packages/synthetic_sideview_walk_v1_bright_prompt_len121_birefnet_review_v2_20260611_153539`
- Godot validation: `ok: true`

Conclusion:

- The longer run solved the previous low-motion problem, but exposed a new structural weakness: Wan preserves a readable walk cycle while deforming the lower body into unstable foreground shapes.
- Existing artifact repair metrics were too optimistic after BiRefNet compositing. The new BiRefNet structure metrics reduce this risk but are still not a full substitute for visual review.
- Next useful branch should target generation-time lower-body structure: stronger pose/appearance disentanglement, lower-body-specific control, or a source/control representation that prevents skirt/leg mass from fusing.

## Follow-Up: Lower-Stride Synthetic Control PDCA

Reason:

- The 121-frame v1 branch had enough motion but produced mesh-like or bag-like lower-body silhouettes.
- A smaller stride/lift synthetic source tests whether reducing lower-body deformation pressure improves the result without relying on cleanup.

Implemented:

- Synthetic template: `outputs_motion_source_video_pdca/run_synthetic_sideview_walk_v2_lower_stride`
- Settings: `stride: 0.075`, `lift: 0.035`, `body_bob: 0.012`

Trial 1: lower stride with weak `wan_confidence_lower`

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_bright_prompt_cont1_len121_20260611_153825`
- Result: rejected as a diagnostic. The generated frames were byte-identical to the v1 121-frame run under the same seed/settings.
- Control images were slightly different, but weak control did not affect the final Wan output enough.

Trial 2: lower stride with stronger `wan_balanced`

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_wan_balanced_len33_20260611_154400`
- BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v2_lower_stride_wan_balanced_len33_birefnet_20260611_154534`
- Span: `outputs_span_selection/synthetic_sideview_walk_v2_lower_stride_wan_balanced_birefnet_motion_gate_20260611_154612`
- Gate: `outputs_artifact_repair/synthetic_sideview_walk_v2_lower_stride_wan_balanced_birefnet_gate_20260611_154709`
- Structure recheck: `outputs_birefnet_foreground/synthetic_sideview_walk_v2_lower_stride_wan_balanced_selected_structure_gate_20260611_154840`
- Review package: `review_packages/synthetic_sideview_walk_v2_lower_stride_wan_balanced_review_20260611_154913`
- Godot validation: `ok: true`

Results:

- Selected span: frames `14..29`
- Span length: `16`
- Mean motion delta: `4.919`
- Mean foreground mask delta: `0.02069`
- Artifact gate: `no_repair_needed: 16/16`
- BiRefNet selected-span structure gate: `mask_ok: 9`, `review_sparse_foreground_bbox: 7`

Visual review:

- This is visibly better than the 121-frame v1 selected span. The legs read more like legs, and the strongest bag-like silhouette failure is reduced.
- It is still not adoption-grade. A few frames retain foot/leg color ghosts, sparse lower-body silhouettes, and mild hand/arm smearing.

Conclusion:

- Lower-stride control is useful only when the control render is strong enough to influence Wan. With `wan_confidence_lower`, the pose change was effectively ignored.
- `wan_balanced` + lower stride is the current best synthetic/local control branch, but it remains `needs_manual_review`, not `adoptable`.
- The next branch should either strengthen lower-body structure without reintroducing duplicate silhouettes, or add a generation-time subject/motion split stronger than current WanAnimate pose input.

## Follow-Up: BiRefNet Mask As Wan Character Mask Rejection

Reason:

- BiRefNet is now useful as a local subject/background separation and evaluation tool.
- This branch tested whether the same foreground mask could improve generation-time subject/background separation through `WanAnimateToVideo`'s `character_mask` input.

Mask setup:

- Start frame: `outputs_next_phase_startframe/auto_cleaned_run_strong_pose_20260611_032832/start_frame.png`
- BiRefNet mask output: `outputs_birefnet_foreground/start_frame_birefnet_character_mask_20260611_155239`
- Mask gate: `review_sparse_foreground_bbox: 1`

Generation:

- Route: `WanAnimateToVideo`
- Base settings: same as the current best lower-stride + `wan_balanced` diagnostic branch.
- Difference: `--character-mask outputs_birefnet_foreground/start_frame_birefnet_character_mask_20260611_155239/foreground_masks/foreground_mask_000.png`
- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_wan_balanced_birefnet_char_mask_len33_20260611_155309`
- Motion metrics: mean frame delta `4.465`

Evaluation:

- Post BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v2_wan_balanced_birefnet_char_mask_len33_post_birefnet_20260611_155513`
- Span: `outputs_span_selection/synthetic_sideview_walk_v2_wan_balanced_birefnet_char_mask_motion_gate_20260611_155550`
- Gate: `outputs_artifact_repair/synthetic_sideview_walk_v2_wan_balanced_birefnet_char_mask_gate_20260611_155629`
- Review package: `review_packages/synthetic_sideview_walk_v2_wan_balanced_birefnet_char_mask_reject_review_20260611_155811`
- Godot validation: `ok: true`

Results:

- Span selected frames `15..30`, but mean motion delta fell to `3.165`.
- Selection penalty: `mean_motion_delta_too_low`.
- Artifact gate again reported `no_repair_needed: 16/16`, but visual review showed blurry silhouette-like frames and brown/yellow background drift.

Conclusion:

- BiRefNet masks should not be used as WanAnimate `character_mask` in the current workflow. They are useful after generation for compositing/evaluation, but as generation input they pushed Wan toward low-detail silhouettes and weak motion.
- This closes the simple generation-time mask route. The next subject/motion split needs a different mechanism, such as a workflow with explicit reference/motion disentanglement or a control route that keeps appearance separate from pose without masking away detail.

## Follow-Up: Lower-Stride Synthetic FunControl Comparison

Reason:

- The earlier FunControl branch failed on Mixkit-derived source motion with duplicate silhouettes.
- The lower-stride synthetic source reduced deformation pressure in the `WanAnimateToVideo` branch, so it was tested as a cleaner FunControl source/control candidate.

Trial 1: FunControl 1.3B + `controlnet`

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_fun_control_1p3b_controlnet_len33_20260611_160143`
- BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v2_fun_control_1p3b_controlnet_len33_birefnet_20260611_160305`
- Span: `outputs_span_selection/synthetic_sideview_walk_v2_fun_control_1p3b_controlnet_birefnet_motion_gate_v2_20260611_160519`
- Gate: `outputs_artifact_repair/synthetic_sideview_walk_v2_fun_control_1p3b_controlnet_birefnet_gate_20260611_160600`
- Review package: `review_packages/synthetic_sideview_walk_v2_fun_control_1p3b_controlnet_reject_review_20260611_160739`
- Godot validation: `ok: true`

Results:

- Contact sheet looked cleaner as still frames than earlier Mixkit FunControl.
- Span hard failures: `16/16`
- Span mean motion delta: `2.038`
- Selection penalty: `mean_motion_delta_too_low`
- Artifact gate: `retake_required: 16/16`
- Main issues: `duplicate_silhouette_area_high: 16`, `double_foot_or_duplicate_leg_risk: 8`, `lower_body_blob_count_high: 8`

Trial 2: FunControl 1.3B + `wan_balanced`

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_fun_control_1p3b_wan_balanced_len33_20260611_160804`
- BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v2_fun_control_1p3b_wan_balanced_len33_birefnet_20260611_160909`
- Span: `outputs_span_selection/synthetic_sideview_walk_v2_fun_control_1p3b_wan_balanced_birefnet_motion_gate_20260611_160946`
- Gate: `outputs_artifact_repair/synthetic_sideview_walk_v2_fun_control_1p3b_wan_balanced_birefnet_gate_20260611_161029`
- Review package: `review_packages/synthetic_sideview_walk_v2_fun_control_1p3b_wan_balanced_reject_review_20260611_161208`
- Godot validation: `ok: true`

Results:

- Visual result became more front-facing/static and less like a walk cycle.
- Span hard failures: `1/16`
- Span mean motion delta: `1.798`
- Selection penalty: `mean_motion_delta_too_low`
- Artifact gate: `retake_required: 1/16`

Conclusion:

- Lower-stride synthetic control did not rescue FunControl for walk adoption.
- `controlnet` preserves attractive still-frame character quality but still fails walk animation gates.
- `wan_balanced` reduces artifact counts but collapses motion/readability into near-static poses.
- Current best synthetic/local walk branch remains `WanAnimateToVideo + lower-stride source + wan_balanced + BiRefNet post-separation`, not FunControl.

## Follow-Up: Clean-Source Walk 0-Retake Recheck

Reason:

- The best clean-source walk baseline previously had artifact `retake_required: 1/8`.
- BiRefNet post-separation appeared to reduce background drift, but that result predated the foreground-structure gate and motion-readability scoring changes.

Recheck:

- Input review package: `review_packages/run_motion_source_mixkit_walk_cont1_review_20260611_141400`
- BiRefNet rerun: `outputs_birefnet_foreground/mixkit_walk_cont1_birefnet_structure_gate_rerun_20260611_161620`
- Motion-aware span: `outputs_span_selection/mixkit_walk_cont1_birefnet_structure_motion_gate_rerun_20260611_161642`
- Artifact gate: `outputs_artifact_repair/mixkit_walk_cont1_birefnet_structure_gate_rerun_20260611_161707`
- Review package: `review_packages/mixkit_walk_cont1_birefnet_0retake_manual_review_20260611_161805`
- Godot validation: `ok: true`

Results:

- BiRefNet structure gate: `mask_ok: 4`, `review_sparse_foreground_bbox: 4`
- Span hard failures: `0/8`
- Mean motion delta: `6.001`
- Mean foreground mask delta: `0.02998`
- Artifact gate: `no_repair_needed: 7`, `repair_candidate: 1`, `retake_required: 0`

Visual review:

- Background color drift is substantially reduced.
- The contact sheet still shows foreground-internal leg/arm afterimages and pale ghosting in several frames.
- Because those artifacts are inside the foreground mask, BiRefNet cannot be considered a full structural repair.

Conclusion:

- The source-video walk checklist item `retake_required: 0/8` is now satisfied by the artifact gate.
- The result remains `manual_review`, not `adoptable`. The next quality jump must target foreground-internal motion/appearance structure, not background cleanup.

## Follow-Up: VACE Subject/Motion Split And Foreground-Normalized Motion

Reason:

- FunControl and `WanAnimateToVideo` had both stalled on the same quality boundary: either the walk was readable but the foreground contained internal afterimages, or the result became clean but too static.
- VACE was tested as a local subject/motion split route because it accepts a reference image plus a control video, which matches the project goal better than prompt-only animation.

Implementation:

- Installed model: `C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/models/diffusion_models/wan2.1_vace_1.3B_fp16.safetensors`
- Script: `scripts/run_wan_walk_i2v.py`
- Added mode: `--mode vace`
- Added tuning parameter: `--vace-strength`
- Added diagnostic control render styles: `vace_depth_proxy`, `vace_side_proxy`
- Added foreground-normalized motion scoring:
  - `FrameQuality.foreground_motion_delta_prev`
  - `scripts/select_best_span.py --motion-metric foreground`

Short VACE trials:

- `controlnet` output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_vace_1p3b_controlnet_len33_20260611_163218`
- `controlnet` BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v2_vace_1p3b_controlnet_len33_birefnet_20260611_163533`
- `controlnet` span: `outputs_span_selection/synthetic_sideview_walk_v2_vace_1p3b_controlnet_birefnet_motion_gate_20260611_163605`
- Result: rejected. It had clean still-frame identity but `hard_failures: 14/16` and `mean_motion_delta_too_low`.

- `wan_balanced` output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_vace_1p3b_wan_balanced_len33_20260611_163642`
- `wan_balanced` BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_len33_birefnet_20260611_163729`
- Global-motion span: `outputs_span_selection/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_birefnet_motion_gate_20260611_163800`
- Foreground-motion span: `outputs_span_selection/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_birefnet_foreground_motion_gate_v2_20260611_165311`
- Artifact gate: `outputs_artifact_repair/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_birefnet_foreground_motion_gate_20260611_165349`
- Review package: `review_packages/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_foreground_motion_review_20260611_165535`
- Godot validation: `ok: true`

Short-trial result:

- The global motion metric under-counted movement because the character is a small, thin full-body subject on a 512x512 white canvas.
- Foreground-normalized scoring raised the selected span motion evidence to `mean_motion_delta: 7.135`.
- Artifact gate found no retake blockers, but did mark `repair_candidate: 7/16`.
- Visual review: this is a better walk candidate than prior FunControl outputs, but still not adoption-grade because minor afterimages and foot overlap remain.

Rejected VACE diagnostics:

- Strong stride v1 with VACE `wan_balanced`: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v1_vace_1p3b_wan_balanced_len33_20260611_163843`
- VACE strength `1.35`: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_vace_1p3b_wan_balanced_strength135_len33_20260611_164122`
- `vace_depth_proxy`: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_vace_1p3b_depth_proxy_len33_20260611_164526`
- `vace_side_proxy`: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_vace_1p3b_side_proxy_len33_20260611_164825`

Conclusion for rejected diagnostics:

- Stronger stride/control can increase motion, but it quickly collapses character structure.
- The proxy controls are not adopted for this branch. VACE copied the simplified proxy/front-view structure into the character instead of treating it as pure motion/depth guidance.

121-frame VACE trial:

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v2_lower_stride_vace_1p3b_wan_balanced_len121_20260611_165634`
- BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_len121_birefnet_20260611_165918`
- Selected span: `outputs_span_selection/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_len121_birefnet_foreground_motion_gate_v3_20260611_170503`
- Artifact gate: `outputs_artifact_repair/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_len121_foreground_motion_gate_20260611_170650`
- Review package: `review_packages/synthetic_sideview_walk_v2_vace_1p3b_wan_balanced_len121_foreground_motion_review_20260611_170831`
- Godot validation: `ok: true`

121-frame results:

- BiRefNet structure summary: `mask_ok: 100/121`, `review_sparse_foreground_bbox: 21/121`
- Selected span: frames `38..53`
- Span hard failures: `0/16`
- Foreground-motion mean delta: `4.086`
- Foreground mask delta: `0.0017`
- Selection penalties: none with `--min-mean-motion-delta 4.0`
- Artifact gate: `repair_candidate: 16/16`, no retake-required summary code

Visual review:

- This is the cleanest local generated walk package so far: stable identity, clean white background, no obvious full-body duplicate silhouette, Godot playback loads.
- It is still `manual_review`, not `adoptable`. The walk amplitude is conservative, and the artifact mask detects small recurring fragments around the skirt/feet.

Next action:

- Improve the lower-stride synthetic trajectory or use a video-control workflow that accepts motion/depth without proxy leakage.
- Keep foreground-normalized motion scoring in the gate for small full-body sprites.
- Do not claim adoption until a 120-frame source run can produce a selected review package with readable walk amplitude and no recurring repair candidates.

## Follow-Up: Mid-Stride VACE Walk Amplitude Push

Reason:

- The v2 lower-stride VACE branch was the cleanest local walk package so far, but the selected span still had conservative walk amplitude.
- This branch tested whether a carefully increased synthetic stride could raise walk readability without returning to duplicate-foot or afterimage failures.

Trial 1: v3 mid-stride

- Motion source: `outputs_motion_source_video_pdca/run_synthetic_sideview_walk_v3_mid_stride`
- Settings: `stride=0.09`, `lift=0.042`, `body_bob=0.012`
- VACE output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v3_mid_stride_vace_1p3b_wan_balanced_len121_20260611_171321`
- BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v3_vace_1p3b_wan_balanced_len121_birefnet_20260611_171617`
- Span: `outputs_span_selection/synthetic_sideview_walk_v3_vace_1p3b_wan_balanced_len121_birefnet_foreground_motion_gate_20260611_171754`
- Artifact gate: `outputs_artifact_repair/synthetic_sideview_walk_v3_vace_1p3b_wan_balanced_len121_foreground_motion_gate_20260611_171941`

v3 result:

- Foreground motion improved slightly to `4.195`.
- Span hard failures stayed `0/16`.
- Artifact gate returned `retake_required: 3/16`.
- Visual review showed stronger lower-body/hem residual masks.
- Decision: reject v3. It proves stride can raise readability, but the margin over v2 was too small for the artifact cost.

Gate fix:

- The repair gate was over-counting normal lower-body structure: a skirt/hem component plus two feet could be counted as three lower-body blobs and marked as `double_foot_or_duplicate_leg_risk`.
- Updated both `src/natural_sprite_lab/quality/artifacts.py` and `scripts/repair_frame_artifacts.py` so foot-like blobs must reach the lower foot zone.
- Added tests so normal skirt plus two feet does not become a double-foot retake.

Trial 2: v4 edge-stride

- Motion source: `outputs_motion_source_video_pdca/run_synthetic_sideview_walk_v4_edge_stride`
- Settings: `stride=0.083`, `lift=0.038`, `body_bob=0.012`
- VACE output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v4_edge_stride_vace_1p3b_wan_balanced_len121_20260611_172226`
- BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v4_vace_1p3b_wan_balanced_len121_birefnet_20260611_172515`
- Span: `outputs_span_selection/synthetic_sideview_walk_v4_vace_1p3b_wan_balanced_len121_birefnet_foreground_motion_gate_20260611_172654`
- Artifact gate after gate fix: `outputs_artifact_repair/synthetic_sideview_walk_v4_vace_1p3b_wan_balanced_len121_foreground_motion_gate_v2_20260611_173416`
- Review package: `review_packages/synthetic_sideview_walk_v4_vace_1p3b_wan_balanced_len121_foreground_motion_review_20260611_173606`
- Godot validation: `ok: true`

v4 result:

- Selected span: frames `0..15`
- Span score: `0.94747`
- Span hard failures: `0/16`
- Foreground motion mean delta: `4.78`
- Foreground mask delta: `0.00232`
- Selection penalties: none
- Artifact gate: `no_repair_needed: 11`, `repair_candidate: 5`, `retake_required: 0`
- Artifact recommendation: `no_repair_needed_or_mask_threshold_too_strict`

Conclusion:

- v4 is the current best local VACE walk candidate. It improves walk amplitude over v2 while keeping retake-required frames at zero after correcting the normal-walk lower-body gate.
- It is still `manual_review`, not adopted. The next quality push should target identity/style preservation, especially the head/hair silhouette and side-profile consistency, without reducing walk readability.

## Follow-Up: Identity-Prompt V4 Walk Refinement

Reason:

- The v4 edge-stride candidate improved walk amplitude and cleared retake-required artifact gates, but visual review showed head/hair/side-profile drift in the selected span.
- The start image itself had good uncovered brown bob hair and a clear side profile, so this branch tested prompt-level identity reinforcement without changing the motion source.

Identity prompt changes:

- Added positives: `uncovered brown bob hair`, `pink hair clip`, `navy sailor school uniform`, `red necktie`, `strict side profile facing right`.
- Added negatives: `hat`, `cap`, `hood`, `head scarf`, `white headgear`, `helmet`.

Trial 1: identity prompt with new seed

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v4_edge_stride_vace_1p3b_wan_balanced_identity_prompt_len121_20260611_173910`
- BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v4_identity_prompt_vace_1p3b_wan_balanced_len121_birefnet_20260611_174200`
- Span: `outputs_span_selection/synthetic_sideview_walk_v4_identity_prompt_vace_1p3b_wan_balanced_len121_birefnet_foreground_motion_gate_20260611_174347`

Result:

- Visual identity improved: the white headgear artifact disappeared.
- Foreground motion dropped to `3.213`.
- Selection penalty: `mean_motion_delta_too_low`.
- Decision: reject this seed as too low-motion.

Trial 2: identity prompt with the previous successful seed

- Output: `outputs_next_phase_pdca/run_synthetic_sideview_walk_v4_edge_stride_vace_1p3b_wan_balanced_identity_prompt_seed717220_len121_20260611_174549`
- BiRefNet: `outputs_birefnet_foreground/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_1p3b_wan_balanced_len121_birefnet_20260611_174843`
- Span: `outputs_span_selection/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_1p3b_wan_balanced_len121_birefnet_foreground_motion_gate_20260611_175031`
- Artifact gate: `outputs_artifact_repair/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_1p3b_wan_balanced_len121_foreground_motion_gate_20260611_175222`
- Review package: `review_packages/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_foreground_motion_review_20260611_175401`
- Godot validation: `ok: true`

Result:

- Selected span: frames `0..15`
- Span score: `0.94198`
- Span hard failures: `0/16`
- Foreground motion mean delta: `4.993`
- Foreground mask delta: `0.00229`
- Selection penalties: none
- Artifact gate: `no_repair_needed: 12`, `repair_candidate: 4`, `retake_required: 0`
- Artifact recommendation: `no_repair_needed_or_mask_threshold_too_strict`

Conclusion:

- The same-seed identity prompt run is now the best local walk evidence.
- It improves identity/style preservation while preserving or slightly improving foreground motion versus the previous v4 selected span.
- It remains `manual_review` rather than adopted because the proof package is still a selected 16-frame span from a 121-frame source. The next step is to validate the full 121-frame output as a continuous source asset before moving on to weapon actions.

## Follow-Up: Full 121-Frame Walk Source Gate

Reason:

- The project target is a 120-frame-class source generation. The 16-frame span package is useful review evidence, but it is not enough to claim the full output is an adopted source asset.

Full-sequence gate:

- Input: `outputs_birefnet_foreground/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_1p3b_wan_balanced_len121_birefnet_20260611_174843/frames`
- Gate: `outputs_artifact_repair/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_full_sequence_gate_20260611_175642`

Result:

- Frame count: `121`
- Artifact gate: `no_repair_needed: 100`, `repair_candidate: 19`, `retake_required: 2`
- Retake frames: `65`, `116`
- Retake issue: `duplicate_silhouette_area_high`
- Mean mask coverage: `0.00016`

Conclusion:

- The full source is close, but not adopted.
- The walk workflow should now converge around the two full-sequence retake frames rather than expanding broad new PDCA branches.
- `Tasks.md` has been reduced to a convergence checklist; detailed PDCA evidence should remain in this report.

## Follow-Up: Full 121-Frame Gate Convergence

Reason:

- The two full-sequence retake frames were visually not strong duplicate silhouettes. Their repair mask coverage was `0.0`; the retake came from the quality duplicate-silhouette metric only.
- The quality metric protected dark/core subject pixels, but not warm light skin/hair pixels, so normal body regions could be counted as duplicate silhouette area.

Fix:

- Updated `src/natural_sprite_lab/quality/artifacts.py` to protect warm light subject pixels when computing duplicate-silhouette area.
- Kept duplicate detection intact for cool/gray ghost silhouettes.
- Added tests for normal skirt/two-foot frames and light skin protection.

Recheck:

- Gate: `outputs_artifact_repair/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_full_sequence_gate_v2_20260611_181716`
- Result: `no_repair_needed: 102`, `repair_candidate: 19`, `retake_required: 0`
- Full review package: `review_packages/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_full_source_review_20260611_182900`
- Godot validation: `ok: true`

Conclusion:

- The walk branch is now converged as the current local workflow reference.
- Remaining work should move to sword action PDCA rather than broadening walk experiments.

## Follow-Up: 768 Walk Quality Improvement Probe

Reason:

- The 512x512 converged walk source was structurally stable, but visually still looked too small and low-detail for a convincing 2D game asset review.
- This branch tested whether a 768x768 VACE walk generation can improve face, outfit, and limb readability without losing the local control workflow.

Implementation changes:

- Added `wan_walk_lower` pose render style. It keeps lower-body walk controls readable while making upper-body control lines nearly white, reducing VACE guide leakage into hands and arms.
- Added `--analysis-max-size` to `scripts/repair_frame_artifacts.py` and `scripts/select_best_span.py` so 768/1024 frames can be evaluated quickly while preserving original-resolution selected frames.
- Added a script-level regression test to ensure analysis downscaling does not downscale selected output frames.

Trial 1: 768 `wan_balanced`, 33 frames

- Output: `outputs_quality_pdca/walk_v4_identity_seed717220_vace_len33_768_quality_probe_20260611_211909`
- Selected span: `outputs_quality_span_selection/walk_v4_identity_seed717220_vace_len33_768_foreground_motion_gate_20260611_212306`
- Result: visually larger and more readable than 512, but rejected as an adopted setting because VACE copied thin control lines around the hands.
- Selected-span gate: `retake_required: 2/16` before changing control style.

Trial 2: 768 `wan_walk_lower`, 33 frames

- Output: `outputs_quality_pdca/walk_v4_identity_seed717220_vace_len33_768_lower_control_probe_20260611_213046`
- Selected span: `outputs_quality_span_selection/walk_v4_identity_seed717220_vace_len33_768_lower_control_foreground_motion_gate_20260611_213320`
- Selected gate: `outputs_quality_artifact_repair/walk_v4_identity_seed717220_vace_len33_768_lower_control_selected_gate_20260611_213440`
- Result: motion improved to foreground motion `7.103`; selected gate had `retake_required: 0/16`, but visual review still showed some hand guide-line leakage and foot afterimage in the short probe.

Trial 3: 768 `wan_walk_lower`, 121 frames

- Output: `outputs_quality_pdca/walk_v4_identity_seed717220_vace_len121_768_lower_control_source_20260611_213748`
- BiRefNet: `outputs_quality_birefnet/walk_v4_identity_seed717220_vace_len121_768_lower_control_birefnet_20260611_214536`
- Full-source gate: `outputs_quality_artifact_repair/walk_v4_identity_seed717220_vace_len121_768_lower_control_full_gate_20260611_214737`
- Selected span: `outputs_quality_span_selection/walk_v4_identity_seed717220_vace_len121_768_lower_control_foreground_motion_gate_v3_20260611_215649`
- Selected gate: `outputs_quality_artifact_repair/walk_v4_identity_seed717220_vace_len121_768_lower_control_selected_gate_v3_20260611_215846`
- Review package: `review_packages/walk_v4_identity_seed717220_vace_len121_768_lower_control_selected_quality_review_20260611_215932`

Trial 3 result:

- Full 121-frame source gate: `no_repair_needed: 113`, `repair_candidate: 6`, `retake_required: 2`.
- Retake frames: `81`, `97`, both `duplicate_silhouette_area_high`.
- Selected span: frames `59..74`.
- Selected foreground motion: `4.558`.
- Selected artifact gate: `no_repair_needed: 16/16`.
- Godot validation: `ok: true`.

Conclusion:

- There is a real visual-quality improvement over the 512 walk proof: the selected 768 package has a larger readable character, clearer face/hair, better outfit definition, and cleaner full-body silhouette.
- It is not yet a full 121-frame adopted source because 2 frames still trip the full-source retake gate and the 768 route can still show faint guide-line or skin-ghost artifacts depending on span.
- The next quality step should focus on eliminating guide-line leakage at generation time, not post-cleaning. Reducing `protect-grow` and white-cleaning masks can touch skin/legs and is not safe as a default.

## Follow-Up: 1024 Full-Body Side Reference Phase

Reason:

- Directly using the original bust-up reference as a Wan start image preserves the close-up framing too strongly.
- Before more broad seed/prompt searches, the workflow needs a clean full-body side-view reference that Wan/VACE can preserve.
- The reference image is treated as a character design source, not as pixels to puppet directly.

Implementation:

- Added `scripts/generate_fullbody_reference_candidates.py`.
- The script creates 1024x1024 `novaOrangeXL_v120.safetensors + SDXL/OpenPoseXL2` candidates, runs start-frame cleanup, scores single-frame quality, selects a candidate, and writes a compact review summary.
- Added tests in `tests/test_fullbody_reference_candidates_script.py` for workflow wiring and candidate assessment.

Trial 1:

- Output: `outputs_fullbody_reference/Anima_00013__20260611_231434`
- Result: rejected by visual review.
- The strict side prompt produced a model-sheet-like source with multiple side figures; the cleaned crop was not a safe adoption path.
- The slight 3/4 prompt produced a high-quality full-body figure, but it was too front-facing for side-view walk generation.

Retake changes:

- Strengthened prompts and negative prompts against model sheets, turnaround sheets, multiple views, guide lines, and front-facing views.
- Added stricter single-character retake variants.
- Updated candidate assessment so `extra_foreground_components_removed` is no longer considered auto-adoptable.

Trial 2:

- Output: `outputs_fullbody_reference/Anima_00013__20260611_231614`
- Selected raw candidate: `outputs_fullbody_reference/Anima_00013__20260611_231614/selected_reference/start_frame.png`
- Background normalization: `outputs_fullbody_reference_cleanup/anima_00013_side_reference_bg_normalize_20260611_231757`
- Final selected reference frame: `outputs_fullbody_reference_cleanup/anima_00013_side_reference_bg_normalize_20260611_231757/frames/frame_000.png`
- Start-frame gate: `outputs_fullbody_reference_gate/anima_00013_selected_side_reference_gate_20260611_231815/artifact_repair_report.json`
- Review package: `review_packages/anima_00013_fullbody_side_reference_phase1_20260611_231836`

Result:

- Selected candidate: `strict_side_profile_retake`
- Source candidate report: `component_count: 1`, no start-frame warning issue codes.
- Quality gate before background cleanup: `hard_failure: false`, no issue codes, score `0.95827`.
- Background-normalized single-frame artifact gate: `no_repair_needed: 1/1`.
- Visual review: the selected frame is a single full-body right-facing side-view character with readable face, sailor uniform, dark socks, brown loafers, and complete feet.

Conclusion:

- Phase 1 is complete enough to feed the next Wan/VACE walk-quality PDCA.
- The adopted reference is not a final animation asset; it is a full-body side-view start/reference image for temporal generation.
- The next step is Phase 2: replace RGB skeleton-like VACE controls with a softer silhouette/depth control style to reduce guide-line leakage.

## Follow-Up: Phase 2 Control-Style Comparison With Full-Body Reference

Reason:

- The 768 proof improved visual scale, but previous `wan_balanced`/`wan_walk_lower` outputs could copy visible pose-guide lines around hands, legs, or the background.
- Phase 2 tested whether a non-RGB silhouette/foot-contact control can preserve walk motion without copying skeleton-like guide lines.

Implementation:

- Added `vace_walk_silhouette` in `src/natural_sprite_lab/pose_templates.py`.
- Added CLI support in `scripts/run_wan_walk_i2v.py`, `scripts/build_synthetic_sideview_motion_source.py`, and `scripts/import_motion_source_pose.py`.
- The new control renders a white background with grayscale body, leg silhouettes, and foot-contact marks rather than OpenPose RGB bones.
- Added regression coverage in `tests/test_pose_templates.py`.

Comparison setup:

- Start/reference image: `outputs_fullbody_reference_cleanup/anima_00013_side_reference_bg_normalize_20260611_231757/frames/frame_000.png`
- Motion source: `outputs_motion_source_video_pdca/run_synthetic_sideview_walk_v4_edge_stride`
- Mode: `WanVaceToVideo`
- Resolution: `768x768`
- Length: `33`
- Seed: `717220`
- Steps/CFG: `8`, `3.0`

Results:

1. `wan_balanced`
   - Output: `outputs_quality_pdca/phase2_ref_side_wan_balanced_len33_768_20260611_232243`
   - Gate: `outputs_quality_artifact_repair/phase2_ref_side_wan_balanced_len33_gate_20260611_232807`
   - Gate summary: `no_repair_needed: 31`, `repair_candidate: 2`, `retake_required: 0`
   - Visual review: best structural result in this comparison, but thin guide-like lines still appear near hands/side in several frames.

2. `wan_walk_lower`
   - Output: `outputs_quality_pdca/phase2_ref_side_wan_walk_lower_len33_768_20260611_232440`
   - Gate: `outputs_quality_artifact_repair/phase2_ref_side_wan_walk_lower_len33_gate_20260611_232807`
   - Gate summary: `no_repair_needed: 26`, `repair_candidate: 6`, `retake_required: 1`
   - Visual review: similar guide leakage, plus one duplicate-silhouette gate failure.

3. `vace_walk_silhouette`
   - Output: `outputs_quality_pdca/phase2_ref_side_vace_walk_silhouette_len33_768_20260611_232622`
   - Gate: `outputs_quality_artifact_repair/phase2_ref_side_vace_walk_silhouette_len33_gate_20260611_232808`
   - Gate summary: `no_repair_needed: 23`, `repair_candidate: 5`, `retake_required: 5`
   - Visual review: rejected. The non-RGB control avoided classic OpenPose color lines, but VACE copied the silhouette guide as back straps/limb guide shapes and produced stronger foot artifacts.

Diagnostic package:

- `review_packages/phase2_ref_side_wan_balanced_len33_diagnostic_20260611_233029`

Conclusion:

- The new silhouette control is not promoted.
- `wan_balanced` is the best Phase 2 diagnostic candidate by gate count, but it is not promoted as the walk-quality default because visual guide-line leakage remains visible.
- The next control retake should make control information less copyable by VACE, likely by lowering contrast further, separating control from character-colored regions, or moving foot-contact constraints into a non-image sidecar/evaluation layer rather than drawing them into the generation control video.

## Follow-Up: Phase 2 Retake and Phase 4 Full 121-Frame Probe

Reason:

- `vace_walk_silhouette` reduced RGB skeleton semantics but still copied visible guide shapes into the character.
- A second retake tested whether a much lower-contrast lower-body-only hint could preserve enough foot motion while avoiding back/arm guide-shape leakage.

Implementation:

- Added `vace_walk_lower_hint`.
- This style draws only pale pelvis, lower-leg, and foot-contact hints; it intentionally omits torso/head/arm guide shapes so VACE has less copyable structure near the outfit and hands.

Short 33-frame probe:

- Output: `outputs_quality_pdca/phase2_ref_side_vace_walk_lower_hint_len33_768_20260611_233434`
- Full 33 gate: `outputs_quality_artifact_repair/phase2_ref_side_vace_walk_lower_hint_len33_gate_20260611_233616`
- Full 33 gate summary: `no_repair_needed: 30`, `repair_candidate: 1`, `retake_required: 2`
- Selected span: `outputs_quality_span_selection/phase2_ref_side_vace_walk_lower_hint_len33_foreground_motion_gate_20260611_233739`
- Selected span: frames `0..15`, foreground motion `7.624`, hard failures `0`, no selection penalties.
- Selected gate: `outputs_quality_artifact_repair/phase2_ref_side_vace_walk_lower_hint_selected_gate_20260611_233923`
- Selected gate summary: `no_repair_needed: 16/16`
- Review package: `review_packages/phase2_ref_side_vace_walk_lower_hint_selected_review_20260611_234017`
- Godot validation: `ok: true`

Decision:

- Promote `vace_walk_lower_hint` as the next walk-quality control default for full-source testing.
- It is not a final adoption claim; it is the best current control representation because visual guide leakage is much lower than `wan_balanced`, `wan_walk_lower`, or `vace_walk_silhouette`.

Full 121-frame probe:

- Output: `outputs_quality_pdca/phase4_ref_side_vace_walk_lower_hint_len121_768_20260611_234129`
- BiRefNet: `outputs_quality_birefnet/phase4_ref_side_vace_walk_lower_hint_len121_768_birefnet_20260611_234944`
- Full gate: `outputs_quality_artifact_repair/phase4_ref_side_vace_walk_lower_hint_len121_full_gate_20260611_235159`
- Raw span: `outputs_quality_span_selection/phase4_ref_side_vace_walk_lower_hint_len121_raw_foreground_motion_gate_20260611_235636`
- Selected-span package: `review_packages/phase4_ref_side_vace_walk_lower_hint_len121_selected_review_20260612_000125`
- Full-source package: `review_packages/phase4_ref_side_vace_walk_lower_hint_len121_full_source_review_20260611_235857`
- Godot validation: `ok: true` for both selected-span and full-source packages.

Full 121 result:

- Frame count: `121`
- Full-source artifact gate: `no_repair_needed: 48`, `repair_candidate: 73`, `retake_required: 0`.
- Main recurring issue: `masked_ghost_or_small_artifact`, mostly small foot-shadow/foot-contact remnants.
- Raw selected span: frames `1..16`, hard failures `0`, mean foreground motion `3.912`, selection penalty `mean_motion_delta_too_low`.

Conclusion:

- This is the strongest full-source E2E result in the branch because it combines a valid 1024 full-body side reference, lower-copy control, 768 generation, BiRefNet foreground separation, full-source retake count `0/121`, and Godot playback.
- It is still not final adoption quality. The remaining blocker is motion/readability, not structural breakage: the full sequence is clean and consistent, but the walk is conservative and foot-shadow artifacts are still visible enough to require explicit visual labeling before claiming a production-quality walk.
- Next practical step: add quality labels for foot-shadow/contact artifacts and low-motion/foot-sliding, then run a 1024 short probe only if the labels confirm the 768 short proof is visually stable enough.

## Follow-Up: Labeled Quality Gate for the 121-Frame Walk Candidate

Reason:

- The previous full-source gate could report `retake_required: 0/121` while the visual review still saw weak motion, foot-contact shadows, and subtle copied guide artifacts.
- To avoid overclaiming quality, the gate now records manual-review labels separately from hard structural failures.

Implementation:

- Added frame-level `review_labels` in `scripts/repair_frame_artifacts.py`.
- Added summary-level `review_label_counts` and conservative `candidate_status`.
- Added span-level `selection_review_labels` in `scripts/select_best_span.py`.
- Added regression tests for visible guide-line labels, foot-shadow/contact labels, low-motion span labels, and conservative candidate classification.

Labeled recheck:

- Source frames: `outputs_quality_birefnet/phase4_ref_side_vace_walk_lower_hint_len121_768_birefnet_20260611_234944/frames`
- Span selection report: `outputs_quality_span_selection/phase4_ref_side_vace_walk_lower_hint_len121_labeled_foreground_motion_gate_20260612_001054/span_selection_report.json`
- Labeled artifact gate: `outputs_quality_artifact_repair/phase4_ref_side_vace_walk_lower_hint_len121_full_gate_labeled_20260612_001153/artifact_repair_report.json`

Result:

- Span selection: frames `3..18`, hard failures `0`, mean foreground motion `3.019`, `selection_review_labels: ["weak_motion_or_foot_sliding_review"]`.
- Labeled full-source gate: `no_repair_needed: 36`, `repair_candidate: 83`, `retake_required: 2`.
- Retake frames: `85`, `89`.
- Main labels: `foot_shadow_or_contact_artifact_review: 85`, `skin_colored_afterimage_near_legs_review: 77`, `visible_guide_line_leakage_review: 8`.
- Candidate status: `rejected`.

Conclusion:

- The full-body-reference `vace_walk_lower_hint` route remains the best current workflow direction, but the current 121-frame output is not adoptable.
- The next improvement should not be Image2Image polish. The blocker is generation/control quality: stronger walk motion and cleaner foot-contact rendering are needed before refinement.
- Next action: improve or replace the 120-frame walk motion source, then rerun 768 full-source generation and require both labeled full-source `retake_required: 0/121` and no low-motion selection label.

## Follow-Up: Motion Source and VACE Strength PDCA

Reason:

- The labeled 121-frame candidate was too conservative: selected-span mean foreground motion was below target and labeled as weak motion / foot-sliding review.
- The next question was whether stronger foot travel can clear the motion gate without reintroducing duplicate legs, guide leakage, or foot-contact artifacts.

Motion sources:

1. `run_synthetic_sideview_walk_v5_contact_swing`
   - Settings: `stride=0.105`, `lift=0.052`, `body_bob=0.018`.
   - Intent: stronger contact/swing motion.

2. `run_synthetic_sideview_walk_v6_moderate_contact`
   - Settings: `stride=0.094`, `lift=0.045`, `body_bob=0.015`.
   - Intent: intermediate control between v4 and v5.

Short 33-frame results:

1. v5, VACE strength `1.0`
   - Output: `outputs_quality_pdca/phase3_v5_contact_swing_vace_lower_hint_len33_768_20260612_001741`
   - Span: `outputs_quality_span_selection/phase3_v5_contact_swing_len33_foreground_motion_gate_20260612_002005`
   - Gate: `outputs_quality_artifact_repair/phase3_v5_contact_swing_len33_labeled_gate_20260612_002005`
   - Result: mean foreground motion `7.953`, but selected span had hard failures `2`; full gate `retake_required: 7/33`. Rejected.

2. v6, VACE strength `1.0`
   - Output: `outputs_quality_pdca/phase3_v6_moderate_contact_vace_lower_hint_len33_768_20260612_002056`
   - Span: `outputs_quality_span_selection/phase3_v6_moderate_contact_len33_foreground_motion_gate_20260612_002316`
   - Gate: `outputs_quality_artifact_repair/phase3_v6_moderate_contact_len33_labeled_gate_20260612_002316`
   - Result: mean foreground motion `7.803`, but selected span had hard failures `4`; full gate `retake_required: 11/33`. Rejected.

3. v5, VACE strength `0.75`
   - Output: `outputs_quality_pdca/phase3_v5_contact_swing_vace075_lower_hint_len33_768_20260612_002403`
   - Span: `outputs_quality_span_selection/phase3_v5_contact_swing_vace075_len33_foreground_motion_gate_20260612_002623`
   - Gate: `outputs_quality_artifact_repair/phase3_v5_contact_swing_vace075_len33_labeled_gate_20260612_002623`
   - Result: mean foreground motion `6.352`; full gate improved to `retake_required: 4/33`. Still rejected.

4. v5, VACE strength `0.55`
   - Output: `outputs_quality_pdca/phase3_v5_contact_swing_vace055_lower_hint_len33_768_20260612_002703`
   - BiRefNet: `outputs_quality_birefnet/phase3_v5_contact_swing_vace055_lower_hint_len33_768_birefnet_20260612_002904`
   - Span: `outputs_quality_span_selection/phase3_v5_contact_swing_vace055_len33_foreground_motion_gate_20260612_002948`
   - Full 33 gate: `outputs_quality_artifact_repair/phase3_v5_contact_swing_vace055_len33_labeled_gate_20260612_002948`
   - Selected gate: `outputs_quality_artifact_repair/phase3_v5_contact_swing_vace055_selected_labeled_gate_20260612_003026`
   - Review package: `review_packages/phase3_v5_contact_swing_vace055_selected_review_20260612_003057`
   - Result: selected span frames `17..32`, hard failures `0`, mean foreground motion `7.695`, no selection penalties, Godot `ok: true`.
   - Selected-span gate: `no_repair_needed: 11`, `repair_candidate: 5`, `retake_required: 0`, candidate status `selected_proof_only`.
   - Full 33 gate: `retake_required: 2/33`, so it is not a full-source adoption.

Conclusion:

- The strongest short proof is `run_synthetic_sideview_walk_v5_contact_swing` with `--vace-strength 0.55`.
- Lowering VACE strength was more effective than lowering the motion-source stride: v6 reduced neither hard failures nor artifacts, while v5 at `0.55` kept strong motion and reduced full-gate retakes.
- Next action: run a 121-frame 768 probe with v5 + `vace_strength=0.55`, then require labeled full-source `retake_required: 0/121`, no selected-span motion penalty, and a clean visual review before adoption.

## Follow-Up: 121-Frame v5 Contact-Swing Probe

Reason:

- The v5 + `vace_strength=0.55` short proof cleared the motion problem on a selected span.
- The next test was whether that setting scales to a full 121-frame source.

Run:

- Output: `outputs_quality_pdca/phase4_v5_contact_swing_vace055_len121_768_20260612_003216`
- BiRefNet: `outputs_quality_birefnet/phase4_v5_contact_swing_vace055_len121_768_birefnet_20260612_003926`
- Span: `outputs_quality_span_selection/phase4_v5_contact_swing_vace055_len121_foreground_motion_gate_20260612_004123`
- Full gate: `outputs_quality_artifact_repair/phase4_v5_contact_swing_vace055_len121_labeled_gate_20260612_004123`
- Selected gate: `outputs_quality_artifact_repair/phase4_v5_contact_swing_vace055_len121_selected_labeled_gate_20260612_004300`
- Review package: `review_packages/phase4_v5_contact_swing_vace055_len121_selected_review_20260612_004320`

Results:

- Full source generated `121` frames at `768x768`.
- BiRefNet structure improved versus earlier strong-motion attempts: `mask_ok: 76`, `review_sparse_foreground_bbox: 44`, `retake_foreground_too_small: 1`.
- Selected span: frames `0..15`, hard failures `0`, mean foreground motion `5.569`, no selection penalties.
- Selected gate: `no_repair_needed: 14`, `repair_candidate: 2`, `retake_required: 0`, candidate status `selected_proof_only`.
- Full-source labeled gate: `repair_candidate: 21`, `no_repair_needed: 49`, `retake_required: 51`, candidate status `rejected`.
- Main full-source issue: `foreground_too_small: 51`.
- Visual review: not adoptable. The selected contact sheet has useful walk motion, but the legs/feet become too faint and the character's readable foreground presence is unstable. The result is better motion evidence, not a production walk asset.

Conclusion:

- v5 + `vace_strength=0.55` solves the low-motion problem but introduces foreground preservation failure across the full 121-frame source.
- The next PDCA should target subject preservation under stronger motion: either strengthen reference/subject conditioning without reintroducing guide copying, tune VACE strength between `0.55` and `0.75`, or improve the control video so feet move strongly while the body silhouette remains dense.
- Do not move this candidate to Image2Image polish. The legs/feet are too faint; refinement would decorate a weak source rather than fix the generation failure.
