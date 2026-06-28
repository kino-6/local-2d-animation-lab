---
name: sprite-pack-visual-quality-gate
description: Validate and repair adopted 2D game sprite asset packs for human-visible review risks. Use when checking Godot-ready character_sprite_asset_pack outputs for scale jitter, crop/edge touch, stray sprite fragments, brightness/saturation drift, loop closure jumps, or when asked to make visual E2E gates catch and auto-fix obvious asset weirdness.
---

# Sprite Pack Visual Quality Gate

Use this skill after a sprite pack is generated and before calling it ProductionOK.

## Inputs

- A `character_sprite_asset_pack` manifest.
- Usually one of:
  - `outputs/adoptable/character_sprite_asset_pack/manifest.json`
  - `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json`

## Required Checks

Run the deterministic visual gate:

```bash
uv run python scripts/visual_asset_gate.py \
  --manifest <pack>/manifest.json \
  --report <pack>/pack_review/visual_gate_report.json
```

Then run Godot playback validation:

```bash
godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- \
  --manifest <pack>/manifest.json
```

## What The Gate Catches

- alpha frame touching canvas edges, which often means crop/cutoff;
- extra foreground components, which often means a sliced-off foot, weapon, hair, or neighboring frame fragment;
- large width/height/center jitter, which often means scale drift or badly aligned frames;
- ground/contact jitter for non-jump actions;
- frame-to-frame brightness or saturation drift;
- upper-body hand cue dropout, which often means hands disappear in a frame even though the action still needs readable arms/hands;
- loop closure jumps for looping actions.

## Auto-Fix Policy

Use auto-fix only for safe mechanical repairs:

```bash
uv run python scripts/visual_asset_gate.py \
  --manifest <pack>/manifest.json \
  --report outputs/<timestamp>/visual_gate_report.json \
  --auto-fix-output outputs/<timestamp>/<asset>_visual_fixed
```

The auto-fix may:

- remove small disconnected foreground fragments;
- normalize brightness and saturation toward the action median;
- stabilize bottom-center alignment for non-jump/non-run actions;
- regenerate action preview GIFs, spritesheets, contact sheets, and the all-actions contact sheet.

Do not use auto-fix to hide a fundamentally bad action. If anatomy, pose meaning, identity, costume, or weapon intent is wrong, mark the action as retake/manual art required.

## Decision Rule

- `production_ready`: deterministic gate passes and Godot E2E passes.
- `needs_retake_or_manual_review`: any visual gate finding remains.
- Human visual review overrides deterministic pass/fail when the issue is art direction or anatomy rather than measurable geometry/color.

## Production Notes

Add the `visual_gate_report.json` path to the pack review notes or task record for any adopted pack. Keep the original pack untouched unless the user explicitly asks to replace it with the fixed copy.
