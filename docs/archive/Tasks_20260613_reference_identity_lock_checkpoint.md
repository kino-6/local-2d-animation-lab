# Tasks: Single-Keyframe Wan I2V Walk Mainline

Archive of the expanded previous checklist:
`docs/archive/Tasks_20260613_single_keyframe_mainline_expanded.md`

## Rules

- [x] Goal: generate local-first 2D game animation assets from a character reference image plus natural-language action.
- [x] Current walk mainline: `single-keyframe Wan i2v`, not visible pose/control/foot-guide overlays.
- [x] Target adopted source length is 120 frames. If a Wan route emits 121 frames, keep raw evidence but normalize the adoption candidate to 120 frames.
- [x] Save new generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Do not promote short probes unless motion readability, lower-body quality, foot/contact quality, and Agent visual review pass.
- [x] Do not use visible `--foot-guide walk`, VACE, or Wan22Fun as mainline unless they beat single-keyframe Wan i2v on identity, motion, and artifact gates.
- [x] Long-running local generation scripts must expose ComfyUI queue controls and progress visibility.
  - ComfyUI scripts should use `add_queue_wait_arguments()` and pass `args` into queue submission so `--max-queue-size` and `--queue-wait-timeout-seconds` are honored.
  - Batch/frame loops should use `progress_iter()`.
  - ComfyUI history waits and queue waits should use `ProgressTimer`.
  - Progress is implemented through `tqdm.auto` when running in an interactive TTY, with a quiet fallback for non-TTY/test environments.
  - Any new generation/refinement/repair script must follow this rule before PDCA runs are considered complete.

## Current Baseline

- [x] Historical benchmark: `phase10_single_keyframe_wan_i2v_len121_strict_selected_proof_review_20260612_130832`.
- [x] Local `review_packages/` is not currently present; reconstruct settings from `outputs_quality_*` reports and docs.
- [x] Best known route: full-body side-view reference -> plain Wan i2v -> BiRefNet/foreground separation -> strict artifact gate -> review.
- [x] Main blocker: recurring pale lower-body afterimages and foot/contact artifacts, not failure to read as a walk.
- [x] Postprocess can help only after action and identity already read correctly.

## PDCA Loop

- [x] Recover historical phase10 settings.
  - Find start image, prompt, negative prompt, seed, width/height, length, fps, steps, cfg, sampler, scheduler, model, VAE, CLIP, and workflow.
  - Record missing settings in `docs/walk_candidate_comparison.md`.
- [x] Pick the start image for reproduction.
  - Prefer the historical phase10 start/reference image if available.
  - Otherwise use the best current contact-pose candidate only if start-frame gate issues are understood.
- [x] Run one short single-keyframe Wan i2v reproduction probe.
  - Use `length=17` or `length=33`.
  - Use no visible pose/control/foot-guide overlay.
  - Store under `outputs/<timestamp>/wan_walk_i2v/<label>/`.
- [x] Gate the short probe.
  - `select_best_span.py --action walk --motion-metric foreground`
  - `analyze_sprite_regions.py`
  - `repair_frame_artifacts.py --mask-only`
  - Agent visual review of `preview.gif` and `contact_sheet.png`
- [x] Decide the next action.
  - If short probe passes: run seed repeat, then consider 120-frame source.
  - If motion/identity is good but minor artifacts remain: try focused postprocess.
  - If double feet, guide burn-in, identity collapse, or major lower-body redraw appear: retake generation settings.
  - Result: `seed717220` raw was rejected, but stabilization improved it to `selected_proof_only`; do not promote to 120 frames yet.
  - Result: `seed717221` repeat increased motion but worsened lower-body afterimage, foot/contact, and duplicate-leg risk; rejected.

## Focused Retake Matrix

- [x] Compare start image choices: historical phase10 start image vs current contact-pose candidate.
  - Historical phase10 image is not present locally; current contact-pose candidate was used with known `shoes_unreadable` risk.
- [x] Compare prompt variants: prompt E baseline vs stricter "no translucent lower body / no pale ghost legs".
  - Result: stricter no-pale prompt did not beat `seed717220` stabilized. Region labels improved in one view, but artifact gate still reported lower-body pale labels on `16/17` frames and rejected the candidate.
- [x] Compare seeds only after the first probe is promising.
  - Compared `717220` and `717221`; `717220` is safer after stabilization.
- [x] Retake start-frame candidates before 120-frame promotion.
  - Generated `outputs/20260613_184302/fullbody_reference/comfyui2025_131891_trim/`.
  - Result: all candidates remained `manual_review_or_retake`; candidate `08` had useful stride but visible blue guide/background residue, and candidate `04` was clean enough to probe but produced mostly still frames plus orange background drift.
- [x] Test background-normalized prior best start frame.
  - Start-frame white background normalization succeeded at `outputs/20260613_185524/background_normalize/prior_best_start_background_normalize/`.
  - Result: short Wan probes reduced lower-body/foot region labels, but both `cfg=4.6` and `cfg=3.2` generated strong background/color drift and failed artifact/visual review.
  - Conclusion: background-normalized start frames are useful for lower-body diagnostics, but the next blocker is keeping Wan output on a sprite-style white/transparent background across frames.
- [x] Test post-Wan foreground separation as a background-drift fix.
  - `birefnet_foreground_masks.py` on the white-background `cfg=3.2` probe produced `mask_ok: 17/17`, artifact gate `no_repair_needed: 17/17`, and span hard failures `0`.
  - Added `stabilize_masked_sprite_sequence.py` for explicit-mask foreground color/luma correction.
  - Result: BiRefNet solves the moving blue/brown background panel; masked correction partly reduces darkening but cannot fully restore original character colors after Wan has already recolored the subject.
  - Current best diagnostic proof for background-fixed output: `outputs/20260613_192635/birefnet_foreground/phase10_prior_best_whitebg_flatlight_cfg32_birefnet_white/`.
- [x] Compare `fun_i2v` against plain `i2v` for background drift.
  - Result: `fun_i2v` matched the same background/color drift pattern and did not beat plain `i2v`.
- [ ] Try 1024 only after a 768 short probe is promising.
- [x] Record every candidate in `docs/walk_candidate_comparison.md` with route, start image, resolution, length, motion score, gate summary, visual decision, and status.

## Masked Color Restoration Goal

- [x] Keep the top rule in scope: this is still a 2D game sprite animation asset workflow from reference image plus natural-language action.
- [x] Use `outputs/20260613_192635/birefnet_foreground/phase10_prior_best_whitebg_flatlight_cfg32_birefnet_white/` as the current background-fixed short proof baseline.
- [x] Define the blocker precisely:
  - BiRefNet fixes generated background drift.
  - Artifact gate can pass after foreground compositing.
  - The remaining visual blocker is subject darkening / color cast / outfit recolor across frames.
- [x] Run low-denoise novaOrangeXL img2img on the BiRefNet white-background frames.
  - Start with 768, low denoise, fixed seed, and explicit character-color prompt.
  - Reject if it redraws legs, changes outfit, introduces frame-to-frame style flicker, or worsens walk readability.
  - Result: `outputs/20260613_200316/wan_img2img_refine/phase10_birefnet_white_nova_img2img_d015_768_color_restore/` preserved structure but did not restore later-frame darkening enough; region labels remained high.
- [x] Gate the img2img-restored candidate.
  - `select_best_span.py --action walk --motion-metric foreground`
  - `repair_frame_artifacts.py --mask-only`
  - `analyze_sprite_regions.py`
  - Agent visual review of contact sheet / preview.
  - Result: artifact gate `no_repair_needed: 16/17`, span hard failures `1`, region lower-body/foot labels remained high; rejected diagnostic.
- [x] If low-denoise img2img fails, test deterministic color transfer as a non-generative fallback.
  - Limit the correction to the BiRefNet foreground mask.
  - Prefer stable but slightly dull colors over saturated color drift.
  - Result: masked luma correction improves readability numerically, but triggers duplicate-silhouette hard failures and visual recolor risk; do not promote over uncorrected BiRefNet proof.
- [x] Retake generation-side color drift with lower Wan `shift`.
  - Result: `shift=4.0`, `cfg=2.8` worsened raw output, but after BiRefNet it produced the best background-fixed proof so far.
  - Best proof: `outputs/20260613_201556/birefnet_foreground/phase10_prior_best_whitebg_shift4_cfg28_birefnet_white/`.
- [x] Package the best background-fixed proof as a game sprite asset.
  - Packaged as `outputs/20260613_201942/game_sprite_asset/phase10_walk_shift4_birefnet_selected_proof_asset/`.
  - Manifest status is `selected_proof_only`, not adopted.
- [x] Record the best candidate and the rejected variants in `docs/walk_candidate_comparison.md`.
- [x] Decide whether this route is promotion-ready, `selected_proof_only`, or still `rejected_diagnostic`.
  - Decision: `selected_proof_only`. Background-fixed asset packaging now works, but character darkening/recoloring still blocks adoption and 120-frame promotion.

## Adoption-OK Path PDCA

- [x] Define the adoption blocker from the latest proof.
  - Motion reads as a walk on short proof.
  - BiRefNet foreground separation fixes sprite-background drift.
  - The remaining blocker is character-internal color/lighting instability, especially later-frame darkening and outfit/skin recolor.
- [x] Add deterministic masked histogram matching as a low-risk postprocess.
  - Implemented `histogram_match` in `scripts/stabilize_masked_sprite_sequence.py`.
  - Added unit coverage in `tests/test_stabilize_masked_sprite_sequence.py`.
  - Test command: `uv run pytest tests\test_stabilize_masked_sprite_sequence.py`.
- [x] Run histogram-strength sweep on the current best BiRefNet proof.
  - `0.45`: luma stdev `25.63 -> 13.96`, artifact gate `no_repair_needed: 17/17`, span hard failures `0`, still visually darker than adoption target.
  - `0.55`: luma stdev `25.63 -> 11.33`, artifact gate `retake_required: 2/17` from duplicate-silhouette risk.
  - `0.65`: luma stdev `25.63 -> 8.73`, artifact gate `retake_required: 3/17` from duplicate-silhouette risk.
- [x] Package the safest improved short proof.
  - Packaged `0.45` as `outputs/20260613_203825/game_sprite_asset/phase10_walk_shift4_birefnet_hist045_selected_proof_asset/`.
  - Status remains `selected_proof_only`, not `adopted_animation_candidate`.
- [x] Decide whether postprocess alone reaches adoption OK.
  - Decision: no. Conservative histogram matching improves consistency but leaves visible darkening; stronger matching triggers duplicate-silhouette gates.
  - Next PDCA must reduce color/lighting drift during generation, then use BiRefNet and mild histogram matching only as cleanup.
- [x] Run one generation-side drift-reduction probe after the postprocess boundary was found.
  - Tried `shift=3.2`, `cfg=2.4`, `steps=6`, `length=17`, `seed=717220` from the white-background prior-best start frame.
  - Result: raw output still darkened heavily and kept a grey/brown background panel.
  - Artifact gate rejected it: `retake_required: 3/17`, `repair_candidate: 14/17`, `duplicate_silhouette_area_high: 3`.
  - Decision: do not continue by simply lowering `shift/cfg` below the current `shift=4.0/cfg=2.8` proof; it reduces neither drift nor adoption risk enough.

## Mechanism Exploration: Reference-Conditioned Final Frames

- [x] Pivot away from small Wan parameter tuning as the primary work.
  - Small `cfg/shift/postprocess-strength` tuning has produced only local improvements.
  - The unresolved issue is structural: generated video gives motion but does not preserve 2D game sprite identity, color, and shape consistently enough.
- [x] Treat Wan output as a motion draft, not as the final asset source.
  - Wan may provide pose phase, silhouette motion, and timing.
  - Final game frames must be regenerated or corrected against the character reference and sprite constraints.
- [x] Inspect the local ComfyUI node environment for reference-conditioning tools.
  - Available: SDXL OpenPose ControlNet (`SDXL\OpenPoseXL2.safetensors`, `SDXL\t2i-adapter-openpose-sdxl-1.0.safetensors`), `ReferenceLatent`, several API-style reference nodes.
  - Not found in the local node list: IPAdapter-style local reference identity node.
  - Decision: first mechanism probe uses local SDXL OpenPose ControlNet plus source-image img2img; do not assume IPAdapter.
- [x] Build a minimal reference-conditioned regeneration probe.
  - Inputs:
    - character reference/start frame;
    - reusable walk pose-template frames as explicit motion controls;
    - source-image img2img latent to preserve identity.
  - Output:
    - regenerated frame sequence under `outputs/<timestamp>/...`;
    - `run_profile.json`, workflow JSON, contact sheet, preview GIF, and quality reports.
- [x] Run reference-image + reusable-walk-pose ControlNet probe.
  - Added `scripts/regenerate_pose_sequence_controlnet.py`.
  - Probe A: `denoise=0.55`, `controlnet_strength=0.78`, 8 walk phases.
    - Output: `outputs/20260613_204839/reference_pose_regen/walk_ref_pose_regen_openpose_d055_8f/`.
    - Result: identity/color/background stable but almost static; motion delta `0.389`.
  - Probe B: `denoise=0.72`, `controlnet_strength=1.10`, 8 walk phases.
    - Output: `outputs/20260613_205340/reference_pose_regen/walk_ref_pose_regen_openpose_d072_s110_8f/`.
    - Result: more variation, but not a readable walk; upper-body/arm redraw dominates, one visible yellow guide burn-in, artifact gate rejected `2/8`.
  - Decision: SDXL OpenPose img2img from a single reference is not sufficient as the final-frame mechanism by itself.
- [x] Compare the first mechanism against the current baseline.
  - Baseline A: current BiRefNet + histogram `0.45`.
  - Mechanism B: low-denoise img2img without reference lock.
  - Mechanism C1: source-image img2img + SDXL OpenPose ControlNet.
  - Result: C1 improves identity/color stability versus Wan drift, but fails motion readability and can burn guide pixels; reject as a standalone final-frame mechanism.
- [ ] Continue comparing mechanisms, not just settings.
  - Mechanism C2: true reference identity lock + pose/control, if local IPAdapter/InstantID/PuLID/reference-only equivalent can be installed.
  - Mechanism D: Wan motion guide only, then still-frame sprite regeneration per frame.
- [x] Install and verify a local reference identity-lock route.
  - Installed `comfyorg/comfyui-ipadapter` into local ComfyUI.
  - Downloaded `sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors`.
  - Added the CLIP-Vision expected filename `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` as a hardlink to the existing local CLIP-Vision model.
  - Updated `scripts/regenerate_pose_sequence_controlnet.py` to use `IPAdapterUnifiedLoader` + `IPAdapter`.
  - First failure was useful: `IPAdapterModelLoader` alone produced `IPAdapter model not present in the pipeline`; the current node version requires `IPAdapterUnifiedLoader`.
  - Second failure was useful: UnifiedLoader could not find CLIP-Vision until the expected filename was provided.
- [x] Verify IPAdapter identity lock against reusable walk controls.
  - Probe C: `outputs/20260613_211402/reference_pose_regen/walk_ipadapter_openpose_d072_c110_ip065_8f/`.
  - Result: identity/outfit stability improved and motion delta reached `3.717`, but existing walk OpenPose controls caused guide burn-in and front-view drift; artifact gate rejected.
  - Probe D: `outputs/20260613_212054/reference_pose_regen/walk_ipadapter_lower_cnet_probe_4f/`.
  - Result: lower ControlNet reduced burn-in but became too static; rejected.
- [x] Verify identity lock with an action-specific side-view motion template.
  - Built side-view control source: `outputs/20260613_212800/motion_source_video_pdca/motion_sources/sideview_walk_ipadapter_probe/`.
  - Best proof: `outputs/20260613_212815/reference_pose_regen/walk_ipadapter_sideview_pose_mid_8f/`.
  - Result: best current reference-conditioned still-frame proof; side-view walking reads better, identity is reasonably stable, and guide burn-in is not obvious.
  - Gate status: still rejected (`retake_required: 5/8`, foot/contact and duplicate-silhouette risks). Mark as `promising_probe`, not adoption OK.
- [ ] Next mechanism task: convert the promising IPAdapter + side-view pose route into an adoption candidate.
  - Build cleaner side-view motion controls with less arm/hand ambiguity and clearer lower-body phase separation.
  - Try 8-17 frame proofs before any 120-frame spend.
  - Target no visible guide burn-in, no duplicate lower limbs, no frame with crossed/vanishing feet, and artifact gate hard failures `0`.
  - If still rejected, compare IPAdapter Advanced or a second identity route (InstantID/PuLID/reference-only equivalent) only after the pose-control source is clean.
- [x] Adopt or reject the tested mechanism using sprite-asset criteria.
  - Pass requires stable character colors, stable outfit, readable walk motion, clean white/transparent background, no visible guide/control burn-in, and no duplicate lower limbs.
  - Reject if the method only makes prettier still frames while breaking temporal consistency or motion readability.
- [ ] If no local reference-conditioning node exists, implement the fallback mechanism.
  - Extract silhouette/motion guides from Wan/BiRefNet.
  - Generate key pose stills with novaOrangeXL using the guide as a composition reference where possible.
  - Use deterministic mask/color gates to identify whether this is worth installing additional models/nodes.
- [ ] Next mechanism candidate.
  - Do not continue plain OpenPose-only per-frame regeneration unless adding a stronger identity/reference mechanism.
  - Search locally for a true reference identity lock, or install/test one if needed: IPAdapter/InstantID/PuLID/reference-only equivalent for SDXL.
  - Alternative fallback: use Wan/BiRefNet output as the pose/silhouette input, but only after extracting a non-rendered guide that cannot burn into the output.

## Adoption Gate

- [ ] Promote to full source only after a passing short probe and one readable seed repeat.
- [ ] Normalize any 121-frame raw output to 120 frames before adoption review.
- [ ] Run full-source gates: stabilization, motion readability, region diagnostics, artifact mask-only gate, LocalVL secondary check, and Godot playback if available.
- [ ] Before 120-frame generation, produce a short proof that passes all of:
  - clean white/transparent background after foreground separation;
  - no visible later-frame character darkening by Agent visual review;
  - artifact gate `no_repair_needed` on all short-proof frames;
  - span hard failures `0`;
  - region diagnostics treated as review hints, with no obvious double-leg/foot/contact defect in contact sheet and GIF.
- [ ] Next generation-side retake matrix:
  - keep `single-keyframe Wan i2v` plus BiRefNet as mainline;
  - test drift-reduction settings before 1024 or 120-frame spend: flatter white-background prompt, start-frame quality, and short proof only;
  - avoid spending more on lower-than-`shift=4.0/cfg=2.8` probes unless another variable changes, because `shift=3.2/cfg=2.4` worsened darkening and artifact risk;
  - use masked histogram strength around `0.45` as the maximum safe cleanup unless a new proof changes the boundary;
  - reject candidates where correction strength above `0.45` is required to look acceptable.
- [ ] Status vocabulary:
  - `adopted_animation_candidate`: full 120-frame source passes deterministic gates and Agent visual review.
  - `selected_proof_only`: strong span exists but full source fails.
  - `rejected_diagnostic`: route/settings fail structurally or semantically.
