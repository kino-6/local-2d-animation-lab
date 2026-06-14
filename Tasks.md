# Tasks: Walk 8-Frame Side-View Baseline MVP Quality Pass

Archived checkpoint:

```text
docs/archive/Tasks_20260614_conservative_walk_endpoint_gate_completed.md
```

## Upper Rule

- [x] Generate local-first 2D game assets from one character reference image plus a natural-language request.
- [x] For this MVP, normalize any request to a fixed walk spec:
  - `action: walk`
  - `direction: right`
  - `frame_count: 8`
  - `view: side`
  - `loop: true`
  - `background: transparent`
- [x] Produce one small game-loadable artifact package before returning to broad quality research.

## Current Quality Finding

- [x] The first preview GIF is not evaluation-worthy as animation.
- [x] Root cause: it preserves package shape but only shifts a cutout; it does not create readable contact, passing, and opposite-contact walk poses.
- [x] A better MVP should preserve reference identity cues while making the legs/feet carry a clear 8-frame side-view walk cycle.
- [x] Second root cause: direct cutout preservation keeps fidelity but fights usable animation; a stylized, reference-derived sprite can be more game-friendly.
- [x] This branch remains a small adoptable-asset MVP branch, not a return to broad 120-frame/video research.

## Do Not Do In This Task

- [x] Do not generate 120-frame outputs.
- [x] Do not run Wan or video generation.
- [x] Do not attempt attack, hit, run, weapon, or multi-action generation.
- [x] Do not add new model integrations.
- [x] Do not chase production-grade art quality, but do require animation-readable walk poses.

## Previous Plan

- [x] Add `scripts/build_walk_8frame_baseline.py`.
- [x] Generate a deterministic or semi-deterministic 8-frame walk baseline from one reference cutout.
- [x] Write outputs only to:

```text
outputs/adoptable/walk_8frame_sideview_baseline/
```

- [x] Export:
  - `frames/walk_000.png` through `frames/walk_007.png`
  - `spritesheet.png`
  - `preview.gif`
  - `contact_sheet.png`
  - `manifest.json`
  - `notes.md`
- [x] Add tests for the output contract.
- [x] Add `docs/walk_8frame_baseline_mvp.md`.
- [x] Remove stale local diagnostic output folders after durable findings are already recorded.
- [x] Run focused tests.
- [x] Review the generated package honestly as `baseline_not_production`.

## Quality Pass Plan

- [x] Replace whole-lower-body shifting with a reference-preserving upper-body plus synthetic leg-cycle renderer.
- [x] Derive simple skin, sock, shoe, and outline colors from the reference cutout.
- [x] Keep exactly one character on a stable transparent 512x512 canvas.
- [x] Generate 8 explicit walk phases:
  - contact
  - down
  - passing
  - up
  - opposite contact
  - opposite down
  - opposite passing
  - opposite up
- [x] Add deterministic motion metrics to `manifest.json`.
- [x] Add tests that catch static or near-static preview output.
- [x] Regenerate `outputs/adoptable/walk_8frame_sideview_baseline/`.
- [x] Agent-review `contact_sheet.png` and honestly label the result.
- [x] If reference-preserving cutout still looks puppet-like, switch the default renderer to a stylized reference-derived sprite cycle.

## Success Criteria

- [x] Exactly eight PNG frames exist.
- [x] All frames share one canvas size.
- [x] PNG frames have transparent backgrounds.
- [x] `spritesheet.png`, `preview.gif`, `contact_sheet.png`, `manifest.json`, and `notes.md` exist.
- [x] Manifest marks `route_status` as `baseline_not_production`.
- [x] The package contains one character and no duplicate/crowd-like generation failure.
- [x] No ComfyUI, Wan, video, 120-frame, attack, hit, run, or weapon path is executed.
- [x] Frames are visibly different enough to represent a walk cycle, not just a wobbling cutout.
- [x] Contact sheet shows alternating contact/passing leg poses.
- [x] `manifest.json` records motion/readability metrics.

## Result

- [x] Implemented deterministic baseline script:
  - `scripts/build_walk_8frame_baseline.py`
- [x] Adopted MVP package:
  - `outputs/adoptable/walk_8frame_sideview_baseline/`
- [x] Documentation:
  - `docs/walk_8frame_baseline_mvp.md`
- [x] Tests:
  - `uv run pytest tests\test_build_walk_8frame_baseline.py tests\test_output_layout_policy.py`
  - `5 passed`
- [x] Honest label:
  - `baseline_not_production`

## Quality Pass Result

- [x] Default renderer changed to:
  - `stylized_sprite_cycle`
- [x] Adopted output regenerated:
  - `outputs/adoptable/walk_8frame_sideview_baseline/`
- [x] Manifest visual decision:
  - `review_worthy_mvp_not_production`
- [x] Focused tests:
  - `uv run pytest tests\test_build_walk_8frame_baseline.py tests\test_output_layout_policy.py`
  - `5 passed`
- [x] Honest assessment:
  - Better than the previous preview because the contact/passing/opposite-contact phases are visible.
  - Still not production art and not a faithful redraw of the original reference.
  - This route is useful as a small game-loadable MVP and a clearer baseline for later quality work.

## Skeleton Quality Pass

- [x] Keep the route scoped to `walk_8frame_sideview_baseline`.
- [x] Keep exactly eight right-facing side-view frames.
- [x] Keep transparent PNG frames and the existing output contract.
- [x] Do not add ComfyUI, Wan, ControlNet, video generation, or new model integrations.
- [x] Add an explicit small skeleton model for the stylized renderer.
- [x] Define stable `ground_y`.
- [x] Define exactly these phases:
  - `contact`
  - `down`
  - `passing`
  - `up`
  - `opposite_contact`
  - `opposite_down`
  - `opposite_passing`
  - `opposite_up`
- [x] Add contact-foot labels per frame.
- [x] Keep contact feet planted on contact/down frames and lift only swing feet on passing/up frames.
- [x] Add small hip bob while keeping head mostly stable.
- [x] Strengthen torso/hip/neck/head connection.
- [x] Add knee bends and heel/toe-oriented foot shapes.
- [x] Improve arm swing with upper/lower arm segments and plausible hand positions.
- [x] Preserve identity cues:
  - pink hair
  - side profile
  - sailor-style white top
  - red tie
  - dark socks
  - brown shoes
- [x] Add `docs/walk_8frame_review_checklist.md`.
- [x] Add `walk_readability` to `manifest.json`.
- [x] Update tests for `walk_readability`, phase names, output contract, and no backend invocation.
- [x] Regenerate `outputs/adoptable/walk_8frame_sideview_baseline/`.
- [x] Agent-review `contact_sheet.png`.

## Skeleton Quality Pass Result

- [x] Renderer now uses a small deterministic skeleton with:
  - stable `ground_y`;
  - explicit phase names;
  - contact-foot labels;
  - head and hip y-range metadata;
  - foot-lock expectation;
  - loop expectation.
- [x] Manifest label remains:
  - `route_status: baseline_not_production`
  - `visual_decision: review_worthy_mvp_not_production`
- [x] Output remains:
  - `outputs/adoptable/walk_8frame_sideview_baseline/`
- [x] Focused tests:
  - `uv run pytest tests\test_build_walk_8frame_baseline.py tests\test_output_layout_policy.py`
  - `5 passed`
- [x] Honest assessment:
  - More reviewable than the crude geometric puppet because contact/down foot lock, hip bob, head stability, knee bends, and arm opposition are explicit.
  - Still not production art.

## Shape Polish Pass

- [x] Keep all hard constraints from the 8-frame walk MVP.
- [x] Do not change the output route or frame contract.
- [x] Preserve the explicit skeleton/foot-lock model.
- [x] Replace stick-like limb drawing with tapered filled limb segments.
- [x] Add clearer thigh/calf separation while keeping dark socks visible.
- [x] Reduce oversized or boot-like foot impression with smaller right-facing shoe shapes.
- [x] Strengthen torso/hip continuity with a waist/hip block under the sailor top.
- [x] Improve arms with upper/lower arm volume and elbow bend.
- [x] Keep head mostly stable and visually connected through neck/collar.
- [x] Add style/polish metadata to `manifest.json`.
- [x] Update tests to verify the polish metadata and unchanged contract.
- [x] Regenerate `outputs/adoptable/walk_8frame_sideview_baseline/`.
- [x] Agent-review `contact_sheet.png`.

## Shape Polish Pass Result

- [x] Renderer polish metadata:
  - `limb_renderer: tapered_filled_segments`
  - `arm_model: upper_lower_segments_with_elbow`
  - `leg_model: thigh_and_sock_segments_with_knee`
  - `shoe_model: compact_right_facing_heel_toe`
  - `torso_hip_connection: waist_block_under_sailor_top`
- [x] Focused tests:
  - `uv run pytest tests\test_build_walk_8frame_baseline.py tests\test_output_layout_policy.py`
  - `5 passed`
- [x] Honest assessment:
  - Arms and legs read less like single-pixel sticks.
  - Shoe/ankle connection is cleaner than the skeleton pass.
  - The sprite remains a deterministic MVP baseline, not production art.

## Stop And Pivot

- [x] Stop minor improvements to the deterministic stylized renderer.
- [x] Mark `walk_8frame_sideview_baseline` as:

```text
baseline_complete_but_not_artistically_viable
```

- [x] Keep the route as a technical baseline only.
- [x] Do not add ComfyUI, Wan, video generation, ControlNet, or new model integrations for this pivot.
- [x] Do not generate new assets for this pivot.
- [x] Add `docs/next_asset_generation_routes.md`.
- [x] Compare exactly three next routes:
  - Route A: Artist-authored base sprite + AI-assisted cleanup.
  - Route B: Reference-derived character redesign + deterministic animation.
  - Route C: Pose-template image generation per keyframe.
- [x] Recommend Route A as the next implementation target.

## Route A Implementation

- [x] Implement `artist_authored_8frame_walk_cleanup` as the next route.
- [x] Keep the current deterministic renderer stopped as a technical baseline only.
- [x] Require exactly 8 artist-authored PNG rough frames as input.
- [x] Keep human control over pose and silhouette.
- [x] Limit automation to deterministic cleanup and packaging.
- [x] Do not add ComfyUI, Wan, ControlNet, video generation, or new model integrations.
- [x] Do not generate 120-frame outputs.
- [x] Do not generate new poses or character art.
- [x] Add `scripts/package_artist_authored_walk_cleanup.py`.
- [x] Add `docs/artist_authored_8frame_walk_cleanup.md`.
- [x] Add tests for:
  - exact 8-frame input;
  - output layout;
  - transparent PNG frames;
  - spritesheet, preview GIF, contact sheet, manifest, cleanup report;
  - backend usage flags all false;
  - rejection of wrong frame count.

## Route A Generated Rough Candidate

- [x] Generate one anime-style 4x2 walk-cycle source sheet as a rough candidate.
- [x] Generate a second stricter game-sprite rough candidate after v1 proved usable but still too illustration-like.
- [x] Store the generated source and prompt under:

```text
assets/artist_authored_roughs/imagegen_walk_8frame_20260614/
assets/artist_authored_roughs/imagegen_walk_8frame_20260614_v2/
```

- [x] Split the source sheet into exactly 8 rough PNG frames.
- [x] Package the rough candidate through `artist_authored_8frame_walk_cleanup`.
- [x] Store the reviewable package under:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/
```

- [x] Mark the manifest source honestly as:

```text
source_kind: ai_generated_rough_for_route_a_v2
```

- [x] Add green-dominance chroma cleanup after v2 showed that visually green backgrounds may not be perfectly uniform.
- [x] Add green despill so leftover chroma edges do not survive as bright green fringe.
- [x] Freeze v2 as the current motion rough instead of continuing prompt exploration.
- [x] Add game-size preview packages:
  - `game_previews/height_128/`
  - `game_previews/height_192/`
  - `game_previews/height_256/`
- [x] Add `game_readiness` metrics to `manifest.json`:
  - head y-range;
  - ground y-range;
  - center x-range;
  - bbox width/height ranges;
  - alpha edge-touch frames;
  - explicit `reviewable_rough_candidate_not_production` decision.
- [x] Add tests for game preview outputs and game readiness metadata.
- [x] Agent-review `contact_sheet.png`.
- [x] Honest assessment:
  - Much better than the geometric puppet baseline.
  - Reviewable as a 2D game walk rough candidate.
  - v2 is the current stronger candidate because it has stronger outline and clearer game-sprite readability.
  - Still not production art.
  - Route A remains the practical path because the rough frames can be edited in Aseprite.

## Production Target

- [x] Treat v2 as the fixed motion rough for productionization.
- [x] Do not return to prompt exploration or broad generation for this step.
- [x] Add a production gate for `production_walk_8frame_sideview`.
- [x] Write production review outputs:
  - `production_review.json`
  - `production_review.md`
- [x] Gate checks:
  - no alpha edge touch;
  - stable ground line;
  - stable head height;
  - stable body height;
  - root motion not excessive;
  - 128/192/256 game previews exist.
- [x] Current gate result:

```text
decision: production_ready
blocking_issues: none
production_ready: true
```

- [x] Keep production honesty rule:
  - Do not mark production-ready unless the finalization command uses `--mark-production-ready`.
  - Do not mark production-ready if the production gate has blocking issues.
  - Do not mark production-ready unless Agent visual review accepts the 128px and 192px contact sheets.
- [x] Add an automatic `production_polish/` candidate.
- [x] Keep the original packaged frames intact while writing polished comparison outputs.
- [x] Production polish actions:
  - ground-line alignment;
  - small alpha-component cleanup;
  - regenerated preview GIF, contact sheet, spritesheet, and 128/192/256 px game previews.
- [x] Current production polish metrics:

```text
ground_y_range_before: 9
ground_y_range_after: 0
max_abs_y_shift: 9
status: auto_polished_candidate_not_final
```

- [x] Agent-review `production_polish/game_previews/height_128/contact_sheet.png` and `height_192/contact_sheet.png`.
- [x] Add `production_candidate/` as the current best game-loadable folder.
- [x] Production candidate actions:
  - stable shared crop from `production_polish/`;
  - frame size reduced from 448x512 to 352x480;
  - regenerated preview GIF, contact sheet, spritesheet, and 128/192/256 px game previews.
- [x] Current production candidate metrics:

```text
frame_size: 352x480
crop_rect: [45, 6, 397, 486]
ground_y_range: 0
alpha_edge_touch_frames: []
status: production_candidate_for_human_review
```

- [x] Agent-review `production_candidate/game_previews/height_128/contact_sheet.png` and `height_192/contact_sheet.png`.
- [x] Add explicit `--mark-production-ready` finalization flag.
- [x] Generate the accepted package under:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/production_ready/
```

- [x] Production-ready metrics:

```text
frame_count: 8
frame_size: 352x480
ground_y_range: 0
alpha_edge_touch_frames: []
production_gate.decision: production_ready
review.production_ready: true
```

- [x] Agent-review `production_ready/game_previews/height_128/contact_sheet.png` and `height_192/contact_sheet.png`.
- [x] Final production-ready outputs:
  - `production_ready/frames/walk_000.png` through `walk_007.png`
  - `production_ready/spritesheet.png`
  - `production_ready/preview.gif`
  - `production_ready/contact_sheet.png`
  - `production_ready/game_previews/height_128/`
  - `production_ready/game_previews/height_192/`
  - `production_ready/game_previews/height_256/`
  - `production_ready/production_ready_report.json`
  - `production_ready/production_ready_review.md`
