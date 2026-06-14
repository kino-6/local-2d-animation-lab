# Walk 8-Frame Side-View Baseline

This is a deliberately conservative MVP package for game import review.

- route: `walk_8frame_sideview_baseline`
- route_status: `baseline_not_production`
- frame_count: `8`
- fps: `8`
- frame_size: `512x512`
- action: `walk`
- direction: `right`
- view: `side`
- loop: `true`
- background: `transparent`

## What This Is

The package starts from one reference cutout and applies a tiny deterministic walk-cycle baseline:
whole-body bob plus a small lower-body offset. It preserves one character silhouette and stable canvas
layout over motion realism.

## What This Is Not

- Not production-grade animation.
- Not Wan/video generation.
- Not a 120-frame candidate.
- Not attack, hit, run, weapon, or broad action generation.
- Not proof that the generative pipeline can make final-quality walk cycles.

Use this as the boring concrete artifact route: `frames/*.png`, `spritesheet.png`, and `preview.gif`
are the review targets.
