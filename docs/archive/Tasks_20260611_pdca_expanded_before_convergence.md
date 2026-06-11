# Tasks: Adoption-Grade Local 2D Animation Asset Workflow

## Current Recognition

- [x] The project goal remains local-first 2D game asset generation from one reference character image plus one natural-language action request.
- [x] The input image is a character design reference, not a pixel source to shake, rig, or puppet as the final method.
- [x] `novaOrangeXL` remains the preferred SDXL still-image checkpoint.
- [x] `WanAnimateToVideo + reference_image + pose_video + TrimVideoLatent + post-trim` is the best local temporal-consistency path found so far.
- [x] OpenPose templates are useful for gross body phase, but body keypoints alone are insufficient for weapons, fast limb contact, and final adoption quality.
- [x] Image2Image is a finishing pass only; it should not be expected to repair pose, body, or weapon structure.
- [x] Explicit masked inpaint can repair small ghost artifacts, but duplicate legs, strong afterimages, and fragmented weapons must return to generation control or trim selection.
- [x] External dance/character-animation workflows suggest the next stability jump should come from dense source-video pose extraction, pose alignment, and confidence-aware pose rendering, not more prompt or seed search.
- [x] The previous completed task list is archived at `docs/archive/Tasks_20260611_completed_novaOrangeXL_controlnet_sprite_asset_workflow.md`.
- [x] Generated `outputs*` folders are cleanup candidates after findings are documented.

## Scope Guard

- [x] Main path is local ComfyUI generation plus local evaluation; do not introduce cloud dependency for core workflow.
- [x] Keep the workflow centered on natural-language action requests converted into structured generation controls.
- [x] Prefer reusable controls and measurable gates over one-off prompt tweaking.
- [x] Prefer motion-source controls over text-only action descriptions when hand-authored templates fail quality gates.
- [x] Keep 120-frame generation as the high-quality source target; thinning/export remains a separate later workflow.
- [x] Judge adoption by animation playback, contact sheets, comparison sheets, and quality reports, not single-frame beauty.
- [x] Keep generated output folders out of git unless explicitly requested.

## Non-Goals

- [x] Do not return to rigged puppet or cutout animation as the final asset route.
- [x] Do not accept a result just because it has plausible motion if identity or structure is broken.
- [x] Do not use Image2Image or inpaint to hide large structural failures.
- [x] Do not treat generic `attack` or `hit` as sufficient action definitions.
- [x] Do not make a checkpoint switch without a documented comparison against `novaOrangeXL`.
- [x] Do not manually inspect many output folders without producing a compact review package.
- [x] Do not keep local generated intermediates indefinitely after their findings are captured.

## Primary Problems To Solve

- [x] Run/walk results need automatic best-span selection before polishing.
- [x] Running currently reuses the `walk` pose template; this should become a dedicated `run` template.
- [x] Strong afterimages and duplicate silhouettes are still common in fast motion.
- [x] Foot/leg duplication needs a more reliable local metric and retake trigger.
- [x] Sword, axe, and bow outputs need weapon-specific controls beyond body OpenPose.
- [x] Weapon continuity needs explicit evaluation: connected to hands, elongated where appropriate, not fragmented.
- [x] Background contamination and character fading need automatic scoring.
- [x] Godot validation should cover selected Wan/refined/repaired outputs, not only older manifest-based outputs.
- [x] PDCA output review should be summarized into a small adoption package.

## Next Action Plan

- [x] First, make walk/run adoption easier by selecting cleaner spans automatically.
- [x] Next, build a dedicated `run` pose template and compare it against the previous walk-template run.
- [x] Then, add stronger artifact metrics and make those metrics feed retake decisions.
- [x] After walk/run is more stable, tackle weapon actions with explicit weapon control assets.
- [x] Finally, package selected candidates for Godot review and cleanup local intermediates.

## Automatic Best-Span Selection

- [x] Add a script that scans all frames in a Wan output folder and selects the best contiguous span.
- [x] Score each frame for foreground visibility.
- [x] Score each frame for background cleanliness.
- [x] Score each frame for duplicate silhouette risk.
- [x] Score each frame for lower-body blob count.
- [x] Score each frame for face/upper-body stability where simple local heuristics can support it.
- [x] Score each frame for frame-to-frame motion continuity.
- [x] Reject spans with any hard structural failure unless explicitly overridden.
- [x] Write selected frames to `selected_frames/`.
- [x] Write `span_selection_report.json`.
- [x] Write `span_contact_sheet.png`.
- [x] Write `span_preview.gif`.
- [x] Add tests for span scoring on synthetic image sequences.

## Dedicated Run Pose Template

- [x] Add `run` to the action catalog if missing.
- [x] Add `pose_templates/run/frame_000.json` through `frame_119.json`.
- [x] Use larger stride than walk.
- [x] Add airborne or near-airborne phases.
- [x] Add stronger arm pumping opposite to legs.
- [x] Keep common character scale and ground-line rules compatible with existing templates.
- [x] Render `pose_templates/run/controlnet/*.png`.
- [x] Generate `pose_templates/run/contact_sheet.png`.
- [x] Add tests for loading and validating the `run` template.
- [x] Run WanAnimateToVideo with `pose_template=run`.
- [x] Compare `run` template output against prior `walk`-template run output in a report.

## Motion-Source Pose Import

- [x] Add a local converter from extracted OpenPose/DWPose-style JSON into `pose_templates/<action>/frame_000.json` through `frame_119.json`.
- [x] Preserve per-keypoint confidence where the source provides it.
- [x] Align imported motion to the target local template scale and baseline before rendering.
- [x] Add a confidence-aware Wan pose render style for imported motion sources.
- [x] Add tests for BODY_25 import, local-template import, confidence rendering, and 120-frame resampling.
- [x] Install and expose the local SDPose checkpoint so ComfyUI can run `SDPoseKeypointExtractor`.
- [x] Validate SDPose extraction on the current clean start frame and save a pose-map proof.
- [x] Add a local ComfyUI custom node for saving `POSE_KEYPOINT` outputs as OpenPose JSON.
- [x] Restart/reload ComfyUI and verify the pose JSON saver node appears in `/object_info`.
- [x] Run video/image pose extraction through the JSON saver and feed the exported JSON into `scripts/import_motion_source_pose.py`.
- [x] Run a source-video-derived walk/run motion-source PDCA through `wan_confidence_lower`.

### Current Motion-Source Findings

- [x] SDPose can detect the current clean start frame and emit a usable full-body pose map.
- [x] The custom ComfyUI JSON saver can persist `POSE_KEYPOINT` output as OpenPose-frame JSON.
- [x] Image-derived SDPose JSON can be imported into the local 120-frame template format.
- [x] The remaining quality jump should come from a real action source video, not another hand-authored pose or prompt-only Wan run.
- [x] A single-frame SDPose probe is connector proof only; it is not animation proof.

### Next Motion-Source Actions

- [x] Add a script that runs `LoadVideo -> GetVideoComponents -> SDPoseKeypointExtractor -> NaturalSpriteSavePoseKeypointsJSON`.
- [x] Prepare a local MP4 smoke source from the current best run review GIF to verify the video path wiring.
- [x] Run the smoke MP4 through video-derived SDPose JSON export and local template import.
- [x] Run a `wan_confidence_lower` Wan connector smoke from the imported video-derived template.
- [x] Export a review package for the motion-source smoke run and record it as non-adoptable.
- [x] Try to acquire Wikimedia Commons `Walk-Cycle.gif` as a clean source candidate and record the HTTP 429 download block.
- [x] Acquire or prepare a clean external walk/run source video; generated review GIFs are connector smoke inputs only, not quality evidence.
- [x] Feed the clean-source video-derived JSON into `scripts/import_motion_source_pose.py`.
- [x] Render the clean-source imported template with `wan_confidence_lower`.
- [x] Run WanAnimateToVideo with the clean-source imported motion template.
- [x] Run best-span selection, artifact gate, Godot validation, and review package export.
- [x] Compare the source-video-derived run against `review_packages/run_wan_lower_default_prompt_source_review_20260611_080321`.
- [x] Only proceed to weapon PDCA if the source-video walk/run span has no structural retake frames.
- [x] Add source-frame range and mean-confidence filtering to motion-source import so weak SDPose frames do not poison Wan controls.
- [x] Record the Mixkit walk-source PDCA as better motion evidence but still not adoption-grade.
- [x] Improve the clean-source walk run by reducing background color drift and residual leg afterimages enough to reach artifact `retake_required: 0/8` after BiRefNet separation.
- [x] Record that the clean-source 0-retake walk remains `manual_review`, not `adoptable`, because foreground-internal leg/arm afterimages are still visible in the contact sheet.
- [x] Try a cleaner source-video pre-process: tighter crop or person-scale normalization before SDPose extraction.
- [x] Try Wan generation with the same imported motion but a stronger plain-white-background prompt and/or character mask.
- [x] Record that auto character mask degraded WanAnimateToVideo in this workflow and should not be the next default.
- [x] Record that stronger white-background prompting reduces color drift only partly and can amplify leg ghosting.
- [x] Add `--pose-sample-span` so Wan can sample a limited section of a 120-frame pose template instead of always spanning the full template.
- [x] Test limited pose-span sampling and record that `pose-sample-span=32` reduced motion delta but caused identity fading in this run.
- [x] Test phase-shifted source-video pose sampling and record that phase changes did not remove duplicate-leg retakes.
- [x] Add deterministic white-mask cleanup and record that broad mask cleanup worsened selected walk frames.
- [x] Try another Mixkit source family candidate and reject foot-only sidewalk footage before SDPose/Wan because it cannot provide full-body pose.

### Quality Recovery Plan After Current Walk Failures

- [x] Treat residual duplicate legs, strong afterimages, and background color drift as generation-control failures, not img2img cleanup failures.
- [x] Add `scripts/audit_comfy_wan_nodes.py` so available local Wan control routes are discovered from ComfyUI `/object_info`.
- [x] Audit the current ComfyUI setup and record that `WanAnimateToVideo` has `reference_image + pose_video + character_mask` but no `end_image`.
- [x] Record that `Wan22FunControlToVideo` is locally available with `ref_image + control_video`, making it the next comparison route before more prompt-only tuning.
- [x] Add `wan22_fun_control` mode to `scripts/run_wan_walk_i2v.py`.
- [x] Run `wan22_fun_control` with the current best Mixkit-derived walk pose control.
- [x] Run best-span selection and artifact gate on the `wan22_fun_control` result.
- [x] Compare `wan22_fun_control` against the current best `WanAnimateToVideo` result.
- [x] Record that `wan22_fun_control` with the normal Wan 14B I2V model fails by reconstructing the green control video rather than the character.
- [x] If `wan22_fun_control` fails, try `WanFunControlToVideo` as the fallback `start_image + control_video` route before changing source video again.
- [x] Record that `WanFunControlToVideo` also fails with the normal Wan 14B I2V model by producing faint pose-line output.
- [x] Install `Wan2.1-Fun-1.3B-Control.safetensors` as the first local FunControl model candidate.
- [x] Re-run `WanFunControlToVideo` with the FunControl model and verify it generates character animation instead of pose-line reconstruction.
- [x] Compare `wan_confidence_lower`, `controlnet`, and `wan_line` pose render styles with the FunControl model.
- [x] Export a review package for the best FunControl 1.3B candidate and validate it in Godot.
- [x] Update the Skill and PDCA report with the FunControl model requirement and current best settings.
- [x] Try a larger or higher-quality FunControl model if a practical local checkpoint is available.
- [x] Install `Wan2.1-Fun-14B-Control.safetensors` and compare it against the 1.3B FunControl candidate.
- [x] Record that 14B FunControl did not improve the current Mixkit walk gate: it stayed at `retake_required: 5/8`.
- [x] Add `controlnet_thin` as a weaker control-video render style and test it.
- [x] Record that `controlnet_thin` worsened the selected span score and did not reduce structural retakes.
- [x] Add `--min-ankle-x-separation` to source-pose import for dropping leg-crossing source frames.
- [x] Test ankle-separation source filtering and record that it did not reduce retakes for the current FunControl walk.
- [x] Test FunControl 1.3B with the lower-stride synthetic source and normal `controlnet` rendering.
- [x] Reject lower-stride FunControl `controlnet`: it produced attractive still frames but failed animation gates with `hard_failures: 16/16`, `mean_motion_delta_too_low`, and artifact `retake_required: 16/16`.
- [x] Test FunControl 1.3B with the lower-stride synthetic source and `wan_balanced` rendering.
- [x] Reject lower-stride FunControl `wan_balanced`: it became front-facing/static, with `mean_motion_delta_too_low` and no usable walk span.
- [x] Close the current FunControl walk branch as non-primary: lower-stride synthetic `controlnet` kept duplicate silhouette carryover, and `wan_balanced` reduced artifacts only by collapsing motion/readability.
- [x] Only after FunControl control rendering fails, search for or prepare a new full-body side-view source video family.
- [x] Try a different source-video family or a cleaner pose-control backend before more prompt-only tuning.
- [x] Investigate whether WanAnimateToVideo supports a stronger motion/reference split or first/last-frame constraint with pose input.
- [x] Re-run quality gates until the source-video walk span has `retake_required: 0/8`.

### Quality Improvement Plan If Current Route Stalls

- [x] Use the existing findings as constraints: do not spend more cycles on prompt-only tuning, more steps, broad masks, thin control lines, or img2img structural repair.
- [x] Treat the source-motion clip as a first-class input quality problem: reject clips that do not provide full-body, side-view, high-confidence pose across enough frames.
- [x] Add a compact source probe package exporter for source contact sheets, SDPose reports, imported control contact sheets, generation gates, and accept/reject notes.
- [x] For each new source candidate, make a compact probe package before generation: source contact sheet, SDPose confidence summary, imported control contact sheet, and accept/reject note.
- [x] Reject source candidates that keep fewer than 8 high-confidence full-body pose frames after filtering unless they are only used as negative evidence.
- [x] Test a lower-confidence import only as a diagnostic when a source has good visible motion but SDPose keeps too few frames.
- [x] Diagnose Mixkit 35419 with a lower-confidence import, run one Animate probe, and reject it because the selected span had hard failures `5/8` and gate `retake_required: 6/8`.
- [x] Test `WanAnimateToVideo --continue-motion-max-frames 1` on the best clean-source walk baseline.
- [x] Package the `continue_motion_max_frames=1` walk candidate for review and Godot validation.
- [x] Record that `continue_motion_max_frames=1` improved stability evidence but did not clear the final gate: `retake_required: 1/8`.
- [x] Test one seed repeat for `continue_motion_max_frames=1` and reject it when span hard failures rose to `6/8`.
- [x] Add a synthetic clean side-view motion-source builder to separate source-pose noise from Wan generation failures.
- [x] Test synthetic side-view motion source with `WanAnimateToVideo` and `continue_motion_max_frames=1`.
- [x] Record that synthetic side-view v1 reduced span structural hard failures to `0/8` but still failed visual adoption after stricter gate review.
- [x] Fix artifact gate so broad repair masks are retake blockers even in `--mask-only` evaluation.
- [x] Re-run the synthetic side-view gate after the fix and record the corrected result: `retake_required: 3/8`, `repair_mask_too_large: 3`.
- [x] Add `wan_balanced` pose render style as an intermediate between `wan_confidence_lower` and `wan_lower`.
- [x] Test `wan_balanced` on synthetic side-view motion and reject it because it reintroduced duplicate-leg failures.
- [x] Test longer `33`-frame synthetic balanced generation and reject it because no clean 8-frame span was found.
- [x] Test bright appearance prompt with synthetic v1 and reject it because blue-gray background contamination caused `retake_required: 8/8`.
- [x] Test deterministic white cleanup on the bright-prompt output and reject it because it produced white holes and still failed `retake_required: 8/8`.
- [x] Test small `character_mask` subject/reference preservation on synthetic v1 and reject it because it caused `foreground_too_small: 8` and `retake_required: 8/8`.
- [x] Add connected-background normalization as a safer alternative to artifact-mask white cleanup.
- [x] Test connected-background normalization on bright-prompt synthetic output and reject it because it still failed `retake_required: 8/8`.
- [x] Add person-cutout background normalization and reject it for the bright-prompt synthetic output because it still failed `retake_required: 8/8`.
- [x] Install local ComfyUI BiRefNet background-removal model under `models/background_removal/birefnet.safetensors`.
- [x] Add `scripts/birefnet_foreground_masks.py` to extract local BiRefNet foreground masks, RGBA frames, white composites, mask contact sheets, previews, and a JSON report.
- [x] Test BiRefNet foreground extraction on the synthetic bright-prompt selected walk span.
- [x] Record that BiRefNet converted the synthetic bright-prompt span from broad-background gate failure to `no_repair_needed: 8/8`, with stable foreground masks.
- [x] Export a compact review package for the BiRefNet synthetic bright-prompt walk candidate and run Godot validation.
- [x] Test BiRefNet foreground extraction on the current Mixkit clean-source baseline.
- [x] Record that BiRefNet helps background drift but does not remove body-internal leg/arm afterimages when those artifacts are inside the foreground mask.
- [x] Add the new BiRefNet branch to the local Skill and PDCA report.
- [x] Prefer the route with the current best evidence for the candidate: `WanAnimateToVideo` for source-video walk when FunControl carries duplicate silhouettes, `WanFunControlToVideo` only when it beats Animate on gate results.
- [x] Compare each generated candidate against the best known clean-source baseline, not only against the immediately previous run.
- [x] Stop a branch and document it when both pose control and gate evidence show the candidate cannot reach `retake_required: 0/8`.
- [x] If source-video family search fails, switch the next branch to a cleaner local motion-control source: synthetic side-view stick/pose video, depth/line-art assisted source, or a local video workflow with stronger subject/motion separation.
- [x] Integrate BiRefNet mask stability and minimum motion scoring into best-span selection so low-motion but visually clean spans are not over-accepted.
- [x] Re-score the BiRefNet synthetic bright-prompt walk candidate with `--min-mean-motion-delta 4.0` and record `mean_motion_delta_too_low`.
- [x] Generate a longer 121-frame synthetic bright-prompt/BiRefNet candidate and verify motion readability before calling it an animation asset.
- [x] Record that the 121-frame candidate produced a motion-readable 16-frame span but still failed visual adoption because lower-body silhouettes became mesh/bag-like.
- [x] Add BiRefNet mask-structure review gates so foreground separation is not treated as automatic permission to refine or adopt.
- [x] Use BiRefNet masks as character/background separation evidence before refinement, not as permission to polish structural duplicate-leg failures.
- [x] Test a lower-stride synthetic motion source (`run_synthetic_sideview_walk_v2_lower_stride`) to reduce lower-body deformation pressure.
- [x] Record that lower-stride with weak `wan_confidence_lower` did not affect Wan output enough: v1 and v2 generated identical frames under the same seed/settings.
- [x] Test lower-stride with stronger `wan_balanced` control as a generation-control branch.
- [x] Record that lower-stride + `wan_balanced` improved leg readability versus the 121-frame v1 candidate, but still remained `needs_manual_review` because BiRefNet structure gate found `review_sparse_foreground_bbox: 7/16`.
- [x] Test BiRefNet-derived start-frame foreground mask as `WanAnimateToVideo` `character_mask` for generation-time subject/background separation.
- [x] Reject the BiRefNet `character_mask` branch because it produced blurry silhouette-like frames, lower motion (`mean_motion_delta_too_low`), and brown background drift despite Godot playback loading.
- [x] Improve synthetic/local motion control with generation-side subject/background separation by adding and testing `WanVaceToVideo` with `reference_image + control_video`.
- [x] Install and verify `wan2.1_vace_1.3B_fp16.safetensors` under the local ComfyUI diffusion models.
- [x] Add `--mode vace` to `scripts/run_wan_walk_i2v.py` and route `reference_image` plus rendered local motion control video into `WanVaceToVideo`.
- [x] Add `--vace-strength` so VACE control strength can be varied without editing workflow JSON.
- [x] Test lower-stride VACE `controlnet` and reject it because it preserved appearance but stayed too low-motion with many span hard failures.
- [x] Test lower-stride VACE `wan_balanced` and record it as the best short synthetic/local walk candidate so far: clean identity/background, readable walk, but still manual-review due sparse-foreground and minor afterimage/foot overlap.
- [x] Add foreground-normalized motion scoring to best-span selection so small full-body sprites are not falsely rejected by canvas-wide pixel delta alone.
- [x] Re-score the short VACE `wan_balanced` candidate with `--motion-metric foreground` and export a Godot-validated review package.
- [x] Add `vace_depth_proxy` and `vace_side_proxy` local control-video render styles as diagnostics.
- [x] Reject `vace_depth_proxy` and `vace_side_proxy` for this character/action because VACE copied the proxy/front-view structure into the generated character instead of using it as clean motion guidance.
- [x] Run a 121-frame VACE `wan_balanced` walk candidate and select a 16-frame foreground-motion span from the full output.
- [x] Export the 121-frame VACE best span as the current best manual-review walk package; record that it has `hard_failures: 0/16` but still only `repair_candidate: 16/16` and conservative walk amplitude.
- [x] Next quality push: raise walk amplitude without reintroducing foreground-internal afterimages by testing mid-stride synthetic VACE variants and fixing lower-body blob over-penalization for normal skirt/two-foot walk frames.
- [x] Reject v3 mid-stride (`stride=0.09`, `lift=0.042`) because it increased walk readability but brought artifact `retake_required: 3/16` before gate correction and showed stronger foot/hem residual masks.
- [x] Adopt v4 edge-stride (`stride=0.083`, `lift=0.038`) as the current best manual-review walk candidate: foreground motion `4.78`, span `hard_failures: 0/16`, artifact gate `retake_required: 0/16`, Godot validation `ok: true`.
- [x] Fix lower-body blob counting in both span quality and artifact repair gates so a normal skirt plus two feet is not counted as a double-foot retake.
- [x] Next quality push: improve identity/style preservation on the current v4 walk candidate by adding explicit uncovered-hair, hair-clip, sailor-uniform, and no-headgear prompt constraints while keeping the same successful seed and motion source.
- [x] Reject the first identity prompt seed repeat (`seed=717221`) because identity improved but foreground motion fell to `3.213` with `mean_motion_delta_too_low`.
- [x] Adopt the same-seed identity prompt run (`seed=717220`) as the current best manual-review walk candidate: foreground motion `4.993`, span `hard_failures: 0/16`, artifact gate `retake_required: 0/16`, Godot validation `ok: true`.
- [ ] Next quality push: validate whether the full 121-frame identity-prompt VACE output can be treated as a continuous high-quality source asset, not only as a selected 16-frame review span.

## Artifact Metrics And Gates

- [x] Extend artifact gate reporting with a normalized duplicate silhouette area metric.
- [x] Improve lower-body blob detection so normal stride is not over-penalized.
- [x] Add background contamination ratio.
- [x] Add dark-frame or non-white-background ratio.
- [x] Add per-frame mask coverage trend.
- [x] Add sequence-level hard failure summary.
- [x] Add a retake recommendation table generated from issue codes.
- [x] Add tests for duplicate silhouette, lower-body blob, background contamination, and mask coverage metrics.
- [x] Document thresholds in the Skill.

## Image2Image And Inpaint Refinement

- [x] Keep `novaOrangeXL` Image2Image as a low-to-moderate denoise finishing pass.
- [x] Require best-span selection before Image2Image refinement.
- [x] Keep seed stable during refinement unless variation is intentional.
- [x] Add foreground/person mask support before background cleanup.
- [x] Add inpaint-only cleanup for small ghost artifacts after the artifact gate permits it.
- [x] Block inpaint for structural issue codes.
- [x] Compare source/refined/repaired frames in a single review sheet.
- [x] Document recommended settings for walk/run after the next PDCA.

## Weapon-Specific Control

- [x] Define weapon-control requirements for `attack_sword`.
- [x] Define weapon-control requirements for `attack_axe`.
- [x] Define weapon-control requirements for `attack_bow`.
- [x] Create a simple weapon guide representation for sword: hand anchor points, blade line, slash arc.
- [x] Create a simple weapon guide representation for axe: hand anchor points, shaft line, head region, swing arc.
- [x] Create a simple weapon guide representation for bow: bow curve, string line, arrow line, draw hand.
- [x] Decide how weapon guides are passed into ComfyUI locally: mask, line-art image, extra control video, or staged reference frame.
- [x] Add weapon guide rendering assets under a reusable folder.
- [x] Add weapon continuity metrics: missing weapon, fragmented weapon, detached weapon, non-elongated sword/bow.
- [ ] Run at least one weapon action PDCA after walk/run quality gates are stable.

## Review Package Export

- [x] Add a script that exports only selected evidence from a run into a compact review folder.
- [x] Include `preview.gif`.
- [x] Include `contact_sheet.png`.
- [x] Include `comparison_sheet.png` when available.
- [x] Include quality reports.
- [x] Include source command or workflow JSON references.
- [x] Include a short `review_summary.md`.
- [x] Exclude raw generated frame floods unless explicitly requested.
- [x] Add cleanup notes for the original output folder.

## Godot E2E For Selected Outputs

- [x] Create a manifest for selected Wan/refined/repaired frame folders.
- [x] Ensure Godot can load selected frames without relying on older PDCA manifests.
- [x] Validate frame count.
- [x] Validate frame dimensions.
- [x] Validate playback starts.
- [x] Save Godot validation JSON into the review package.
- [x] Add pytest coverage when Godot is available.

## Local Workflow Documentation

- [x] Update `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md` with best-span selection.
- [x] Add a dedicated local Skill or section for Wan video workflow if the procedure grows beyond the ControlNet Skill.
- [x] Update `docs/local_cleanup_and_next_tasks_report.md` or add a new progress report after the first next-phase PDCA.
- [x] Keep `README.md` focused on stable commands, not every experimental run.
- [x] Add a cleanup checklist for generated `outputs*` folders after each PDCA cycle.

## First Next-Phase Proof

- [x] Generate or reuse a walk/run Wan output with enough frames for span selection.
- [x] Run automatic span selection.
- [x] Run Image2Image refinement on the selected span.
- [x] Run artifact gate and permitted masked inpaint.
- [x] Export a compact review package.
- [x] Run Godot validation on the selected frames.
- [x] Record whether the result is `adoptable`, `needs_retake`, or `research_only`.
- [x] Document what failed if still not adoptable.

## Done Criteria For This Task Set

- [x] Completed old `Tasks.md` remains archived.
- [x] New `Tasks.md` clearly states current recognition, problems, non-goals, next actions, and done criteria.
- [x] The next engineering goal can start from this checklist without rereading the whole conversation.
- [x] All new generated outputs from future PDCA runs have a review package or a documented cleanup note.
- [x] `uv run pytest` passes after task implementation changes.
