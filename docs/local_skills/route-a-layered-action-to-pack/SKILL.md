---
name: route-a-layered-action-to-pack
description: Build layered 2D game sprite actions with body, weapon, and effect layers for character_sprite_asset_pack. Use when adding or improving weapon/effect actions, separating sword or slash/parry effects from character body frames, preserving composed-frame compatibility, exposing hit/parry/invulnerability timing windows, and documenting heuristic versus native layer sources without returning to 120-frame, Wan/video, ComfyUI, ControlNet, or broad model research.
---

# Route A Layered Action To Pack

## Top Rule

Preserve the composed action frames as the compatibility output, then add layers as an extension.

Do not replace:

```text
actions/<action>/frames/*.png
actions/<action>/spritesheet.png
actions/<action>/preview.gif
```

Layered outputs are additional review/runtime assets.

## Layer Contract

Use these default layers for weapon/effect actions:

- `body`: character body, outfit, hair, and pose.
- `weapon`: sword, axe, bow, shield, or held combat prop.
- `effect`: slash arc, parry spark, hit flash, dust, smoke, or magic effect.

Use this z-order for weapon/effect actions when the hand or sleeve should visually cover the grip:

```text
weapon -> body -> effect
```

Write:

```text
actions/<action>/layers/body/frames/<action>_000.png
actions/<action>/layers/weapon/frames/<action>_000.png
actions/<action>/layers/effect/frames/<action>_000.png
actions/<action>/layered_manifest.json
```

Each layer should also have:

- `spritesheet.png`;
- `preview.gif`;
- `contact_sheet.png`.

## Source Policy

Production layered actions must use native separated sources:

- one source sheet for body;
- one source sheet for weapon;
- one source sheet for effect;
- identical frame count, canvas, camera, and phase names.

If only composed rough frames exist, heuristic extraction is acceptable for review, but mark it as:

```text
heuristic_split_from_composed_frames
```

Do not claim heuristic extraction is production-grade separation. It is useful for review, Godot
toggle tests, and identifying whether native layer generation is worth doing next. Retake or
regenerate the source when a production asset needs true layer separation.

## Runtime Metadata

Layered actions must keep action timing windows close to runtime metadata:

- attacks: `hit_frames`;
- parries: `parry_frames`;
- dodge/evasion: `invulnerable_frames`;
- effects: `effect_visible_frames`;
- weapons: `weapon_visible_frames`.

The layer manifest should include:

- `layers`;
- `z_order`;
- `composite_source`;
- per-layer artifacts;
- visible frame lists;
- timing windows;
- source/extraction method;
- honest notes about limitations.

## Review Checklist

Review the composed contact sheet first. If the composed action fails, layering will not save it.

Then review:

- `layers/body/contact_sheet.png`: identity, silhouette, no missing core body parts.
- `layers/weapon/contact_sheet.png`: weapon visibility, rough continuity, no major body contamination.
- `layers/effect/contact_sheet.png`: effect timing, no unwanted character fragments.
- `layered_manifest.json`: z-order and timing windows match the action spec.
- Godot import manifest: exposes the layered manifest path without breaking composed imports.

For heuristic extraction, accept minor contamination only when:

- composed frames remain unchanged;
- the layer is labeled heuristic;
- future native layer generation is documented as the next improvement.

Reject if:

- composed compatibility is broken;
- layer files have inconsistent frame counts;
- the action loses gameplay timing metadata;
- the layer contract hides that extraction is heuristic.
- a production action depends on color-based extraction from composed art.

## Current Accepted Layered Examples

- `attack_sword_light`: native body-only rough frames plus independently generated sword/effect layers.
- `parry_sword`: native body-only rough frames plus independently generated sword/effect layers.

Current limitation:

- These actions are production-ready for the current Route A sprite pack, not proof that arbitrary
  weapon actions can be generated without action-specific body roughs.
- The accepted path is regeneration or authoring of native layers; color/heuristic extraction from
  composed frames is rejected as a production route.
