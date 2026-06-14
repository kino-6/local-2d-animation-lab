# Character Identity Sprite Asset Pack

This route follows the accepted `walk` production-ready output with a small pack-level contract.
It exists to address two open risks:

- the sprite can drift away from the reference and become a different character;
- a single accepted walk cycle does not mean other actions are solved.

## Output

```text
outputs/adoptable/character_sprite_asset_pack/
```

The package contains:

- `actions/walk/`
- `actions/idle/`
- `actions/run/`
- `manifest.json`
- `identity_report.json`
- `production_gate.json`
- `notes.md`

## Identity Contract

The character must preserve these source-reference cues before an action can be accepted:

- pink bob hair;
- right-facing side-profile anime girl;
- sailor-style white top;
- red tie;
- navy skirt;
- dark socks;
- brown shoes.

The current sprite is accepted as a reference-derived game sprite design. It is not a faithful copy
of the original illustration. The contract prevents future action work from silently dropping the
important character cues.

## Action Scope

Current production-ready actions:

- `walk`: copied from `artist_authored_8frame_walk_cleanup/production_ready/`;
- `idle`: deterministic subtle-idle action derived from the accepted walk sprite.

Explicitly gated future action:

- `run`: stub only, not production-ready.

This is intentional. A run cycle needs authored or accepted rough frames and should not be faked by
speeding up the walk cycle.

## Production Ready Meaning

`production_ready` for this pack means:

- `walk.production_ready == true`;
- `idle.production_ready == true`;
- `run.production_ready == false` and is honestly gated;
- required identity cues pass on the reference, walk, and idle assets;
- no model or video backend is used.

It does not mean arbitrary future actions are complete.
