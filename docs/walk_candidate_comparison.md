# Walk Candidate Comparison

This table tracks walk candidates as sprite-sheet task candidates, not as isolated pretty frames.

| Candidate | Source route | Control style | Resolution | Length | Motion score | Gate summary | Status | Visual decision |
|---|---|---|---:|---:|---:|---|---|---|
| 512 v4 baseline | `run_synthetic_sideview_walk_v4_edge_stride` | `wan_balanced` | 512 | 121 | selected foreground motion `4.993` | full artifact `retake_required: 0/121` | `diagnostic` | Structurally stable but small and not visually strong enough. |
| 768 lower-control proof | v4 edge stride | `wan_walk_lower` | 768 | 121 | selected proof only | full artifact `retake_required: 2/121` | `selected_proof_only` | Better face/outfit readability, but full source failed. |
| Full-body reference v4 | 1024 generated side reference + v4 | `vace_walk_lower_hint` | 768 | 121 | selected foreground motion `3.019` to `3.912` | labeled full gate `retake_required: 2/121` | `rejected` | Identity stable, but conservative motion and foot-shadow/skin afterimage labels remained. |
| v5 contact-swing short proof | 1024 generated side reference + v5 | `vace_walk_lower_hint`, VACE `0.55` | 768 | 33 | selected foreground motion `7.695` | selected gate `retake_required: 0/16`; full 33 `retake_required: 2/33` | `selected_proof_only` | Solved low motion on a selected span, but not full-source adoption. |
| v5 contact-swing 121 probe | 1024 generated side reference + v5 | `vace_walk_lower_hint`, VACE `0.55` | 768 | 121 | selected foreground motion `5.569` | full gate `foreground_too_small: 51`; selected gate `retake_required: 0/16` | `selected_proof_only` | Motion improved, but legs/feet became faint and foreground preservation failed across the full source. |
| confidence-aware v5 retake | 1024 generated side reference + v5 | `vace_walk_confidence_hint`, VACE `0.65` | 768 | 33 | selected foreground motion `7.227` | full 33 `retake_required: 15/33` | `rejected` | Confidence-aware hint plus stronger VACE increased motion but reintroduced guide leakage, duplicate silhouette, and lower-body risks. |
| 1024 short probe | 1024 generated side reference + v5 | `vace_walk_lower_hint`, VACE `0.55` | 1024 | 17 | selected foreground motion `11.666` | full 17 `no_repair_needed: 17/17`; Godot `ok: true` | `rejected_by_visual_review` | Stronger foreground and legs, but outfit color drift, arm/hair afterimages, and facing/identity instability make it non-adoptable. |
| single-keyframe Wan i2v proof | full-body side reference only | no pose-control video | 768 | 33 | selected foreground motion `16.424` | full 33 `no_repair_needed: 33/33` | `selected_proof_only` | Best subject preservation so far; clean identity and no guide leakage, but still needs longer-source validation. |
| single-keyframe Wan i2v 121 strict | full-body side reference only | no pose-control video | 768 | 121 | selected foreground motion `18.208` | strict full 121 `retake_required: 0/121`; `lower_body_pale_afterimage_review: 12` | `selected_proof_only` | Solves VACE foreground shrinkage and reads as a walk, but recurring pale lower-body afterimages block adoption. |

## Current Interpretation

- The best route is now staged single-keyframe Wan i2v for base motion, followed by BiRefNet separation and strict artifact/review labeling.
- VACE contact-swing remains useful as a controlled-motion comparator, but it is no longer the preferred subject-preservation route.
- The latest blocker is not foreground shrinkage; it is recurring pale lower-body afterimages inside otherwise readable walking frames.
- The next retake should tune Wan i2v prompts/settings or source cropping to reduce ghosted lower-body motion, then rerun the strict 121-frame gate and visual review.
