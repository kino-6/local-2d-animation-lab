# Output Cleanup: High-Density Jump and Hurt

Date: 2026-06-15

## Keep

The current adopted output remains:

```text
outputs/adoptable/character_sprite_asset_pack/
```

It is retained because it is the current game-loadable package and now contains:

- `walk`: 8 frames, loop;
- `idle`: 4 frames, loop;
- `run`: 8 frames, loop;
- `jump`: 12 source frames, one-shot;
- `hurt`: 8 source frames, one-shot;
- Godot import metadata and headless E2E coverage.

The accepted walk source is also retained:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/production_ready/
```

The builder still consumes it as the canonical walk source.

## Delete

No additional `outputs/` directory was deleted in this cleanup pass. The remaining output tree is
already restricted to adopted assets and the required production-ready walk source.

## Findings

- Godot already supports variable action frame counts through manifest-driven `SpriteFrames`.
- Increasing frame count by adding real source frames works; `jump` is now 12 frames and `hurt` is
  now 8 frames.
- `hurt.loop=false` was already correct. The visible left-right snap was caused by source-frame
  horizontal offsets and edge clipping, not Godot loop metadata.
- Reaction actions should be centered during cleanup instead of preserving accidental rough-sheet
  horizontal offsets.
- `jump` readability improves with more source phases, but generated roughs still introduce pose,
  scale, and identity drift across sheets.
- Dense actions should use multiple 2x2 high-resolution source sheets instead of one crowded grid.

## Next Direction

The next useful action is a single constrained attack:

```text
attack_sword_light
```

Start with a one-handed short sword and 12 source frames. Treat it as a one-shot action with explicit
active hit frames. Avoid broad attack families until this route is proven.
