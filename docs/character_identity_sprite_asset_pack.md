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
- `actions/jump/`
- `actions/hurt/`
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
- `run`: cleaned and packaged from the dedicated `imagegen_run_8frame_20260614` rough sheet.
- `jump`: cleaned and packaged from the dedicated `imagegen_jump_6frame_20260614` rough sheet.
- `hurt`: cleaned and packaged from the dedicated `imagegen_hurt_4frame_20260614` rough sheet.

The repeatable workflow for adding actions is documented in
`docs/local_skills/route-a-action-rough-to-pack/SKILL.md`.

Future action policy:

Run, jump, and hurt were promoted only after they had dedicated rough sheets with action-specific
poses. Stronger actions still need authored or accepted rough frames and should not be faked by
retiming walk frames.

Built-in image generation or image-to-image is acceptable for rough source art when local generation
is not producing usable assets. In that case, record the rough creation as non-local in `prompt.md`;
the local reproducible pipeline begins from the committed rough frames.

## Production Ready Meaning

`production_ready` for this pack means:

- `walk.production_ready == true`;
- `idle.production_ready == true`;
- `run.production_ready == true`;
- `jump.production_ready == true`;
- `hurt.production_ready == true`;
- required identity cues pass on the reference, walk, idle, run, jump, and hurt assets;
- no model or video backend is used.

It does not mean arbitrary future actions are complete.
