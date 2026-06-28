# Artist-Authored 8-Frame Walk Cleanup

This package is Route A: a rough walk cycle packaged for review from `ai_generated_rough_for_route_a_v2`.

- route: `artist_authored_8frame_walk_cleanup`
- route_status: `requires_artist_authored_rough`
- source_kind: `ai_generated_rough_for_route_a_v2`
- frame_count: `8`
- background: `transparent`
- AI/model scope: `cleanup_only_no_pose_or_silhouette_generation`
- game_readiness: `reviewable_rough_candidate_not_production`
- production_gate: `production_ready`
- production_ready: `True`

## What This Route Does

- Preserves the provided rough poses and silhouette without generating new frames.
- Produces transparent frames, spritesheet, preview GIF, contact sheet, manifest, and cleanup report.
- Produces 128, 192, and 256 px-height game-size preview packages by default.
- Produces an optional `production_polish/` candidate with ground-line alignment.
- Produces a trimmed `production_candidate/` folder when production polish is enabled.
- Produces a `production_ready/` folder when explicitly finalized with `--mark-production-ready`.
- Produces production review JSON/Markdown for the manual polish gate.
- Uses deterministic cleanup only.

## What This Route Does Not Do

- Does not generate poses.
- Does not redesign the character.
- Does not run ComfyUI, Wan, ControlNet, video generation, or new model backends.
- Does not create 120-frame outputs.

## Cleanup Warnings

- none
