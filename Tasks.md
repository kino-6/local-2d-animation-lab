# Tasks: Walk 8-Frame Side-View Baseline MVP

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

## Do Not Do In This Task

- [x] Do not generate 120-frame outputs.
- [x] Do not run Wan or video generation.
- [x] Do not attempt attack, hit, run, weapon, or multi-action generation.
- [x] Do not add new model integrations.
- [x] Do not chase production-grade art quality.

## Plan

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

## Success Criteria

- [x] Exactly eight PNG frames exist.
- [x] All frames share one canvas size.
- [x] PNG frames have transparent backgrounds.
- [x] `spritesheet.png`, `preview.gif`, `contact_sheet.png`, `manifest.json`, and `notes.md` exist.
- [x] Manifest marks `route_status` as `baseline_not_production`.
- [x] The package contains one character and no duplicate/crowd-like generation failure.
- [x] No ComfyUI, Wan, video, 120-frame, attack, hit, run, or weapon path is executed.

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
