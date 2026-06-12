# Action Generalization PDCA Report

This report checks whether the single-keyframe Wan i2v lesson from walk generation generalizes beyond walking.

## Setup

- New reference image: `assets/reference/ComfyUI2025_131891_trim.png`
- Reference type: bust-up anime character image with blonde hair, black hood, and black/yellow futuristic armor.
- Key issue: Wan i2v preserves start-image framing, so the bust-up input is not directly suitable for full-body 2D game animation.
- Mitigation: generate a 1024 full-body side-view keyframe first, then run single-keyframe Wan i2v for multiple action types.

External notes used:

- Wan2.1 / Wan i2v workflows support image-conditioned video generation, including first/last-frame style endpoint control in compatible workflows.
- Sprite-sheet research frames the problem as reference character plus pose/action sequence, not pure prompt generation.
- Community sprite workflows emphasize preparing full-body character references before animation and treating weapon/action details as separate controlled elements.

Full-body keyframe:

- Output root: `outputs_generalization_pdca/fullbody_reference/ComfyUI2025_131891_trim_20260612_200239`
- Selected keyframe: `outputs_generalization_pdca/fullbody_reference/ComfyUI2025_131891_trim_20260612_200239/selected_reference/start_frame.png`
- Visual decision: usable for generalization testing, but not an adopted reference. It is a generated interpretation of the bust-up design, not a faithful full-body extraction from the input pixels.

## Action Probes

All probes used:

- Mode: `i2v`
- Model: `wan2.1_i2v_480p_14B_fp16.safetensors`
- Resolution: `768x768`
- Length: `33`
- Steps: `8`
- CFG: `3.0`
- Post-process: BiRefNet foreground separation, span selection, strict artifact gate, Godot review package.

| Action | Review package | Motion / gate summary | Decision | Notes |
|---|---|---|---|---|
| `idle` | `review_packages/comfy2025_idle_breath_len33_generalization_review_20260612_202710` | BiRefNet `mask_ok: 33/33`; full gate `no_repair_needed: 33/33`; Godot `ok: true` | `adoptable_probe` | Subject is stable and clean, but the prompt drifted from side-view idle into a slow side-to-front turn. Useful for idle/turn, not a strict side idle. |
| `run` | `review_packages/comfy2025_run_len33_generalization_review_20260612_202914` | selected foreground motion `20.980`; full gate `repair_candidate: 2`, `lower_body_pale_afterimage_review: 3`; Godot `ok: true` | `selected_proof_only` | Strongest generalization evidence. It reads as a run, preserves identity reasonably well, but fast motion still creates lower-body afterimages and sparse-mask review labels. |
| `hit_heavy` | `review_packages/comfy2025_hit_heavy_len33_generalization_review_20260612_203118` | selected foreground motion `19.848`; full gate `retake_required: 1`; Godot `ok: true` | `rejected_but_promising` | The semantic action is clear: recoil, bend-back, fall/recovery energy. Quality fails because strong body rotation creates ghost silhouettes and one duplicate-leg risk. |
| `attack_sword` | `review_packages/comfy2025_attack_sword_len33_generalization_review_20260612_203324` | selected foreground motion `6.647`; full gate `retake_required: 3`; Godot `ok: true` | `rejected_needs_weapon_control` | The model invented a readable glowing sword/energy blade, which is encouraging. Weapon consistency, attack timing, and background glow are not reliable enough without weapon/action guidance. |

## Findings

- The walk finding is not walk-only. Single-keyframe Wan i2v also works for `idle`, `run`, `hit` reactions, and partially for weapon attacks.
- The route generalizes best when the action can be expressed as whole-body motion without adding new persistent objects.
- `run` is the clearest next production target after walk. The main remaining issue is the same family as walk: lower-body afterimages during fast leg motion.
- `hit_heavy` is semantically strong but structurally risky. It needs tighter action duration or key pose control so the character does not smear through large rotations.
- `attack_sword` needs an action-specific control sidecar: weapon guide, hand/weapon attachment validation, and possibly a short keyframe sequence. Prompt-only sword generation is not stable enough.
- The generated full-body reference step is now a first-class requirement when the user-provided input is bust-up or cropped.

## Updated Direction

Primary route:

```text
input character image
-> full-body side-view keyframe generation or selection
-> single-keyframe Wan i2v action probe
-> BiRefNet separation
-> strict full-source artifact gate
-> action-specific visual review labels
-> Godot review package
```

Action scope after this probe:

- Good candidates for the current route: `walk`, `run`, `idle`, `turn`, `hit_light`, `hit_heavy`.
- Requires extra action guidance: `attack_sword`, `attack_axe`, `attack_bow`, weapon throws, projectile attacks.
- Quality improvement should focus next on reducing afterimages for fast lower-body motion and preventing view drift for idle/turn actions.

## Follow-Up: First/Last Keyframe Probe

External workflow notes suggested using explicit action endpoints when first-frame-only i2v cannot control the destination pose. I implemented a local endpoint-keyframe generator and tested it on the ComfyUI2025 character.

Implementation:

- Added `scripts/generate_action_keyframe_candidates.py`.
- The script generates action endpoint candidates with OpenPoseXL + `novaOrangeXL_v120.safetensors`.
- Supported initial actions: `run`, `hit_heavy`, `attack_sword`.
- It writes candidate reports, contact sheets, and a selected `end_frame.png` for Wan first/last-frame generation.

Generated endpoint keyframes:

- Run endpoint: `outputs_generalization_pdca/action_keyframes/ComfyUI2025_131891_trim_run_keyframes_20260612_211813/selected_keyframe/end_frame.png`
- Hit endpoint: `outputs_generalization_pdca/action_keyframes/ComfyUI2025_131891_trim_hit_heavy_keyframes_20260612_211850/selected_keyframe/end_frame.png`

First/last probes:

| Action | Review package | Gate summary | Visual decision |
|---|---|---|---|
| `run` first/last | `review_packages/comfy2025_run_len33_first_last_review_20260612_213101` | full gate `no_repair_needed: 33/33`, Godot `ok: true` | Not adopted. Endpoint control worked, but the clip moves too slowly at first, then warps into the endpoint with dark/green smearing. First-frame-only `run` is still better as an action proof. |
| `hit_heavy` first/last | `review_packages/comfy2025_hit_heavy_len33_first_last_review_20260612_213306` | full gate `retake_required: 4/33`, Godot `ok: true` | Rejected. The endpoint helps the action arc, but the large crouch transition creates duplicate-leg and lower-body silhouette failures. |

Findings:

- First/last keyframes are useful for action intent, but only if the endpoint keyframe is itself sprite-like, side-view, clean, and close enough to the start framing.
- Bad or over-dramatic endpoint keyframes make Wan interpolate through broad smears rather than produce clean game frames.
- The automatic gate can miss endpoint-induced visual warping when each individual frame has a clean isolated foreground. Visual contact-sheet review remains mandatory.
- For `run`, the next endpoint should be a conservative stride pose, not a dramatic kick/high-stride illustration.
- For `hit_heavy`, use two short probes or a 3-stage key pose plan: neutral -> recoil -> low recovery. A single far endpoint is too much motion for clean first/last interpolation.

Updated local strategy:

```text
single-keyframe i2v: best for initial action proof and subject preservation
first/last i2v: use only with conservative endpoint keyframes
weapon actions: require weapon sidecar/key-pose control before first/last
```

## Follow-Up: Conservative Endpoint Keyframe Probe

After the first/last probe failed on over-dramatic endpoints, I tightened the endpoint templates for `run` and `hit_heavy` and added `hit_light` as a smaller reaction target.

Implementation update:

- `scripts/generate_action_keyframe_candidates.py` now uses conservative endpoint variants:
  - `run_low_stride`
  - `run_compact_forward_stride`
  - `hit_light_small_stagger`
  - `hit_light_guard_recover`
  - `hit_heavy_compact_recoil`
  - `hit_heavy_mid_recover`
- The templates explicitly reject high kicks, extreme crouches, falling poses, and dramatic illustration poses.
- Tests were updated in `tests/test_action_keyframe_candidates_script.py`.

Generated endpoint candidates:

| Action | Candidate root | Result |
|---|---|---|
| `run` | `outputs_general_action_quality/action_keyframes/ComfyUI2025_131891_trim_run_keyframes_20260612_221908` | Rejected for first/last use. The prompts asked for low/compact stride, but both images still became high-knee or kick-like illustration poses. |
| `hit_light` | `outputs_general_action_quality/action_keyframes/ComfyUI2025_131891_trim_hit_light_keyframes_20260612_221944` | Rejected. The candidates drifted to front-view standing, extra face fragments, and an extra small character fragment. |
| `hit_heavy` | `outputs_general_action_quality/action_keyframes/ComfyUI2025_131891_trim_hit_heavy_keyframes_20260612_222004` | Rejected for first/last use. `hit_heavy_compact_recoil` was the closest, but still failed the side-view/sprite endpoint bar; `hit_heavy_mid_recover` became a cropped dramatic crouch. |

Finding:

- Text prompt plus OpenPoseXL can describe the intended endpoint, but it does not reliably preserve a sprite-like side-view full-body framing.
- The failure mode is not only artifact noise. The generated endpoint image changes camera angle, framing, pose language, or adds secondary fragments before Wan ever sees it.
- Therefore, these endpoint candidates should not be passed into first/last Wan generation. Doing so would repeat the known endpoint-warp failure.

Next route:

```text
selected full-body side-view start frame
-> reference-conditioned / img2img endpoint generation with small pose delta
-> reject endpoint unless it remains single-character, side-view, full-body, and close to start framing
-> only then run first/last Wan
```

## Follow-Up: Reference-Conditioned Endpoint Probe

I added a `--source-image` path to `scripts/generate_action_keyframe_candidates.py`. When provided, the script now uses the selected full-body start frame as an img2img latent, applies the OpenPose endpoint through ControlNet, and records `source_delta` so the gate can distinguish "clean but not enough motion" from "broken endpoint".

Implementation update:

- Added `--source-image` for reference-conditioned endpoint generation.
- Added `--denoise` for img2img endpoint strength.
- Added `--min-endpoint-delta` and issue code `endpoint_delta_too_low`.
- Updated the candidate review summary with a `source_delta` column.

Probe source:

- Start frame: `outputs_generalization_pdca/fullbody_reference/ComfyUI2025_131891_trim_20260612_200239/selected_reference/start_frame.png`

Generated probes:

| Action | Candidate root | Settings | Result |
|---|---|---|---|
| `run` | `outputs_general_action_quality/action_keyframes_refcond/ComfyUI2025_131891_trim_run_keyframes_20260612_222745` | denoise `0.40`, control `0.58` | Much cleaner than txt2img endpoints, but pose change was too small. |
| `run` | `outputs_general_action_quality/action_keyframes_refcond/ComfyUI2025_131891_trim_run_keyframes_20260612_222924` | denoise `0.56`, control `0.74` | Still preserved side-view/full-body framing, but did not reach a readable run endpoint. |
| `run` | `outputs_general_action_quality/action_keyframes_refcond/ComfyUI2025_131891_trim_run_keyframes_20260612_223120` | denoise `0.72`, control `0.90` | Stronger settings still did not follow the OpenPose enough to become a run key pose. |
| `run` | `outputs_general_action_quality/action_keyframes_refcond/ComfyUI2025_131891_trim_run_keyframes_20260612_223625` | denoise `0.56`, control `0.74`, source-delta gate | Clean side-view single-character endpoint, but rejected with `endpoint_delta_too_low` (`source_delta` about `8.9`). |

Finding:

- Reference-conditioned endpoint generation fixes the major txt2img failures: front-view drift, high-kick illustration poses, cropped crouches, and secondary character fragments.
- However, with this workflow, the source image dominates the pose. Even stronger denoise/control settings preserved the character but failed to move the legs enough for a run endpoint.
- This route should not yet be used for first/last Wan, because it would produce an almost neutral interpolation endpoint.

Next implication:

- Keep reference-conditioned endpoint generation as the preferred safety baseline.
- Add stronger pose transfer or localized lower-body editing before expecting `run` endpoints from img2img.
- Candidate next probes: masked lower-body img2img, a denoise/control grid beyond `0.72/0.90`, or a ControlNet/IPAdapter-style identity split where pose can dominate without losing the character.
