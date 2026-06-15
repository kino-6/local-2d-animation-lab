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

## Decision

Current status:

```text
reference_faithful_motion_probe_promising_not_production
```

This image is better for testing reference-faithful style retention than the prior examples, but it is still not an adopted game animation source.

Next useful step:

1. Curate or regenerate a cleaner one-character full-body side-view design without armor drift.
2. Use `animate_pose` with action-specific walk template and foot guide as the first motion route.
3. Treat VACE lower-body hint as unsuitable for this reference/settings unless its dark-output failure is solved.
4. Package motion probes through `package_game_sprite_asset.py` before judging game readability.
5. Add a stricter non-armor identity gate so gold accents do not become full armor.
