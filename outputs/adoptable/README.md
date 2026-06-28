# Adoptable Asset Index

This folder contains the current adopted game-asset packages. Treat the two character packs below as the active deliverables.

## Current Character Packs

| Character | Directory | Manifest | Review Sheet | Visual Gate | Status |
| --- | --- | --- | --- | --- | --- |
| Sailor schoolgirl | `outputs/adoptable/character_sprite_asset_pack/` | `outputs/adoptable/character_sprite_asset_pack/manifest.json` | `outputs/adoptable/character_sprite_asset_pack/pack_review/all_actions_contact_sheet.png` | `outputs/adoptable/character_sprite_asset_pack/pack_review/visual_gate_report.json` | `production_ready`, visual review still required |
| Gothic nun, skirt + boots | `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/` | `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json` | `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/all_actions_contact_sheet.png` | `outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/visual_gate_report.json` | `production_ready`, visual review still required |

## Sailor Schoolgirl Pack

Source identity:

- pink bob hair
- right-facing anime side profile
- white sailor-style top
- red tie
- navy skirt
- dark socks
- brown shoes

Location:

```text
outputs/adoptable/character_sprite_asset_pack/
```

Actions:

- `idle`: 4 frames
- `walk`: 8 frames
- `run`: 8 frames
- `jump`: 12 frames
- `hurt`: 8 frames
- `dodge_backstep`: 8 frames
- `parry_sword`: 8 frames
- `attack_sword_light`: 16 frames

Godot preview:

```bash
godot --path godot -- \
  --manifest outputs/adoptable/character_sprite_asset_pack/manifest.json \
  --action walk
```

Visual gate:

```bash
uv run python scripts/visual_asset_gate.py \
  --manifest outputs/adoptable/character_sprite_asset_pack/manifest.json \
  --report outputs/adoptable/character_sprite_asset_pack/pack_review/visual_gate_report.json
```

## Gothic Nun, Skirt + Boots Pack

Source identity:

- black short nun hood and veil
- long white/silver hair
- black skirt with subtle gold trim
- small red tie accent
- black thigh socks
- black leather boots

Location:

```text
outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/
```

Actions:

- `idle`: 4 frames
- `walk`: 8 frames
- `run`: 8 frames
- `jump`: 12 frames
- `hurt`: 8 frames
- `attack_sword_light`: 11 frames

Godot preview:

```bash
godot --path godot -- \
  --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json \
  --action walk
```

Visual gate:

```bash
uv run python scripts/visual_asset_gate.py \
  --manifest outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json \
  --report outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/pack_review/visual_gate_report.json
```

## Historical / Not One Of The Two Current Characters

`outputs/adoptable/artist_authored_8frame_walk_cleanup/` is an older walk-only Route A/MVP artifact. Keep it as historical evidence and tooling reference, but do not treat it as one of the current two character asset packs.
