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
