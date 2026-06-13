# Walk Short Probe PDCA 2026-06-13

Objective: improve the local-first 2D game walk asset route before spending on a 121-frame generation. The adoption target remains a natural 2D game animation asset from a character reference plus natural-language action. Packaging alone is not success.

## Runs

| run | motion mean/max | region lower/foot/jitter | region decisions | repair gate | visual verdict |
|---|---:|---:|---:|---:|---|
| `base_i2v_cmf1_noop` | 13.094/30.369 | 11/33/24 | local 9, retake 24 | no repair 2, retake 4, repair 27 | Walk readable but strong foot ghosts and luma/background drift. |
| `base_i2v_cmf2_noop` | 13.094/30.369 | 11/33/24 | local 9, retake 24 | n/a | Identical to cmf1; `continue_motion_max_frames` is a no-op for `WanImageToVideo`. |
| `animate_pose_cmf1_rejected` | 4.462/16.783 | 0/27/14 | local 7, retake 24, postprocess 2 | retake 33 | Rejected: dark silhouette collapse. |
| `prompt_d_i2v` | 12.136/30.896 | 6/33/20 | local 13, retake 20 | no repair 6, retake 7, repair 20 | Improved vs base, still has foot ghosts. |
| `prompt_e_i2v_best_single` | 12.201/33.190 | 4/33/20 | local 13, retake 20 | no repair 5, retake 7, repair 21 | Best single probe; lower-body pale lowest, still rejected. |
| `vace_lower_hint_rejected` | 1.683/4.236 | 21/17/9 | local 24, retake 3, postprocess 6 | retake 33 | Rejected: white-out/translucent body, too little motion. |
| `prompt_e_seed_repeat_static` | 9.329/52.968 | 5/33/0 | local 33 | no repair 28, retake 5 | Rejected: mostly static despite low deterministic jitter. |
| `clean_start_02_rejected` | 11.213/19.103 | 28/33/19 | local 3, retake 30 | retake 29, repair 4 | Rejected: guide/background leakage amplified by Wan. |

## Key Outputs

- Baseline i2v cmf1: `outputs_wan_short_walk_probes/walk_len33_cmf1_prompt_base_20260613_104358`
- Prompt D i2v: `outputs_wan_short_walk_probes/walk_len33_i2v_prompt_d_clean_small_stride_20260613_110545`
- Prompt E i2v, best single probe: `outputs_wan_short_walk_probes/walk_len33_i2v_prompt_e_slow_separated_feet_20260613_111114`
- Prompt E seed repeat: `outputs_wan_short_walk_probes/walk_len33_i2v_prompt_e_seed_repeat_721338_20260613_112121`
- VACE rejected probe: `outputs_wan_short_walk_probes/walk_len33_vace_lower_hint_strength065_20260613_111703`
- Clean start candidates: `outputs_fullbody_reference_walk_ready/ComfyUI2025_131891_trim_20260613_112743`
- Clean start Wan rejected probe: `outputs_wan_short_walk_probes/walk_len33_i2v_prompt_e_clean_start_02_20260613_113053`

## Findings

- `continue_motion_max_frames` should not be used as a comparison axis for plain `WanImageToVideo`; it did not enter the generated workflow and cmf1/cmf2 outputs were identical.
- Prompt constraints help: the prompt E wording reduced deterministic lower-body pale labels from `11/33` to `4/33` on the original start frame.
- Foot/contact artifacts are still universal on the best motion-bearing i2v probes: `33/33`.
- `WanAnimateToVideo` with the current `wan_walk_lower` control produced an unusable dark silhouette. This route needs a separate node/control calibration before more generation.
- The local VACE model is available but the tested lower-hint route over-whitened and made the subject translucent, with too little useful motion.
- Seed repeat exposed a gate weakness: deterministic jitter can look good when the clip is nearly static. Motion readability must remain an Agent/semantic gate, not just a region count.
- New start-frame generation with `novaOrangeXL` can produce readable side candidates, but automatic selection chose a back-view candidate. Human/semantic start-frame selection is required.
- A cleaner side start frame did not automatically improve Wan; guide/background leakage and residual panel background were amplified into the clip.

## Current Decision

Do not promote any current 33-frame probe to 121 frames.

The best single probe is `prompt_e_i2v_best_single`, but it is still a rejected proof because foot ghosts remain on every frame and seed repeat did not preserve a readable walk. The next practical improvement is start-frame quality/selection and background cleanup before Wan, plus an explicit motion-readability gate that rejects near-static clips.
