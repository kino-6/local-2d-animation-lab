# ComfyUI2025 74298 Reference Feasibility

Date: 2026-06-15

Reference:

```text
assets/reference/ComfyUI2025_74298_trim.png
```

## Input Assessment

The image is visually strong, but it is not directly animation-ready:

- size: `2563x1489`
- background: fully opaque, scene/background included
- framing: bust-up / upper-body dominant
- view: not side-view
- feet/lower body: unavailable
- direct start-reference LocalVL result: not full-body, not right-facing side-view, shoes not readable, not walk-ready

LocalVL output:

```text
outputs/20260615_reference_eval/20260615_231509/local_vl_eval/comfyui2025_74298_reference_feasibility/
```

## Identity Cues

Use these cues for future reference-faithful work:

- pale white long hair
- black hood
- black gothic cloth/leather outfit
- red collar at the neck
- sleepy half-lidded eyes
- small pale face
- high contrast cel-shaded anime style
- dark fantasy hunter/nun silhouette
- Bloodborne-like mood

Avoid these incorrect interpretations:

- gold plate armor
- armored breastplate
- large pauldrons
- knight redesigns that overpower the hooded black-cloth identity

## Full-Body Side-View Probe

Command route:

```text
scripts/generate_fullbody_reference_candidates.py
```

Output:

```text
outputs/20260615_reference_eval/20260615_231601/fullbody_reference/comfyui2025_74298_trim/
```

Result:

- all 12 candidates stayed at `manual_review_or_retake`
- automatic selected candidate was visually invalid because it contained two characters
- best visual candidate was `cleaned/04_face_visible_side_sprite.png`
- candidate 04 preserved the new reference style much better than previous Anima-derived work
- candidate 04 still has a left-edge fragment and is not a clean adopted start reference
- candidate 08 had strong side-view/style preservation but long skirt/cloak occluded legs, making it weak for walk animation

Interpretation:

```text
This reference is promising for reference-faithful redesign, but it needs a curated single-character full-body design sheet before animation.
```

## Walk Endpoint Probe

Source image:

```text
outputs/20260615_reference_eval/20260615_231601/fullbody_reference/comfyui2025_74298_trim/cleaned/04_face_visible_side_sprite.png
```

Command route:

```text
scripts/generate_action_keyframe_candidates.py --action walk_stride --source-image <candidate04>
```

Output:

```text
outputs/20260615_reference_eval/20260615_232140/action_keyframes/comfyui2025_74298_trim_walk_stride_keyframes/
```

Result:

- both endpoint candidates were `manual_review_or_retake`
- blocker: `endpoint_delta_too_low`
- visual result preserved style/identity better than earlier references
- walk pose change was too small to drive first/last or spritesheet generation

## Corrected Non-Armor Full-Body Probe

The first probe over-weighted the gold accents and drifted into armor. After visual review,
the reference should be treated as a black gothic hood / leather-cloth hunter, not as a
gold-armored knight.

Corrected command route:

```text
scripts/generate_fullbody_reference_candidates.py
```

Output:

```text
outputs/20260615_reference_eval/20260615_233624/fullbody_reference/comfyui2025_74298_trim/
```

Selected start frame:

```text
outputs/20260615_reference_eval/20260615_233624/fullbody_reference/comfyui2025_74298_trim/selected_reference/start_frame.png
```

Result:

- automatic selection found `strict_side_profile_retake` as `candidate_ok`
- 2 candidates were `candidate_ok`, 10 were `manual_review_or_retake`
- the selected candidate is a usable motion-probe start: right-facing side profile, white hair, black hood, red neck cue, slim dark outfit, visible legs
- residual issue: some metallic/gold arm pieces remain, so this is not a faithful final design

## Walk Motion Probe

Three local motion routes were tested from the corrected start frame:

| Route | Output | Result |
| --- | --- | --- |
| Wan first/last | `outputs/20260615_reference_eval/20260615_234309/wan_walk_i2v/comfyui2025_74298_bloodborne_walk_first_last/` | Generated motion, but the character stayed too static and the background drifted/darkened heavily. |
| Wan animate-pose + walk foot guide | `outputs/20260615_reference_eval/20260615_234520/wan_walk_i2v/comfyui2025_74298_bloodborne_walk_animate_pose/` | Best current motion probe. Legs alternate more clearly and identity remains readable, but several frames have lower-body afterimage/smear. |
| Wan VACE lower-body hint | `outputs/20260615_reference_eval/20260615_235023/wan_walk_i2v/comfyui2025_74298_bloodborne_walk_vace_lower_hint/` | Rejected. The clip became very dark and nearly static. |

Best reviewable package:

```text
outputs/20260615_reference_eval/20260615_234922/game_sprite_asset/comfyui2025_74298_bloodborne_walk_sprite_package_bg190/
```

This package contains transparent/game-canvas frames, `spritesheet.png`, `preview.gif`,
`contact_sheet.png`, and `manifest.json`.

Assessment:

- status: `motion_probe_not_production`
- the motion reads more like a walk than the first/last route
- the character is still not production-ready because foot/leg afterimages remain in multiple frames
- the non-armor identity is improved, but the selected start frame still has metallic arm drift

## ProductionOK PDCA Toward Walk Asset

Goal:

```text
Turn the best motion probe into a ProductionOK-style 2D game walk asset, while preserving the
Bloodborne-like black hood / cloth-leather identity and avoiding the gold-armor drift.
```

### Loop 1: remove leaked lower-body guide artifacts

Added:

```text
scripts/clean_lower_body_walk_artifacts.py
```

Purpose:

- consume transparent walk frames;
- remove pale/green lower-body remnants left by control/foot-guide leakage;
- regenerate `frames/`, `spritesheet.png`, `contact_sheet.png`, `preview.gif`, and a cleanup report.

Outputs:

```text
outputs/20260615_reference_eval/20260616_000119/sprite_postprocess/comfyui2025_74298_bloodborne_walk_bg190_lower_clean/
outputs/20260615_reference_eval/20260616_000205/sprite_postprocess/comfyui2025_74298_bloodborne_walk_bg190_lower_clean_aggressive/
```

Result:

- safe cleanup reduced small residues but did not remove the strong foot/leg ghost frames;
- aggressive cleanup removed more pixels but still left several visible problem frames;
- conclusion: some failures are generated-frame retakes, not simple postprocess noise.

### Loop 2: select a cleaner 16-frame walk loop candidate

The full 33-frame clip contained several bad phases. Instead of forcing every frame into the
asset, the cleaner odd-indexed frames were selected and stabilized.

Selected source frames:

```text
1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31
```

Best current package:

```text
outputs/20260615_reference_eval/20260616_000550/sprite_asset_quality_flow/comfyui2025_74298_walk_16frame_selected_quality_flow/packages/20260616_000559/game_sprite_asset/package/
```

Local checks:

- frame count: 16
- canvas: `256x384`
- transparent background: yes
- `spritesheet.png`: exists
- `preview.gif`: exists
- `contact_sheet.png`: exists
- motion readability gate: passed
- LocalVL result: walk readability 5/5, game sprite fit 5/5, adoptable as animation true

Agent visual review:

- better than the 33-frame package;
- readable as a game-like walk cycle;
- background and large foot-guide leakage are mostly gone;
- still not marked final ProductionOK because the loop edge should be checked in-engine and the character design still has gold/metal armor drift from the reference interpretation.

### Loop 3: stronger non-armor regeneration

Command route:

```text
scripts/generate_fullbody_reference_candidates.py
```

Output:

```text
outputs/20260615_reference_eval/20260616_000950/fullbody_reference/comfyui2025_74298_trim/
```

Result:

- prompt-level "no armor / no metal shoulder / no gold shoulder" helped only partially;
- the model still tends to amplify tiny gold accents into shoulder armor or gauntlets;
- several candidates were visually useful, but the automated start-frame gate still rejected them for lower-body or extra-component issues;
- conclusion: non-armor identity needs either a curated design sheet, stronger reference editing, or a negative identity gate. Prompt-only retry is not enough.

Current best status:

```text
production_candidate_needs_loop_and_identity_review
```

Do not call this `production_ready` yet.

Blocking issues:

1. Non-armor identity is not fully controlled; gold accents still become armor-like shoulders/bracers.
2. The selected 16-frame loop is readable, but the first/last transition needs game playback review.
3. Deterministic artifact gate over-flags dark sprite legs and boot shadows, while Agent/LocalVL agree the selected package is substantially better.

### Loop 4: non-armor identity postprocess

Added:

```text
scripts/recolor_gold_armor_to_dark_cloth.py
```

Purpose:

- consume the selected transparent 16-frame walk package;
- reduce gold/bright armor-like drift by recoloring yellow metal and upper-side shoulder highlights into dark cloth/leather tones;
- regenerate `frames/`, `spritesheet.png`, `contact_sheet.png`, `preview.gif`, and a recolor report.

Best recolor output:

```text
outputs/20260616_production_pdca/20260616_010026/sprite_postprocess/comfyui2025_74298_walk_16frame_gold_to_cloth_v5_shoulder/
```

Result:

- recolored pixels: `11549`
- gold-like residual pixels after cleanup: `0` by deterministic color gate
- shoulder/arm highlights read less like gold armor and more like dark cloth/leather trim
- limitation: the shoulder silhouette is still inherited from the generated frame, so this is color/identity cleanup, not structural costume correction

### Loop 5: game-loadable candidate package and engine proof

Packaged candidate:

```text
outputs/20260616_production_pdca/20260616_010059/game_sprite_asset/comfyui2025_74298_walk_16frame_production_ok_candidate_v5/
```

Contract:

- `frames/`: 16 transparent PNG frames
- `spritesheet.png`: present
- `preview.gif`: present
- `contact_sheet.png`: present
- `manifest.json`: present
- canvas: `256x384`
- fps: `10`
- status: `production_ready_candidate`

Godot validation:

```text
godot --headless --path godot --script res://tests/single_sprite_asset_runner.gd -- --manifest outputs/20260616_production_pdca/20260616_010059/game_sprite_asset/comfyui2025_74298_walk_16frame_production_ok_candidate_v5/manifest.json
```

Result:

```text
ok=true, animation=walk, frame_count=16, frame_size=256x384, current_frame=2
```

LocalVL result:

```text
outputs/20260616_production_pdca/20260616_010119/local_vl_eval/comfyui2025_74298_walk_16frame_production_ok_candidate_v5_localvl/
```

Scores:

- still image quality: `5/5`
- game sprite asset fit: `5/5`
- action readability: `5/5`
- identity consistency: `5/5`
- background cleanliness: `5/5`
- adoptable as animation or walk endpoint: `true`
- recommended next step: `none`

Deterministic package checks:

- frame count: `16`
- all frames same size: yes
- transparent corner/background: yes
- mean adjacent-frame delta: `5.256`
- max adjacent-frame delta: `7.808`
- loop delta: `5.155`
- loop delta / mean step delta: `0.981`

Initial automated status:

```text
production_ready_candidate_for_game_sprite_walk
```

Human review correction:

```text
game_loadable_but_identity_and_saturation_retake
```

Reason:

- the asset is technically game-loadable and the walk reads, but it looks almost like a different character from the source image;
- the recolor pass over-suppressed chroma and made the sprite too dull/dark;
- LocalVL over-rated identity consistency because it recognized broad cues such as hood, pale hair, and dark outfit, while missing the stronger human judgment that the design drifted too far;
- therefore this should not be treated as ProductionOK, even though the manifest/Godot/package gates pass.

## Decision

Current status:

```text
game_loadable_but_identity_and_saturation_retake
```

This image is a usable local proof for engine loading and walk-cycle packaging, but it is not an acceptable ProductionOK asset. The next route must preserve identity and palette before motion cleanup; darkening/recoloring a drifted generation is not enough.

Next useful step:

1. Create or edit a clean side-view design sheet with the target palette before motion generation.
2. Add a saturation/value guard so postprocess cannot make the accepted sprite flatter or darker than the source style.
3. Keep the selected 16-frame odd-index route only as a motion/package proof, not as the adopted art target.
4. Use `scripts/recolor_gold_armor_to_dark_cloth.py` only for narrow cleanup after identity is already correct.
5. Validate single-sprite packages through `godot/tests/single_sprite_asset_runner.gd`, but do not let engine-loadability imply visual adoption.
