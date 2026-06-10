# Natural Sprite Asset Improvement Plan

## Objective

Build a local-first workflow that turns:

- one reference character image
- one natural-language asset instruction

into game-ready 2D character animation assets with reproducible generation, local evaluation, and Godot playback validation.

Walking is only the baseline example. The durable target is prompt-driven asset generation for walk, idle, attack, hit reaction, directional variants, and future game animation types.

## Current Baseline

Stable enough to reuse:

- Structured `AnimationSpec`
- Reference interpretation into `CharacterProfile`
- Action catalog for walk, idle, sword, axe, bow, light hit, heavy hit, knockback
- ComfyUI backend with NovaOrangeXL default
- OpenPose ControlNet pose maps
- Same-seed identity stabilization
- Transparent attack/hit effect layers
- Local heuristic `evaluation_report.json`
- Godot headless E2E manifest playback test

Known weak points:

- Weapon continuity drifts across frames, especially sword and axe.
- Hit body poses are still too mild.
- Effect layers are heuristic overlays, not anchored to pose keypoints or masks.
- Identity consistency needs stronger reference guidance.
- Evaluation detects image stability but not action semantics.

## Local Workflow

### 1. Plan

Choose the asset recipe from `src/natural_sprite_lab/action_catalog.py`.

For new assets, decide:

- action category
- semantic variant
- frame count
- loop or one-shot behavior
- required prop, hit source, or effect cue
- acceptance criteria

Do not start with a vague instruction such as `attack animation`. Make it concrete, such as `quick sword slash`, `heavy axe overhead chop`, `bow draw and release`, `light stagger`, `heavy recoil`, or `knockback`.

### 2. Generate

Use the local ComfyUI path first:

```bash
uv run python scripts/pdca_multi_asset.py \
  --input assets/reference/Anima_00013_.png \
  --output-root outputs_action_variants_effect_pdca
```

Use NovaOrangeXL as the default visual baseline unless a sweep shows a better checkpoint for the specific asset family.

### 3. Check

Inspect:

- `contact_sheet.png`
- `contact_sheet_with_effects.png` for attack/hit
- `preview.gif`
- `evaluation_report.json`
- `manifest.json`

Run Godot validation:

```bash
godot --headless --path godot --script res://tests/e2e_runner.gd -- \
  --manifest <relative path to manifest.json>
```

The Godot gate should confirm:

- manifest loads
- frame count matches spec
- frame sizes are consistent
- composited frames are used when available
- `AnimatedSprite2D` starts playback

### 4. Act

Apply one focused improvement per PDCA loop:

- prompt/profile change
- frame plan change
- pose template change
- effect layer change
- checkpoint/config change
- evaluator change

Regenerate only the cheapest artifact when possible. For example, use `scripts/regenerate_action_effects.py` when only effect cues changed.

## Improvement Roadmap

### Phase 1: Semantic Control

Goal: make each action read correctly before chasing polish.

Tasks:

- Add action-specific pose templates for sword, axe, bow, light hit, heavy hit, and knockback.
- Add prop intent to frame plans, not only prompts.
- Add hit source direction and reaction direction to hit frame plans.
- Store action variant metadata in `AnimationSpec` or director metadata.

Acceptance:

- Contact sheets visually distinguish sword, axe, bow.
- Hit variants visibly differ in recoil magnitude and direction.
- Godot E2E passes for each best candidate.

### Phase 2: Reference Consistency

Goal: keep the character identity stable across frames and actions.

Tasks:

- Add local IP-Adapter or equivalent ComfyUI reference-guided workflow.
- Evaluate character LoRA feasibility for frequently reused characters.
- Export identity score fields for hair, outfit color, face, and silhouette.
- Compare same-seed, seed-step, and reference-guided runs.

Acceptance:

- Outfit color and hair silhouette remain stable across 8 frames.
- Same character remains recognizable in walk, idle, attack, and hit.

### Phase 3: Prop and Effect Layers

Goal: separate game-readable action cues from body generation.

Tasks:

- Anchor sword slash, arrow, axe impact, and hit bursts to pose keypoints.
- Export effect-only PNG layers as first-class game assets.
- Add optional prop guide layers for weapons.
- Add Godot preview scene controls to toggle raw, effect, and composited frames.

Acceptance:

- Effects appear only on meaningful frames.
- Effects align with hands, weapon direction, or hit location.
- Godot preview can switch between raw and composited playback.

### Phase 4: Semantic Evaluation

Goal: detect action correctness locally, not just image stability.

Tasks:

- Add a local semantic evaluator using Ollama vision or a lightweight image classifier.
- Score action readability: weapon present, hit direction, motion magnitude, frame ordering.
- Keep heuristic evaluation as a fast pre-check.
- Emit per-action findings into `evaluation_report.json`.

Acceptance:

- A high score requires both stable imagery and recognizable action semantics.
- The evaluator flags cases like `axe prompt without axe` or `hit pose with no recoil`.

### Phase 5: Game Export Quality

Goal: make generated outputs immediately usable in a 2D game pipeline.

Tasks:

- Add pivot, frame timing, hitbox, hurtbox, and event metadata.
- Export Godot `.tres` or import-ready animation resources.
- Add batch E2E over all best candidates in `multi_asset_pdca_summary.json`.
- Add visual regression snapshots or frame hash summaries for stable tests.

Acceptance:

- Godot can load a whole generated asset pack.
- Each animation has frame timing, pivot metadata, and optional gameplay events.
- CI/local tests catch broken manifests or unusable frame sets.

## Next Recommended PDCA Loop

Run one focused loop on `attack_sword` and `hit_knockback`:

1. Add prop/effect anchors to frame plans.
2. Generate pose or guide metadata per frame.
3. Regenerate effect layers without rerunning ComfyUI.
4. Validate in Godot.
5. If cue alignment improves, rerun ComfyUI only for the changed variants.

This loop targets the current highest-value weakness: actions are more readable with effect layers, but the cues are not yet anchored to the generated pose.

## 1h Goal Implementation Result

Completed locally:

- Added per-frame semantic metadata:
  - `action_variant`
  - `semantic_tags`
  - `effect_anchor`
  - `game_events`
- Updated effect generation to read `effect_anchor` metadata before falling back to label heuristics.
- Added semantic action-readability evaluation to `evaluation_report.json`.
- Added semantic metadata to `manifest.json`.
- Added game-engine metadata:
  - frame size
  - frame duration
  - frame events
  - rough hurtboxes
  - rough attack hitboxes
- Added `scripts/godot_validate_summary.py` for batch Godot validation of all best candidates in a PDCA summary.
- Added tests for semantic metadata, manifest game metadata, and Godot summary validation.

Validated:

- `uv run pytest` passed.
- `uv run python scripts/godot_validate_summary.py --summary outputs_action_variants_effect_pdca/multi_asset_pdca_summary.json` passed for walk, idle, attack_sword, attack_axe, attack_bow, hit_light, hit_heavy, and hit_knockback.

Deferred because they require model/workflow assets outside this code change:

- IP-Adapter or equivalent ComfyUI reference-guided workflow.
- Character LoRA creation and evaluation.
- A learned local vision classifier for action semantics.

Next loop:

1. Add ComfyUI IP-Adapter workflow support behind an optional backend flag.
2. Run a focused comparison on `attack_sword` and `hit_knockback`.
3. Promote semantic evaluator from metadata-gated checks to local vision checks when Ollama vision is available.
