# Tasks: High-Quality Walk Animation Asset

This file is the active checklist for improving walk animation quality.

Keep detailed experiment logs in `docs/next_phase_run_generation_pdca_report.md`.
Keep local generated outputs under ignored output/review directories.

## Top Rule

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet or shake.
- [x] Keep the main route on generated video/control workflows, not rig/cutout animation.
- [x] Preserve 120-frame-class source generations; selected spans are evidence, not the final asset target.
- [x] Prefer `novaOrangeXL_v120.safetensors` for still-image/full-body reference work.
- [x] Prefer the staged Wan image-to-video route for temporal motion when subject preservation matters; keep VACE for controlled probes or later masked refinements.

## Current Baseline

- [x] 512 walk structural baseline exists: `review_packages/synthetic_sideview_walk_v4_identity_prompt_seed717220_vace_len121_full_source_review_20260611_182900`.
- [x] 512 baseline has full-source artifact gate `retake_required: 0/121`.
- [x] 768 quality proof exists: `review_packages/walk_v4_identity_seed717220_vace_len121_768_lower_control_selected_quality_review_20260611_215932`.
- [x] 768 selected proof has clearer face/outfit/limbs than the 512 baseline.
- [x] 768 selected proof has selected-span artifact gate `no_repair_needed: 16/16` and Godot `ok: true`.
- [x] 768 full source is not adopted because full-source gate still has `retake_required: 2/121`.

## Non-Goals

- [x] Do not claim selected 16-frame proof as full 120-frame adoption.
- [x] Do not solve guide-line leakage by unsafe white cleanup that touches skin, legs, hands, or outfit.
- [x] Do not keep searching seeds/prompts before improving input reference, control representation, or motion source.
- [x] Do not switch back to rig/cutout animation as the primary answer.
- [x] Do not accept a candidate only because heuristic gates pass; contact sheet and preview review are required.
- [x] Do not treat prompt-only tuning as the main quality-improvement strategy.

## External Research Baseline

Use the following outside projects as the next planning anchor:

- [x] `comfyui-2d-character-pipeline`: inspect local applicability of the staged ComfyUI route: pose edit, Wan video, BiRefNet, sprite sheet export, layered outputs.
- [x] `Sprite Sheet Diffusion`: translate the task definition into this project: reference image plus pose sequence produces a coherent sprite-sheet action sequence.
- [x] `MusePose`: evaluate pose alignment as a first-class preprocessing step before generation.
- [x] `MimicMotion`: evaluate confidence-aware pose guidance and regional emphasis as the model-side lesson for hands/feet/legs.
- [x] `Wan2.2 Animate`: evaluate whether its animation/replacement preprocessing is a better local subject-preservation route than current VACE.
- [x] Keep all imported lessons local-first; external services may inform UX or evaluation, but not become the required production path.

## Phase 1: Full-Body Character Reference

- [x] Generate or curate a high-quality 1024x1024 full-body side-view character reference from `assets/reference/Anima_00013_.png`.
- [x] Keep the character identity traits: brown bob hair, pink hair clip, sailor uniform, red necktie, dark socks, brown loafers.
- [x] Produce at least two full-body reference candidates: strict side profile and slight 3/4 side.
- [x] Select one reference candidate based on full-body readability, stable face, complete feet, and clean white/transparent background.
- [x] Run start-frame quality checks on the selected full-body reference.
- [x] Save a compact reference review package and record the selected path in the PDCA report.

## Phase 2: Control Representation

- [x] Add `wan_walk_lower` as a lower-body-focused VACE control style.
- [x] Add `--analysis-max-size` so 768/1024 analysis remains practical while preserving original output frames.
- [x] Create a soft/silhouette walk control style that avoids visible RGB skeleton lines.
- [x] Create a foot-contact control layer for left/right foot placement and ground contact.
- [x] Compare `wan_balanced`, `wan_walk_lower`, and the new soft/silhouette control at the same seed and resolution.
- [x] Reject any control style that leaks visible guide lines into hands, legs, or background.
- [x] Promote one control style as the current walk-quality default only after selected-span gate and visual review pass.
- [x] Design a second control-retake that preserves motion without copying guide shapes into the character.

## Phase 3: Motion Source Quality

- [x] Define visual criteria for a good walk source: foot contact, weight shift, leg alternation, arm swing, loop closure.
- [x] Build or import at least one improved 120-frame walk motion source using those criteria.
- [x] Keep the existing synthetic v4 edge-stride source as the baseline comparator.
- [x] Compare motion sources using foreground-normalized motion, contact-sheet review, and Godot playback.
- [x] Reject sources with foot sliding, too-static hips, unstable body scale, or unclear contact phases.
- [x] Select one motion source for full 120-frame generation.

## Phase 4: 768/1024 Generation PDCA

- [x] Run a 768x768 full 121-frame walk generation using the selected full-body reference, selected control style, and selected motion source.
- [x] Run BiRefNet foreground separation for the full 121-frame generation.
- [x] Run full-source artifact gate with `--analysis-max-size 512`.
- [x] Run span selection with `--motion-metric foreground` and `--analysis-max-size 512`.
- [x] Export one selected-span review package with Godot validation.
- [x] If 768 full source reaches `retake_required: 0/121`, export a full-source review package.
- [x] If 768 selected proof improves but full source fails, document exact failing frames and failure type.
- [x] Run one 1024x1024 short probe only after 768 has a stable selected proof.
- [x] Do not run 1024 full 121-frame generation until short probe shows better visual quality without new structural failures.

## Phase 5: Quality Gates

- [x] Add explicit detection or review labels for visible guide-line leakage.
- [x] Add explicit review labels for skin-colored afterimage near thighs/feet.
- [x] Add explicit review labels for pale lower-body afterimages that the old mask gate missed.
- [x] Add explicit review labels for foot sliding and weak contact.
- [x] Add explicit review labels for face/detail readability at game-asset scale.
- [x] Keep artifact gate as a blocker for duplicate silhouettes, duplicate legs, large masks, and broken structure.
- [x] Treat visual review as blocking when the gate passes but the animation still looks low quality.
- [x] Record each candidate as `adopted_full_source`, `selected_proof_only`, `diagnostic`, or `rejected`.

## Phase 6: Adoption Criteria

- [x] Full 121-frame source package exists at 768 or higher.
- [x] Current strict labeled full-source artifact gate has `retake_required: 0/121`.
- [x] Full contact sheet review completed: recurring pale lower-body afterimages remain, so the candidate is not adopted.
- [x] Preview GIF review completed: the sequence reads much more like a walk than the VACE route, but remains `selected_proof_only`.
- [x] Character identity remains consistent across the full source.
- [x] Godot validation passes for the full-source package.
- [x] PDCA report states why the current candidate is better than the 512 baseline while still not adopted.
- [x] Skill document names the current walk-quality workflow and known rejection boundaries.

## Phase 7: External Workflow Audit

- [x] Clone or inspect `comfyui-2d-character-pipeline` without mixing its generated outputs into this repository.
- [x] Map its workflow stages to this project's stages: reference preparation, pose/control authoring, video generation, foreground extraction, sprite sheet export, review package.
- [x] Record which ComfyUI nodes/models are already installed locally and which are missing.
- [x] Identify whether its Wan workflow uses stronger subject preservation than our current VACE route.
- [x] Identify whether its layered sprite-sheet output can become a later export stage without changing the core generation route.
- [x] Write a short audit section in `docs/next_phase_run_generation_pdca_report.md`.

## Phase 8: Reference and Pose Alignment

- [x] Implement or prototype a pose-alignment report inspired by MusePose: compare source pose scale, hip height, shoulder width, ankle baseline, and facing direction against the selected full-body reference.
- [x] Add an alignment transform for imported or synthetic pose sequences before rendering control video.
- [x] Add per-frame alignment diagnostics to the motion source report.
- [x] Reject motion sources whose aligned foot baseline or body scale drifts beyond a configured threshold.
- [x] Rebuild the current v4 and v5 walk controls through the alignment step and compare against the existing controls.

## Phase 9: Confidence-Aware Control

- [x] Extend local pose templates or imported pose JSON to carry confidence values for hips, knees, ankles, shoulders, elbows, wrists, and head.
- [x] Render confidence-aware lower-body controls where uncertain keypoints are dimmer and high-confidence foot contact is clearer.
- [x] Add regional emphasis for feet/ankles and hands without drawing copyable guide shapes into the character area.
- [x] Compare current `vace_walk_lower_hint` against at least one confidence-aware variant at the same seed, length, and resolution.
- [x] Gate the comparison on foreground preservation, guide leakage, foot readability, and foreground-normalized motion.

## Phase 10: Subject Preservation Retake

- [x] Solve the latest blocker by switching route: v5/contact-swing VACE foreground shrinkage is bypassed by single-keyframe Wan i2v, which keeps full-source foreground readable.
- [x] Test a subject-preservation retake that keeps v5 motion but prevents faint legs/feet and foreground shrinkage.
- [x] Test at least one intermediate VACE strength between `0.55` and `0.75`.
- [x] Test one stronger-reference route before more motion-source changes: improved start frame, subject mask/reference conditioning, or Wan2.2 Animate if locally feasible.
- [x] Do not run Image2Image polish until the source generation has readable legs/feet and full-source foreground stability.
- [x] Do not promote the new candidate despite `retake_required: 0/121`, because strict visual labels found recurring lower-body pale afterimages.

## Phase 11: Sprite-Sheet Task Framing

- [x] Create a benchmark manifest that matches Sprite Sheet Diffusion's framing: `reference_image`, `pose_sequence`, `action_name`, `expected_sprite_sheet`, `review_outputs`.
- [x] Add a compact comparison table for every walk candidate: source route, control style, resolution, length, motion score, retake count, candidate status, visual decision.
- [x] Keep selected 16-frame proofs as evidence, but require a separate full 120-frame adoption row.
- [x] Add placeholders for later actions beyond walk: run, idle, sword attack, axe attack, bow attack, hit light, hit heavy, knockback.

## Current Next Action: Research-Grounded Plan

- [x] Start with Phase 1: create a high-quality full-body side-view reference before running more broad Wan seed/prompt searches.
- [x] Continue with Phase 2: create a soft/silhouette walk control style that avoids visible RGB skeleton-line leakage.
- [x] Continue Phase 2 retake: reduce copied guide-shape leakage before promoting a walk-quality default.
- [x] Continue with Phase 5/6: add explicit visual labels for the remaining foot-shadow/low-motion quality limits before calling the full 121-frame source adopted.
- [x] Next: improve the 120-frame walk motion source so the selected span clears foreground motion without increasing foot-shadow/contact artifacts.
- [x] Next: rerun 768 full-source generation with the improved motion source and require labeled full-source gate `retake_required: 0/121`.
- [x] Next: use `run_synthetic_sideview_walk_v5_contact_swing` with `--vace-strength 0.55` as the next full-source 121-frame probe; short selected proof is `review_packages/phase3_v5_contact_swing_vace055_selected_review_20260612_003057`.
- [x] Next: solve full-source foreground preservation; single-keyframe Wan i2v solved foreground shrinkage but exposed pale lower-body afterimages as the next blocker.
- [x] Next: test a subject-preservation retake that keeps v5 motion while preventing faint legs/feet and foreground shrinkage.
- [x] Next: audit `comfyui-2d-character-pipeline` and map its staged workflow to our local pipeline.
- [x] Next: implement pose-alignment diagnostics before running more generation.
- [x] Next: implement confidence-aware control rendering for feet/legs before running another broad seed search.
