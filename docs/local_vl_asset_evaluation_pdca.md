# Local VL Asset Evaluation PDCA

This report checks whether the current best local artifact can be evaluated by Agent review, deterministic quality gates, and local VLM/LLM tooling.

## Target

Current local best still-image refinement:

- frames: `outputs_image_quality_pdca/run_endpoint_quality_d035_bgclean160_20260612_234849/frames`
- contact sheet: `outputs_image_quality_pdca/run_endpoint_quality_d035_bgclean160_20260612_234849/contact_sheet.png`
- quality gate: `outputs_image_quality_pdca/run_endpoint_d035_bgclean160_quality_gate_20260612_234919/artifact_repair_report.json`

This is the best current *still-image quality* proof for the ComfyUI2025 `run` endpoint branch. It is not the best motion proof.

## Agent Visual Evaluation

Agent verdict:

- Still-image quality: good. The 1024 img2img pass removed the beige panel, improved face/line/color quality, and left a clean white background.
- Game asset fit: usable as a polished standing/full-body character frame.
- Run/action readability: poor. The two frames are mostly neutral standing frames; arms do not pump, stride is minimal, and it does not read as a run endpoint.
- Adoption: acceptable as still-image polish proof; not acceptable as a run animation or first/last endpoint.

## Deterministic Gate

`scripts/repair_frame_artifacts.py --mask-only` reports:

```json
{
  "gate_counts": {"no_repair_needed": 2},
  "issue_counts": {},
  "review_label_counts": {},
  "candidate_status": "adopted_full_source"
}
```

This correctly says the still frames are structurally clean. It does not judge whether the requested action reads as `run`.

## Local VLM/LLM Evaluation

Available local model:

- vision model: `huihui_ai/qwen3-vl-abliterated:8b`
- text normalizer: `huihui_ai/qwen3-abliterated:8b`

The direct VLM output recognized the important issue, but did not reliably return valid JSON. A robust local workflow therefore needs three steps:

1. Ask the local VLM for visual judgment and save raw text.
2. Ask a local text LLM to normalize the raw notes into JSON.
3. Apply deterministic consistency rules.

Implemented helper:

```bash
uv run python scripts/evaluate_sprite_with_ollama_vl.py \
  --image outputs_image_quality_pdca/run_endpoint_quality_d035_bgclean160_20260612_234849/contact_sheet.png \
  --action run \
  --run-label best_still_run_endpoint_eval \
  --output-root outputs_local_vl_eval
```

Result:

- output: `outputs_local_vl_eval/best_still_run_endpoint_eval_20260613_000100/local_vl_eval.json`

```json
{
  "still_image_quality_0_5": 5,
  "game_sprite_asset_fit_0_5": 5,
  "action_readability_0_5": 2,
  "identity_consistency_0_5": 5,
  "background_cleanliness_0_5": 5,
  "is_readable_run_action": false,
  "is_adoptable_as_still_sprite_proof": true,
  "is_adoptable_as_animation_or_run_endpoint": false,
  "visible_issues": [
    "Character is standing still, not running",
    "Still image may be usable, but run action readability is insufficient."
  ],
  "recommended_next_step": "Animate the run action by adding motion to the limbs"
}
```

## Decision

Local evaluation is useful, but not as a single unguarded VLM call.

Works:

- Local VLM can detect the high-level semantic mismatch: clean still image, not a run.
- Local LLM can normalize the VLM notes into a usable JSON report.
- Deterministic consistency rules can prevent contradictory outcomes, such as `is_readable_run_action=false` but `is_adoptable_as_animation_or_run_endpoint=true`.

Weaknesses:

- The VLM direct JSON instruction following is unreliable with the current model.
- The VLM tends to over-score still-image and sprite fit (`5/5`) and needs strict downstream gates.
- Deterministic gates catch structural artifacts, not action semantics.

Recommended Skill pattern:

```text
deterministic gate -> Agent/visual review -> LocalVL semantic review -> LocalLLM normalization -> consistency rules
```

Adoption rule:

- A candidate can pass still-image polish only when deterministic gates and visual review agree.
- A candidate can pass action animation only when LocalVL/Agent both say the requested action is readable, and motion/quality gates also pass.

## PDCA Follow-Up: Multi-Candidate Check

I evaluated three related candidates to see whether LocalVL can distinguish still-image polish from action semantics.

| Candidate | Deterministic gate | LocalVL action result | LocalVL still result | Interpretation |
|---|---|---|---|---|
| source lower-body endpoint | `outputs_image_quality_pdca/run_endpoint_source_quality_gate_20260612_234651`: `rejected`, `duplicate_silhouette_area_high: 2` | `is_readable_run_action: false`, `action_readability_0_5: 2` | `still_image_quality_0_5: 5`, `is_adoptable_as_still_sprite_proof: true` | LocalVL catches semantic failure, but misses/overlooks deterministic structural rejection. |
| best d0.35 bgclean160 | `outputs_image_quality_pdca/run_endpoint_d035_bgclean160_quality_gate_20260612_234919`: `adopted_full_source` | `is_readable_run_action: false`, `action_readability_0_5: 2` | `still_image_quality_0_5: 5`, `is_adoptable_as_still_sprite_proof: true` | Correct combined verdict: good still proof, not run/action proof. |
| d0.50 bgclean | `outputs_image_quality_pdca/run_endpoint_d050_bgclean_quality_gate_20260612_234825`: `selected_proof_only`, `lower_body_pale_afterimage_review: 2` | `is_readable_run_action: false`, `action_readability_0_5: 2` | `still_image_quality_0_5: 5`, `is_adoptable_as_still_sprite_proof: true` | LocalVL again catches action failure but does not penalize subtle identity/outfit drift or lower-body review labels. |

LocalVL outputs:

- source rejected: `outputs_local_vl_eval/source_rejected_run_endpoint_eval_fixed_20260613_000852/local_vl_eval.json`
- best still: `outputs_local_vl_eval/best_still_run_endpoint_eval_20260613_000100/local_vl_eval.json`
- d0.50: `outputs_local_vl_eval/d050_run_endpoint_eval_fixed_20260613_000955/local_vl_eval.json`

Bug found and fixed:

- Some VLM responses used a single string for `visible_issues`.
- The helper previously converted that string with `list(value)`, producing one character per issue.
- `scripts/evaluate_sprite_with_ollama_vl.py` now coerces strings to a one-item issue list and tests cover the case.

Updated conclusion:

- LocalVL is useful for semantic action checks, especially "does this look like the requested action?"
- LocalVL is not sufficient for fine artifact detection or adoption by itself. It over-scored the rejected source endpoint as high still-image quality.
- The local evaluation workflow must require both deterministic gates and semantic review:

```text
still adoption = deterministic gate pass + Agent visual pass
action adoption = still adoption + motion gate pass + Agent action pass + LocalVL action pass
```

## 2026-06-14 Start-Reference LocalVL

Implemented a start-reference-specific LocalVL evaluator:

```text
scripts/evaluate_start_reference_with_ollama_vl.py
```

It evaluates still start-reference images for:

- full-body framing;
- right-facing side/profile;
- walk-contact pose;
- readable separated shoes;
- single-character composition;
- plain background;
- model-sheet/turnaround or prop contamination.

The evaluator is explicitly secondary:

```text
local_vl_role: secondary_start_reference_review
```

Proof run:

```text
outputs/20260614_002335/local_vl_eval/anima_start_reference_retake_vl/start_reference_vl_eval.json
```

Result:

- LocalVL plus consistency rules marked the candidate `is_walk_ready_start_reference: false`.
- Deterministic blockers were propagated:
  - `deterministic_selection_not_candidate_ok`
  - `deterministic_shoes_unreadable`
- LocalVL also contributed semantic blockers:
  - `local_vl_low_shoe_readability_score`
  - `local_vl_low_side_view_score`
  - `local_vl_low_walk_contact_score`

Observation:

The raw normalized booleans can still be over-permissive, but the numeric scores plus deterministic override produced the correct final decision. Keep LocalVL as a semantic secondary review, not a sole start-reference gate.

## 2026-06-14 Sidecar Start-Reference And Probe Review

Start-reference review:

```text
outputs/20260614_010050/local_vl_eval/anima_sidecar_start_reference_vl/start_reference_vl_eval.json
```

LocalVL agreed with the deterministic gate:

- `is_walk_ready_start_reference: true`
- selected deterministic status: `candidate_ok`
- no blocking reasons

Animation quality review:

```text
outputs/20260614_010359/sprite_asset_quality_flow/anima_sidecar_probe_quality/local_vl/local_vl_eval/local_vl/local_vl_eval.json
```

LocalVL over-promoted the short animation:

- `is_readable_walk_action: true`
- `is_adoptable_as_animation_or_walk_endpoint: true`
- visible issues still included brightness/saturation drift and foot smears.

Final quality-flow decision:

```text
rejected_animation_candidate
```

Reason:

- deterministic artifact gate rejected the clip.
- motion readability passed, but artifact gate found lower-body afterimages, duplicate-silhouette risk, and ghost/contact artifacts.

Rule update:

LocalVL can support semantic action readability, but it must not override artifact, region, or Agent visual rejection. If LocalVL says "adoptable" and deterministic gate says "rejected", final status remains rejected.
