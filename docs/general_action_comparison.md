# General Action Candidate Comparison

This table is for non-walk action probes. Keep walk-specific ranking in `docs/walk_candidate_comparison.md`.

## Current Decisions

| Action | Route | Evidence | Automatic result | Visual decision | Next action |
|---|---|---|---|---|---|
| `idle` | single-keyframe Wan i2v | `review_packages/comfy2025_idle_breath_len33_generalization_review_20260612_202710` | full gate clean, Godot ok | `adoptable_probe` for idle/turn, not strict side idle | Use as low-motion baseline only. |
| `run` | single-keyframe Wan i2v | `review_packages/comfy2025_run_len33_generalization_review_20260612_202914` | motion score `20.980`, Godot ok, lower-body review labels | `selected_proof_only` | Still the best current run proof; improve lower-body afterimages before adoption. |
| `run` | first/last Wan from dramatic endpoint | `review_packages/comfy2025_run_len33_first_last_review_20260612_213101` | frame gate clean, Godot ok | rejected visually due endpoint warp/dark smear | Do not use dramatic endpoint keyframes. |
| `run` | conservative txt2img endpoint | `outputs_general_action_quality/action_keyframes/ComfyUI2025_131891_trim_run_keyframes_20260612_221908` | endpoint candidates generated | rejected visually due high-kick/front/illustration pose drift | Do not pass to first/last Wan. |
| `run` | reference-conditioned endpoint | `outputs_general_action_quality/action_keyframes_refcond_rerun/ComfyUI2025_131891_trim_run_keyframes_20260612_231436` | `candidate_ok`, `source_delta` about `12.4` | rejected for action use; visually still near neutral/front standing | Keep `endpoint_delta_too_low`/visual action-readability blocker. |
| `run` | lower-body masked endpoint | `outputs_general_action_quality/action_keyframes_refcond_lower_body/ComfyUI2025_131891_trim_run_keyframes_20260612_233937` | `manual_review_or_retake`, `duplicate_silhouette_area_high` | rejected; mask can localize legs but redraws outfit/leg structure instead of producing a clean stride | Do not use local lower-body inpaint as endpoint driver without stronger pose/identity separation. |
| `run` | lower-body endpoint + 1024 still-image refinement | `outputs_image_quality_pdca/run_endpoint_quality_d035_bgclean160_20260612_234849` | artifact gate `adopted_full_source`, no review labels | accepted as still-image polish proof only; not accepted as a run/action endpoint | Use 1024 img2img refinement for polish after action semantics are already correct. |
| `hit_light` | reference-conditioned endpoint | `outputs_general_action_quality/action_keyframes_refcond_rerun/ComfyUI2025_131891_trim_hit_light_keyframes_20260612_233040` | `candidate_ok`, `source_delta` about `12.3-12.7` | rejected for first/last; too neutral and front-facing to read as hit | Wait until `run` endpoint control is action-bearing. |
| `hit_heavy` | single-keyframe Wan i2v | `review_packages/comfy2025_hit_heavy_len33_generalization_review_20260612_203118` | Godot ok, quality failures | semantic proof only | Split into short stages after endpoint control improves. |
| `hit_heavy` | first/last Wan from far endpoint | `review_packages/comfy2025_hit_heavy_len33_first_last_review_20260612_213306` | `retake_required: 4/33` | rejected due duplicate lower body / broad transition | Use neutral -> recoil and recoil -> recovery stages only after clean endpoints exist. |
| `hit_heavy` | reference-conditioned endpoint | `outputs_general_action_quality/action_keyframes_refcond_rerun/ComfyUI2025_131891_trim_hit_heavy_keyframes_20260612_233101` | `candidate_ok`, `source_delta` about `12.3-12.5` | rejected for first/last; too neutral/front-facing | Wait until `run` endpoint control is action-bearing. |
| `attack_sword` | prompt-only single-keyframe Wan i2v | `review_packages/comfy2025_attack_sword_len33_generalization_review_20260612_203324` | quality failures | rejected; readable blade appears but weapon continuity is not controlled | Requires sidecar: hands, blade line, slash arc, weapon mask. |

## Required Review Fields

Every future general-action package should record:

- `motion_score`
- `artifact_gate_summary`
- `visual_decision`
- `visual_labels`
- `godot_status`

Important visual labels:

- `endpoint_warp_or_pose_teleport_review`
- `side_to_front_view_drift_review`
- `background_tone_drift_review`
- `lower_body_pale_afterimage_review`
- `weapon_missing`
- `weapon_fragmented`
- `weapon_detached`

## Current Lesson

The current blocker is not queueing or lack of generation. It is action-bearing control while preserving a sprite-like character. Single-keyframe Wan can invent plausible motion, but fast lower-body actions still need quality cleanup. First/last Wan should stay gated until the endpoint is visually clean, side-view, and obviously action-bearing.

1024 img2img refinement can improve drawing quality after generation. The best current still-image recipe is recorded in `docs/image_quality_refinement_pdca.md`: denoise `0.35`, `cfg 5.4`, 1024x1024, and background cleanup threshold `160`. This can remove noise/panel artifacts, but it does not solve action semantics.
