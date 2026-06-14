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

The package starts from one reference image, derives identity colors, and renders a stylized
8-phase side-view walk cycle. The default renderer intentionally favors readable game motion over
direct cutout fidelity, because the cutout-shift preview was not evaluation-worthy.

## What This Is Not

- Not production-grade animation.
- Not Wan/video generation.
- Not a 120-frame candidate.
- Not attack, hit, run, weapon, or broad action generation.
- Not proof that the generative pipeline can make final-quality walk cycles.
- Not a faithful redraw of every reference-image detail.

Use this as the boring concrete artifact route: `frames/*.png`, `spritesheet.png`, and `preview.gif`
are the review targets.
