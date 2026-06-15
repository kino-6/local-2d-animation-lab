# Tasks: Style Lock And Frame Density Upgrade

## Upper Rule

- [x] Keep `character_sprite_asset_pack` as the production target.
- [x] Do not return to 120-frame research, Wan/video generation, ControlNet sweeps, or prompt-only animation experiments.
- [x] Treat the original illustration as an identity reference, not as the direct animation source.
- [x] Treat the accepted pack style as the primary source of truth for new action roughs.
- [x] Improve the two visible blockers: action-to-action style drift and low frame density in motion-heavy actions.

## Completed Baseline Preservation

- [x] Preserved the current committed pack route under `outputs/adoptable/character_sprite_asset_pack/`.
- [x] Kept all current actions loadable in Godot: `idle`, `walk`, `run`, `jump`, `hurt`, `dodge_backstep`, `parry_sword`, `attack_sword_light`.
- [x] Kept native `body`, `weapon`, and `effect` layers for `attack_sword_light` and `parry_sword`.
- [x] Kept composed frames as the compatibility output for Godot/Aseprite.

## Completed Style Reference Set

- [x] Added `assets/style_reference_sets/character_sprite_pack_v1/`.
- [x] Selected representative accepted frames from `idle`, `walk`, `run`, `attack_sword_light`, and `parry_sword`.
- [x] Generated `contact_sheet.png`.
- [x] Wrote `manifest.json` with source action/frame, identity cues, palette notes, and line/shape notes.
- [x] Documented that future roughs should use the accepted pack style, not only the original illustration.

## Completed Style Consistency Gate

- [x] Added deterministic style metrics in `scripts/build_character_sprite_asset_pack.py`.
- [x] Generated `outputs/adoptable/character_sprite_asset_pack/pack_review/style_consistency_report.json`.
- [x] Included per-action labels: `style_pass`, `style_review`, `style_retake_needed`.
- [x] Added style consistency summary to `manifest.json`, `production_gate.json`, and `pack_review/godot_import_manifest.json`.
- [x] Kept the gate honest: deterministic pass means no retake-level failure, while `style_review` still requires Agent visual review.

## Completed Frame Density Policy

- [x] Added action-level recommended source frame counts.
- [x] Stored the policy in docs and runtime metadata as review guidance, not a hard universal rule.
- [x] Added `frame_density_review` to action reports, runtime metadata, manifest entries, and Godot import metadata.
- [x] Rejected fake inbetweens based only on frame blending or cross-fade ghosts.
- [x] Preferred real/retimed source frames for anticipation, active, overshoot, and recovery.

## Completed Attack Sword Light Density Pass

- [x] Targeted `attack_sword_light` first because it exposes both style drift and motion density issues.
- [x] Planned and implemented a 16-frame source spec: ready, anticipation, draw back, windup, active, overshoot, recoil, settle, recover, ready return.
- [x] Created body-only 16-frame rough source under `assets/artist_authored_roughs/route_a_attack_sword_light_body_16frame_retime_20260615/`.
- [x] Kept sword and slash effects as native separate layers.
- [x] Updated active `hit_frames` to `[6, 7]`.
- [x] Regenerated action outputs and Godot previews.
- [x] Agent-reviewed `pack_review/all_actions_contact_sheet.png`; attack now reads as a 16-frame reviewable light sword action with separated weapon/effect timing.

## Completed Walk Density Decision

- [x] Reviewed current 8-frame walk as part of the all-actions contact sheet and Godot E2E.
- [x] Decided to keep walk at 8 frames for now.
- [x] Recorded that walk should only be retaken to 10/12 frames if foot contact, head stability, or loop smoothness clearly improves.

## Completed Godot Demo Review Tools

- [x] Added playback speed controls: 0.5x, 1x, 2x.
- [x] Added visible current action, frame index, speed, and loop/one-shot status.
- [x] Kept stable action shortcuts for the eight current actions.
- [x] Verified headless Godot pack validation.

## Completed Documentation And Skills

- [x] Updated `docs/character_identity_sprite_asset_pack.md`.
- [x] Updated `docs/local_skills/route-a-action-rough-to-pack/SKILL.md`.
- [x] Updated `docs/local_skills/route-a-layered-action-to-pack/SKILL.md`.
- [x] Recorded that production-ready means game-ready redesign consistency, not faithful animation of the original illustration.

## Completed External Knowledge Intake

- [x] Reviewed `NO6KIKO/gorest-2d-animation-spritesheet-generator` as a compatible external reference.
- [x] Incorporated non-conflicting spritesheet-first guidance:
  - complete sheet first, then split frames;
  - global character scale/root anchor across the sheet;
  - grid/cell detection before proportional splitting;
  - no duplicate first frame as the final loop frame.
- [x] Added `spritesheet_authoring_policy` to the pack manifest, runtime manifest, and Godot import manifest.
- [x] Recorded the guidance in docs and Route A Skill without reintroducing 120-frame/video research.

## Completed Tests

- [x] Updated `tests/test_build_character_sprite_asset_pack.py` for style consistency report, production gate style consistency, frame density metadata, and 16-frame attack.
- [x] Verified Godot headless import with `attack_sword_light` at 16 frames.
- [x] Ran focused Python, Godot, and diff checks.

## Verification

- [x] `uv run pytest tests\test_build_character_sprite_asset_pack.py`
- [x] `godot --headless --path godot --quit`
- [x] `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/character_sprite_asset_pack/manifest.json`
- [x] `git diff --check`

## Current ProductionOK Scope

- [x] `production_gate.json` decision is `production_ready`.
- [x] Current pack remains loadable in Godot.
- [x] Style drift is measured and documented.
- [x] Frame density expectations are explicit per action.
- [x] `attack_sword_light` is upgraded to a 16-frame reviewable production action.
- [x] No unsupported broad-generation route is reintroduced.

## Completed ComfyUI2025 Walk Engine-Loadable Candidate

- [x] Promoted the best ComfyUI2025 walk probe through a focused non-armor identity cleanup pass.
- [x] Added `scripts/recolor_gold_armor_to_dark_cloth.py` for dark cloth/leather recolor cleanup.
- [x] Added regression tests for the recolor route so skin-like pixels are not recolored as armor.
- [x] Added Godot single-sprite manifest validation for `asset_kind: 2d_game_sprite`.
- [x] Added `godot/tests/single_sprite_asset_runner.gd` for headless AnimatedSprite2D playback checks.
- [x] Created the current walk engine-loadable candidate at `outputs/20260616_production_pdca/20260616_010059/game_sprite_asset/comfyui2025_74298_walk_16frame_production_ok_candidate_v5/`.
- [x] Verified the candidate as 16 transparent frames, `256x384`, `preview.gif`, `spritesheet.png`, `contact_sheet.png`, and `manifest.json`.
- [x] Verified Godot playback starts from the single-sprite manifest.
- [x] Verified LocalVL scores: still quality 5/5, sprite fit 5/5, walk readability 5/5, identity consistency 5/5, background cleanliness 5/5.
- [x] Corrected the human review status to `game_loadable_but_identity_and_saturation_retake`; it is not ProductionOK because it reads like a different character and the saturation/value cleanup went too dull.

## Honest Remaining Notes

- [x] `style_review` labels remain for actions with large pose/scale variance; these are not retake blockers, but they should be checked visually before shipping in a real game.
- [x] The pack is ProductionOK for this MVP asset pack route, not proof that arbitrary future actions can be generated automatically.
- [x] The ComfyUI2025 walk candidate still inherits generated costume silhouette choices and over-darkened color; exact identity requires a curated design sheet or manual edit before animation.
- [x] LocalVL identity scoring is a semantic signal only; human visual identity and palette review overrides it for adoption decisions.

## Completed Reference-Faithful Design Source Pivot

- [x] Stopped treating the over-dark walk package as a visual ProductionOK candidate.
- [x] Generated a new reference-faithful design sheet before motion work.
- [x] Saved the design sheet at `outputs/20260616_design_sheet_pdca/20260616_0100_reference_faithful_design_sheet/design_sheet_v1.png`.
- [x] Added `scripts/extract_design_sheet_side_view.py` to crop and alpha-extract the right-facing full-body view.
- [x] Added tests for the side-view extraction route.
- [x] Created the current side-view design source at `outputs/20260616_design_sheet_pdca/20260616_0100_reference_faithful_design_sheet/side_view_v1c_alpha/side_view_v1c_alpha.png`.
- [x] Verified the side-view source has transparent corners, no neighboring-view leakage, and preserved high-contrast saturation/value better than the old walk package.
- [x] Documented the result in `docs/comfyui2025_reference_faithful_design_sheet_pdca.md`.

## Next Motion PDCA From Design Source

- [x] Incorporated user review that `side_view_v1c_alpha.png` reads too much like a biker.
- [x] Generated Nun + gothic hunter design variants.
- [x] Selected `outputs/20260616_design_sheet_pdca/20260616_081036_nun_bloodborne_design_sheet/side_view_v3_nun_hunter_walkable/side_view_v3_nun_hunter_walkable.png` as the next design-source candidate.
- [x] Recorded that v3 is closer to Nun + Bloodborne-like identity, while robe panels make walk animation harder than the biker-like pants version.
- [x] Incorporated user review that long robes raise walk animation difficulty.
- [x] Generated a skirt + boots nun variant that keeps the mood while making legs/feet readable.
- [x] Selected `outputs/20260616_design_sheet_pdca/20260616_0820_nun_skirt_boots_design_sheet/side_view_v4_nun_skirt_boots/side_view_v4_nun_skirt_boots.png` as the next walk-cycle source.
- [ ] Use `side_view_v4_nun_skirt_boots.png` as the source for the next walk cycle attempt.
- [ ] Add an identity/palette gate before packaging: reject outputs that look like a different character or collapse into dull low-value black.
- [ ] Preserve white hair, black glossy hood, red collar, gold forehead band, and sleepy pale face across frames.
- [ ] Preserve skirt hem, black stockings, and boots; do not accept pants conversion, robe-only silhouette, biker gear, generic knight/rogue redesigns, heavy shoulder armor drift, or weapon/action expansion.
- [ ] Keep legs/feet readable for contact and passing poses.
- [ ] Package only after identity and palette pass, then run Godot playback validation.
