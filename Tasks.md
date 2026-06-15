# Tasks: Style Lock And Frame Density Upgrade

## Upper Rule

- [ ] Keep the current `character_sprite_asset_pack` route as the production target.
- [ ] Do not return to broad 120-frame research, Wan/video generation, ControlNet sweeps, or prompt-only animation experiments.
- [ ] Treat the original illustration as an identity reference, not as the direct animation source.
- [ ] Treat the accepted pack style as the source of truth for new action roughs.
- [ ] Improve two visible blockers:
  - action-to-action art style drift;
  - low frame density in motion-heavy actions.

## Current Baseline

- [ ] Preserve the current committed pack as the rollback baseline:

```text
outputs/adoptable/character_sprite_asset_pack/
```

- [ ] Keep all current actions loadable in Godot:
  - `idle`;
  - `walk`;
  - `run`;
  - `jump`;
  - `hurt`;
  - `dodge_backstep`;
  - `parry_sword`;
  - `attack_sword_light`.
- [ ] Keep the existing native layered weapon/effect route for `attack_sword_light` and `parry_sword`.
- [ ] Keep composed frames as the compatibility output for Godot/Aseprite.

## Style Reference Set

- [ ] Add a style reference set under:

```text
assets/style_reference_sets/character_sprite_pack_v1/
```

- [ ] Select representative accepted frames from the current pack:
  - `idle` neutral;
  - `walk` contact or passing pose;
  - `run` readable stride;
  - `attack_sword_light` active or windup pose;
  - `parry_sword` guard/contact pose.
- [ ] Generate `contact_sheet.png` for the style reference set.
- [ ] Write `manifest.json` for the reference set with:
  - source action;
  - source frame;
  - identity cues;
  - expected palette notes;
  - expected line/shape notes.
- [ ] Document that future roughs should be image-to-image or manually edited against this pack style, not only against the original illustration.

## Style Consistency Gate

- [ ] Add deterministic style metrics to `scripts/build_character_sprite_asset_pack.py` or a helper script:
  - foreground bbox height and width;
  - dominant hair color;
  - sailor top color range;
  - skirt/sock dark color range;
  - shoe brown color range;
  - foreground saturation/brightness range;
  - transparent corner check;
  - action canvas consistency.
- [ ] Generate pack-level:

```text
outputs/adoptable/character_sprite_asset_pack/pack_review/style_consistency_report.json
```

- [ ] Include per-action labels:
  - `style_pass`;
  - `style_review`;
  - `style_retake_needed`.
- [ ] Add style consistency summary to:
  - `manifest.json`;
  - `production_gate.json`;
  - `pack_review/godot_import_manifest.json` if useful.
- [ ] Keep the gate honest: do not mark style as solved if metrics pass but Agent visual review still sees obvious drift.

## Frame Density Policy

- [ ] Add action-level recommended source frame counts:
  - `idle`: 4-6;
  - `walk`: 8-12;
  - `run`: 8-12;
  - `jump`: 12-16;
  - `hurt`: 8-12;
  - `dodge_backstep`: 8-12;
  - `parry_sword`: 8-12;
  - `attack_sword_light`: 12-18.
- [ ] Store the policy in docs and runtime metadata as review guidance, not a hard universal rule.
- [ ] Add `frame_density_review` to action reports:
  - source frame count;
  - playback frame count;
  - recommended range;
  - decision.
- [ ] Reject fake inbetweens based only on frame blending or cross-fade ghosts.
- [ ] Prefer real drawn/generated source frames for anticipation, active, overshoot, and recovery.

## Attack Sword Light Density Pass

- [ ] Target `attack_sword_light` first because it exposes both style drift and motion density issues.
- [ ] Plan a 16-frame source spec:
  - ready;
  - anticipation 1;
  - anticipation 2;
  - draw back;
  - windup;
  - slash start;
  - active slash 1;
  - active slash 2;
  - active follow-through;
  - overshoot;
  - recoil 1;
  - recoil 2;
  - settle 1;
  - settle 2;
  - recover;
  - ready return.
- [ ] Create or retake body-only rough frames in the accepted pack style.
- [ ] Keep sword and slash effects as native separate layers.
- [ ] Update active `hit_frames` for the 16-frame timing.
- [ ] Regenerate action outputs and Godot previews.
- [ ] Agent-review:
  - no obvious style drift;
  - sword connects to hands;
  - active slash reads at 1x and slow playback;
  - recovery does not snap.

## Walk Density Decision

- [ ] Review current 8-frame walk in Godot at 0.5x, 1x, and 2x.
- [ ] Decide whether to:
  - keep 8 frames and only polish style/foot contact;
  - retake to 10 or 12 real source frames.
- [ ] Do not increase walk frame count unless it clearly improves foot contact, head stability, or loop smoothness.
- [ ] If retaking walk, preserve:
  - side-view right-facing;
  - transparent canvas;
  - stable ground contact;
  - pack style identity cues.

## Godot Demo Review Tools

- [ ] Add playback speed controls to the Godot demo:
  - 0.5x;
  - 1x;
  - 2x.
- [ ] Add visible current action, frame index, and loop/one-shot status.
- [ ] Add action order shortcuts that remain stable as actions grow.
- [ ] Verify `godot --headless` pack validation still passes.

## Documentation And Skills

- [ ] Update `docs/character_identity_sprite_asset_pack.md` with:
  - style reference set policy;
  - style consistency gate;
  - frame density policy.
- [ ] Update `docs/local_skills/route-a-action-rough-to-pack/SKILL.md` with:
  - accepted pack style as primary style reference;
  - image-to-image or manual edit guidance against style reference set;
  - frame density review.
- [ ] Update `docs/local_skills/route-a-layered-action-to-pack/SKILL.md` if 16-frame attack changes the layer contract.
- [ ] Record that production-ready means game-ready redesign consistency, not faithful animation of the original illustration.

## Tests

- [ ] Update `tests/test_build_character_sprite_asset_pack.py` for:
  - style consistency report exists;
  - production gate includes style consistency;
  - frame density metadata exists;
  - attack frame count if upgraded to 16.
- [ ] Update Godot tests if playback speed controls or action metadata affect the viewer.
- [ ] Run:

```powershell
uv run pytest tests\test_build_character_sprite_asset_pack.py tests\test_godot_e2e.py tests\test_godot_character_sprite_pack.py tests\test_output_layout_policy.py
godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest outputs/adoptable/character_sprite_asset_pack/manifest.json
git diff --check
```

## Completion Criteria

- [ ] `Tasks.md` reflects the current next plan, not the completed native-layer pass.
- [ ] Current pack remains loadable in Godot.
- [ ] Style drift is measured and documented.
- [ ] Frame density expectations are explicit per action.
- [ ] `attack_sword_light` has a clear path to 16-frame production review.
- [ ] No unsupported broad-generation route is reintroduced.
