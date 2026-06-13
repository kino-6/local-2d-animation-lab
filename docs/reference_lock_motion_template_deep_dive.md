# Reference Lock + Motion Template Deep Dive

Date: 2026-06-13

## Core Finding

The current split is:

```text
IPAdapter works for identity/reference stabilization.
But final 2D game animation quality is controlled by:
identity lock + action-specific side-view motion template + strict gate.
```

This means the next useful work is not "increase IPAdapter" or "increase OpenPose".
The workflow needs clearer responsibility boundaries:

- IPAdapter: preserve character design, palette, outfit, face/hair, and sprite rendering style.
- Action-specific side-view motion template: encode body mechanics, view angle, phase timing, feet/contact, and limb readability.
- ControlNet schedule: apply the motion template strongly enough to change pose, but not so strongly that guide pixels or front-view bias leak into the image.
- Gate: reject candidates where the still frames are attractive but not usable as game animation frames.

## What The Latest Probes Proved

### 1. Identity lock is real

`outputs/20260613_211402/reference_pose_regen/walk_ipadapter_openpose_d072_c110_ip065_8f/`

Compared with OpenPose-only probes, IPAdapter kept hair color, outfit, and overall character identity more stable under higher denoise/control pressure. The failure was not "IPAdapter does nothing".

### 2. Ambiguous motion controls poison the result

The existing reusable walk OpenPose controls are too front-facing/ambiguous for side-view sprite walking. With strong ControlNet they produced guide burn-in and upper-body/arm redraw; with weak ControlNet they became too static.

This means the control source is not a neutral implementation detail. It is part of the asset design.

### 3. Side-view motion controls changed the outcome

`outputs/20260613_212815/reference_pose_regen/walk_ipadapter_sideview_pose_mid_8f/`

This was the best short proof because it combined:

- IPAdapter Plus SDXL reference lock;
- a synthetic side-view walk control source;
- mid-strength ControlNet;
- a shorter IPAdapter end schedule.

It is still rejected, but it is a better failure: the frame set now reads closer to side-view walking, so the remaining blockers are narrower.

### 4. Gate rejection is still meaningful

The promising proof still failed artifact gates:

- `retake_required: 5/8`
- foot/contact review labels on all frames
- lower-body pale/afterimage labels on several frames
- one silhouette redraw/jitter label

So the correct status is `promising_probe`, not `selected_proof_only` or `adopted_animation_candidate`.

## Deeper Hypothesis

The current workflow has three coupled pressures:

```text
denoise        = how much the frame is allowed to move away from the reference image
ControlNet     = how much the pose template can force body mechanics
IPAdapter      = how much the reference image pulls design/composition back
```

If IPAdapter is too strong or active too late:

- the character stays stable;
- motion collapses toward the source pose;
- hands/legs may ignore the action template.

If ControlNet is too strong or active too late:

- motion increases;
- pose guide burn-in and skeleton-shaped artifacts appear;
- the model may redraw body parts around the guide rather than preserve the character.

If denoise is too low:

- identity is clean;
- animation is almost static.

If denoise is too high:

- motion becomes possible;
- identity and local anatomy become fragile unless the reference lock and template are clean.

The practical target is not a single magic value. It is a narrow operating band where:

```text
denoise permits pose change
ControlNet acts early/mid then gets out
IPAdapter preserves identity early/mid but does not override pose mechanics late
```

## Next Mechanism Improvements

### A. Upgrade from simple IPAdapter to IPAdapter Advanced

Local node support confirms `IPAdapterAdvanced` exposes:

- `weight_type`: `linear`, `composition`, `composition precise`, `style transfer precise`, etc.
- `combine_embeds`
- `start_at` / `end_at`
- `embeds_scaling`
- optional `attn_mask`

The next probe should add a `--ipadapter-advanced` mode to `scripts/regenerate_pose_sequence_controlnet.py`.

First test matrix:

| Label | Weight type | Weight | End | Embeds scaling | Reason |
| --- | --- | ---: | ---: | --- | --- |
| adv_comp_precise | `composition precise` | 0.45 | 0.60 | `K+mean(V) w/ C penalty` | Preserve layout/design with less style bleed |
| adv_style_precise | `style transfer precise` | 0.55 | 0.62 | `K+mean(V) w/ C penalty` | Preserve color/style while letting pose template drive composition |
| adv_linear_short | `linear` | 0.50 | 0.52 | `V only` | Shorter reference pull, less motion collapse |

Expected signal:

- If motion improves but identity drifts, IPAdapter was too weak/short.
- If identity improves but legs freeze, IPAdapter is still overriding pose.
- If guide burn-in appears, ControlNet strength/end is still too high or control images are too visible/noisy.

### B. Add IPAdapter attention mask

The IPAdapter docs state that `attn_mask` limits where the adapter applies. For sprite walking, full-image reference pressure may be too broad: it can pull the whole body back toward the source stance.

Test masks:

- upper-body-heavy mask: head, hair, torso, outfit colors remain locked; legs are freer for motion.
- whole-character soft mask: prevents background/style leak but keeps full design.
- head/hair mask only: tests whether face/hair identity can be locked without freezing walk mechanics.

This is useful because our failure is lower-body action quality, not face identity.

### C. Improve the side-view motion template itself

Current side-view synthetic control helped, but still has ambiguities:

- arm positions can pull hands into awkward poses;
- feet/contact positions are not explicitly evaluated before generation;
- stride phases may create crossed or vanishing feet in sampled frames;
- OpenPose lines are visual pixels and can still leak if ControlNet pressure is too high.

Template improvements:

- lower-body-first template variants with clearer ankle separation;
- hands closer to body and less visually dominant;
- per-frame metadata for stance/swing foot;
- reject sampled control spans where ankle separation or foot contact is unclear;
- compare normal `controlnet` against thinner/lower-contrast render only if guide burn-in returns.

### D. Make the gate diagnose cause, not only fail

The gate should separate:

- identity failure;
- motion-template failure;
- ControlNet burn-in;
- lower-body duplication;
- foot/contact unreadability;
- background/style drift.

For the current route, `duplicate_silhouette_area_high` with near-zero repair mask coverage suggests the heuristic may be over-triggering on valid stride silhouettes. The visual review still matters, but the gate should expose enough sub-metrics to avoid chasing false positives.

## Recommended Next PDCA Order

1. Add `IPAdapterAdvanced` mode to the regeneration script.
2. Generate three 8-frame probes using the same side-view pose source:
   - `composition precise`
   - `style transfer precise`
   - shorter `linear`
3. Gate and visually review all three.
4. If the best still has frozen legs, add upper-body/head-focused `attn_mask`.
5. If the best has broken feet/contact, improve the pose template before trying more identity models.
6. Only after a clean 8-17 frame proof, spend on 120-frame output.

## 2026-06-13 Advanced + Mask PDCA Result

Implemented in:

- `scripts/regenerate_pose_sequence_controlnet.py`
- `scripts/build_synthetic_sideview_motion_source.py`

Generated cleaner side-view walk controls:

```text
outputs/20260613_214207/motion_source_video_pdca/motion_sources/sideview_walk_adv_identity_lock_v2/
```

This control source passed the new pre-generation motion diagnostics:

- sampled ankle separation passed;
- unclear ankle separation count: `0`;
- min sampled ankle separation: `0.082`.

Advanced IPAdapter probes showed that `style transfer precise` was the best unmasked direction, but still not usable:

| Probe | Output | Deterministic gate | Decision |
| --- | --- | --- | --- |
| `composition precise` | `outputs/20260613_214241/reference_pose_regen/walk_ipadv_comp_precise_sideview_v2_8f/` | artifact `retake_required: 8/8` | rejected |
| `style transfer precise` | `outputs/20260613_214341/reference_pose_regen/walk_ipadv_style_precise_sideview_v2_8f/` | artifact `retake_required: 3/8`, span score `0.72707` | best unmasked proof, still rejected |
| `linear short` | `outputs/20260613_214434/reference_pose_regen/walk_ipadv_linear_short_sideview_v2_8f/` | artifact `retake_required: 6/8` | rejected |

Attention-mask probes were more informative:

| Mask | Output | Gate summary | Agent visual review |
| --- | --- | --- | --- |
| upper body | `outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/` | artifact `no_repair_needed: 8/8`; span hard failures `0`; region `retake_required: 2/8` | best current proof; readable side-view walk, but color/style drift and foot/contact artifacts remain |
| whole character | `outputs/20260613_220050/reference_pose_regen/walk_ipadv_style_precise_whole_mask_sideview_v2_8f/` | artifact `no_repair_needed: 8/8`; span hard failures `0`; region `retake_required: 3/8` | more structurally stable but stiffer |
| head/hair | `outputs/20260613_220147/reference_pose_regen/walk_ipadv_style_precise_head_mask_sideview_v2_8f/` | artifact `retake_required: 5/8` | rejected; too much lower-body redraw and outfit drift |

Conclusion:

```text
IPAdapterAdvanced helps, and attention masks are not cosmetic.
The upper-body mask is the best current compromise:
it preserves enough identity while allowing more lower-body motion.
```

But this is still `selected_proof_only`, not an adopted 2D game asset. The remaining blocker is lower-body/foot mechanics and local redraw stability. A 120-frame spend is not justified until a short proof passes both deterministic gates and visual review.

## 2026-06-13 Lower-Body Contact Control PDCA

Implemented:

- explicit `foot_contact` metadata on synthetic side-view `PoseFrame` outputs;
- per-frame `ground_y`, `stance_foot`, `swing_foot`, `contact_state`, foot `ankle/toe/heel/box`;
- motion diagnostics for foot-box readability, contact counts, stance/swing balance, and stance sliding;
- lower-body sidecar frames under the same timestamped motion-source run.

The first clean-pose retake kept ankle separation readable but exposed a better failure:

```text
outputs/20260613_222321/motion_source_video_pdca/motion_sources/sideview_walk_foot_contact_v1/
```

It passed ankle separation but failed foot-box readability:

- `unclear_ankle_separation_count: 0`
- `unclear_foot_box_count: 19`
- `passes_foot_box_separation: false`

This is useful because it catches a common 2D-game problem before generation: ankles can be separated while the actual shoe/foot silhouettes would still overlap.

The corrected source is:

```text
outputs/20260613_222505/motion_source_video_pdca/motion_sources/sideview_walk_foot_contact_v3/
```

Key diagnostics:

- `sampled_min_ankle_x_separation: 0.204`
- `sampled_min_foot_box_x_gap: 0.11352`
- `unclear_ankle_separation_count: 0`
- `unclear_foot_box_count: 0`
- `max_stance_slide_delta: 0.00345`
- `passes_min_ankle_x_separation: true`
- `passes_foot_box_separation: true`

The next generation experiment should use this as the motion source. The sidecar is not final artwork; it is a structured lower-body/contact control candidate for future ControlNet, mask, or retake routing.

## 2026-06-13 Foot-Contact v3 Generation Probe

Probe:

```text
outputs/20260613_223902/reference_pose_regen/walk_ipadv_upper_mask_foot_contact_v3_8f/
```

Settings matched the previous best upper-body-mask IPAdapterAdvanced route, but replaced the pose source with:

```text
outputs/20260613_222505/motion_source_video_pdca/motion_sources/sideview_walk_foot_contact_v3/controlnet/
```

Gate reports:

- artifact: `outputs/20260613_224018/artifact_repair/walk_ipadv_upper_mask_foot_contact_v3_8f_mask_gate/artifact_repair_report.json`
- span: `outputs/20260613_224018/span_selection/walk_ipadv_upper_mask_foot_contact_v3_8f_span/span_selection_report.json`
- region: `outputs/20260613_224018/region_diagnostics/walk_ipadv_upper_mask_foot_contact_v3_8f_regions/region_diagnostics_report.json`

Result versus the previous best proof:

| Metric | Previous upper-body mask | Foot-contact v3 |
| --- | ---: | ---: |
| Artifact hard failures | `0/8` | `3/8` |
| Region retake decisions | `2/8` | `2/8` |
| Span motion | `11.725` | `8.918` |
| Mean lower-body temporal delta | `0.07925` | `0.06004` |
| Mean feet/contact temporal delta | `0.04478` | `0.02694` |

Decision: `rejected_diagnostic`.

The cleaner foot-contact template improved lower-body stability metrics, but did not improve the generated sprite enough to beat the prior proof. The artifact gate worsened due to duplicate-silhouette hard failures, and motion became more conservative.

The important takeaway is narrower:

```text
Foot/contact metadata is useful for template validation.
But OpenPose-only does not carry toe/heel/foot-box semantics into generated shoes/contact.
```

Next mechanism should use `lower_body_sidecar/` as a separate non-visible control or mask candidate. Do not keep tuning only OpenPose geometry, text prompts, or scalar ControlNet/IPAdapter weights.

## Non-Goals For The Next Loop

- Do not switch to InstantID/PuLID before the side-view motion control is clean; they mainly help face identity and add dependency complexity.
- Do not tune only denoise/control strength for another long loop.
- Do not accept a pretty contact sheet unless it reads as a game animation.
- Do not rely on postprocess to fix duplicate feet, vanishing legs, or bad walk mechanics.
