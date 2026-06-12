# Action Generalization PDCA Report

This report checks whether the single-keyframe Wan i2v lesson from walk generation generalizes beyond walking.

## Setup

- New reference image: `assets/reference/ComfyUI2025_131891_trim.png`
- Reference type: bust-up anime character image with blonde hair, black hood, and black/yellow futuristic armor.
- Key issue: Wan i2v preserves start-image framing, so the bust-up input is not directly suitable for full-body 2D game animation.
- Mitigation: generate a 1024 full-body side-view keyframe first, then run single-keyframe Wan i2v for multiple action types.

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
