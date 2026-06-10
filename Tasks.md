# Tasks: novaOrangeXL + ControlNet Sprite Asset Workflow

## Scope Guard

- [x] Main path is `novaOrangeXL + ControlNet(OpenPose)`.
- [x] Input image is treated as a character design reference, not as pixels to shake or rig directly.
- [x] Shared OpenPose keypoint templates are first-class assets.
- [x] Rig-based generation is not the primary output path.
- [x] Final quality is judged by contact sheets and Godot playback, not by single-frame beauty alone.

## Non-Goals

- [x] Do not make rigged puppet animation the main generation method.
- [x] Do not optimize around procedural stick-figure or cutout demos as final artifacts.
- [x] Do not treat random frame-to-frame image generation as an animation workflow.
- [x] Do not accept outputs only because a heuristic score is high.
- [x] Do not judge quality from one still image.
- [x] Do not skip contact-sheet review.
- [x] Do not skip Godot playback validation for adopted candidates.
- [x] Do not use vague actions such as generic `attack` or generic `hit` as final evaluation targets.
- [x] Do not hide failed candidates; rejected outputs need failure reasons.
- [x] Do not commit heavy generated output folders unless explicitly requested.
- [x] Do not depend on cloud services for the core workflow.
- [x] Do not introduce a new model or checkpoint as the default without comparing it against `novaOrangeXL`.
- [x] Do not let visual polish override animation readability.
- [x] Do not let animation readability override character identity preservation.
- [x] Do not add broad refactors unrelated to the ControlNet asset workflow.

## Target Output Contract

- [x] Define the required output folder layout per action.
- [x] Ensure each action run writes `frames/*.png`.
- [x] Ensure each action run writes `contact_sheet.png`.
- [x] Ensure each action run writes `preview.gif`.
- [x] Ensure each action run writes `spritesheet.png`.
- [x] Ensure each action run writes `manifest.json`.
- [x] Ensure each action run writes `evaluation_report.json`.
- [x] Ensure each action run records the pose template used.
- [x] Ensure each PDCA run writes `pdca_log.json`.
- [x] Set the main workflow output target to 120 frames.
- [x] Keep frame thinning/downsampling out of this workflow.

## Action Set

- [x] Support `walk`.
- [x] Support `idle`.
- [x] Support `attack_sword`.
- [x] Support `attack_axe`.
- [x] Support `attack_bow`.
- [x] Support `hit_light`.
- [x] Support `hit_heavy`.
- [x] Support `hit_knockback`.

## Pose Template Assets

- [x] Create `pose_templates/` directory.
- [x] Define pose template schema for one frame.
- [x] Define pose template schema for one action sequence.
- [x] Add metadata fields: `action`, `variant`, `frame_index`, `phase`, `keypoints`, `notes`.
- [x] Add template validation script.
- [x] Add OpenPose render script to convert template JSON to ControlNet input images.
- [x] Add contact sheet generation for pose templates.
- [x] Create initial `walk` pose template sequence.
- [x] Create initial `idle` pose template sequence.
- [x] Create initial `attack_sword` pose template sequence.
- [x] Create initial `attack_axe` pose template sequence.
- [x] Create initial `attack_bow` pose template sequence.
- [x] Create initial `hit_light` pose template sequence.
- [x] Create initial `hit_heavy` pose template sequence.
- [x] Create initial `hit_knockback` pose template sequence.
- [x] Add tests for pose template loading and validation.

## Shared Keypoint Rules

- [x] Define common skeleton proportions for the reference character.
- [x] Define common ground line and foot contact rules.
- [x] Define common character center and scale rules.
- [x] Define common walk cycle phases.
- [x] Define common attack phases: ready, anticipation, active, follow-through, recover.
- [x] Define common hit phases: neutral, impact, recoil, peak, recover.
- [x] Define weapon-hand rules for sword.
- [x] Define weapon-hand rules for axe.
- [x] Define bow draw and release rules.
- [x] Define knockback displacement rules.

## novaOrangeXL Generation Workflow

- [x] Add a ControlNet workflow preset for `novaOrangeXL`.
- [x] Confirm checkpoint name and ComfyUI model path assumptions.
- [x] Add CLI option for selecting pose template action.
- [x] Add CLI option for selecting pose template frame directory.
- [x] Add CLI option for `novaOrangeXL` preset.
- [x] Add prompt pack generation from `AnimationSpec`.
- [x] Add per-action positive prompt fragments.
- [x] Add per-action negative prompt fragments.
- [x] Add seed strategy for identity stability.
- [x] Add ControlNet strength strategy per action.
- [x] Add CFG and step defaults for `novaOrangeXL`.
- [x] Save generated ComfyUI workflow JSON per run.
- [x] Save the exact prompt and ControlNet image per frame.

## Character Reference Handling

- [x] Extract character profile from reference image.
- [x] Record visible traits: hair, outfit, palette, silhouette, accessories.
- [x] Add identity preservation prompt fragment.
- [x] Add negative prompt against extra characters.
- [x] Add negative prompt against background clutter.
- [x] Add size and full-body framing constraints.
- [x] Investigate local reference guidance option: IP-Adapter.
- [x] Investigate local reference guidance option: character LoRA.
- [x] Decide whether reference guidance is required for the first stable workflow.

## Breakage Evaluation

- [x] Detect missing or tiny foreground character.
- [x] Detect multiple foreground characters.
- [x] Detect background contamination.
- [x] Detect frame-to-frame character center drift.
- [x] Detect frame-to-frame character scale drift.
- [x] Detect frame-to-frame color drift.
- [x] Detect weak motion for non-idle actions.
- [x] Detect poor loop closure for `walk` and `idle`.
- [x] Detect pose/action mismatch against template phase.
- [x] Detect likely hand/weapon breakage for attack variants.
- [x] Detect likely bow/string/arrow breakage for `attack_bow`.
- [x] Detect weak recoil or displacement for hit variants.
- [x] Emit actionable issue codes, not only prose.
- [x] Add tests for each evaluation issue code.

## Visual Review Assets

- [x] Generate contact sheet for raw frames.
- [x] Generate contact sheet with effect layers when applicable.
- [x] Generate pose template contact sheet.
- [x] Generate side-by-side sheet: pose template vs generated frame.
- [x] Generate preview GIF at game-like timing.
- [x] Generate Godot-compatible manifest.
- [x] Add a summary report that lists adopted and rejected candidates.

## Retake Policy

- [x] If pose/action mismatch, adjust keypoint template first.
- [x] If identity drift, adjust prompt, seed, or reference guidance.
- [x] If extra character appears, strengthen negative prompt and framing.
- [x] If weapon breaks, add weapon-specific prompt/control guidance.
- [x] If motion is weak, increase pose contrast in keypoint template.
- [x] If frame jitter is high, lock seed and reduce stochastic variation.
- [x] If loop closure is weak, revise first/last pose templates.
- [x] Record the retake reason in `pdca_log.json`.

## Godot E2E Validation

- [x] Validate one generated manifest in Godot headless.
- [x] Validate all adopted candidates from PDCA summary.
- [x] Confirm frame count.
- [x] Confirm frame size.
- [x] Confirm transparent frames load correctly.
- [x] Confirm animation playback starts.
- [x] Confirm composited effect frames are used for attack/hit previews.
- [x] Save Godot validation result JSON.

## First Proof: attack_sword

- [x] Create `attack_sword` OpenPose template sequence.
- [x] Render `attack_sword` pose images.
- [x] Generate `attack_sword` frames with `novaOrangeXL + ControlNet`.
- [x] Create contact sheet and preview GIF.
- [x] Run breakage evaluation.
- [x] Run Godot validation.
- [x] Perform at least three retakes based on evaluation results.
- [x] Select one adopted candidate.
- [x] Document why rejected candidates failed.

## Expansion After attack_sword

- [x] Apply workflow to `walk`.
- [x] Apply workflow to `hit_heavy`.
- [x] Apply workflow to `attack_bow`.
- [x] Apply workflow to remaining action variants.
- [x] Compare shared template reuse across actions.
- [x] Extract common prompt fragments.
- [x] Extract common retake rules.

## Skill Documentation

- [x] Create `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`.
- [x] Write top-level rule: no rig-first generation.
- [x] Write `novaOrangeXL` default settings.
- [x] Write pose template naming rules.
- [x] Write action generation workflow.
- [x] Write breakage evaluation checklist.
- [x] Write retake decision table.
- [x] Write Godot validation procedure.
- [x] Write adopted/rejected artifact criteria.
- [x] Link the Skill from `README.md`.

## Repository Cleanup

- [x] Mark previous rig outputs as historical experiments in docs.
- [x] Keep rig backend only as optional diagnostic/comparison tooling.
- [x] Make ControlNet workflow the documented main path.
- [x] Keep generated outputs ignored by git.
- [x] Commit source code, templates, docs, and tests only.

## Artifact Repair And Quality Gate

- [x] Add explicit artifact repair workflow for post-video frames.
- [x] Generate local repair masks for small ghost trails and detached artifacts.
- [x] Keep protected character pixels out of the repair mask.
- [x] Use ComfyUI `VAEEncodeForInpaint` for masked local cleanup.
- [x] Composite repaired pixels only inside the explicit mask.
- [x] Block inpaint when the repair mask is too broad.
- [x] Detect strong duplicate silhouette risk.
- [x] Detect double-foot or duplicate-leg risk.
- [x] Detect fragmented weapon risk for sword-style outputs.
- [x] Treat duplicate legs, strong afterimages, and broken weapons as retake/retrim failures.
- [x] Verify masked inpaint on the current walk/run refinement output.
- [x] Verify weapon gate on the current sword refinement output.
- [x] Probe Wan `continue_motion_max_frames` as a generation-side afterimage control.
- [x] Document why masked inpaint helps only small artifacts.
- [x] Document why large duplicate silhouettes and weapon structure failures must return to generation control.

## Done Criteria

- [x] `attack_sword` has a complete ControlNet-based PDCA run.
- [x] At least one generated candidate is adopted with clear evidence.
- [x] At least two rejected candidates have recorded failure reasons.
- [x] Pose templates are reusable and versioned in repo.
- [x] Evaluation report gives actionable retake guidance.
- [x] Godot validation passes for the adopted candidate.
- [x] Skill documentation is sufficient to repeat the workflow locally.
- [x] `uv run pytest` passes.
