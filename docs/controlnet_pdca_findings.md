# ControlNet PDCA Findings

Date: 2026-06-10

## Main Rule

The main workflow is `novaOrangeXL + ControlNet(OpenPose)` with 120-frame outputs. The reference image is interpreted as character design. Frame thinning is out of scope and belongs to a separate export skill.

## Commands

```bash
uv run python scripts/build_pose_templates.py --output-root pose_templates --frame-count 120
uv run python scripts/pdca_controlnet_assets.py --input assets/reference/Anima_00013_.png --action attack_sword --output-root outputs_controlnet_pdca --pose-template-root pose_templates --frame-count 120 --retakes 3
uv run python scripts/pdca_controlnet_assets.py --input assets/reference/Anima_00013_.png --action walk --output-root outputs_controlnet_pdca --pose-template-root pose_templates --frame-count 120 --retakes 1
```

Repeat the PDCA command with `idle`, `attack_axe`, `attack_bow`, `hit_light`, `hit_heavy`, and `hit_knockback` to reproduce the full action sweep.

## Result Summary

All generated candidates wrote the expected output contract:

- `frames/*.png`
- `contact_sheet.png`
- `preview.gif`
- `spritesheet.png`
- `manifest.json`
- `evaluation_report.json`
- `controlnet_pose/*.png`
- `comfy_workflows/*.json`
- `pose_vs_generated_contact_sheet.png`

All action summaries passed Godot manifest playback validation at 120 frames and 768x768.

## Visual Findings

- `attack_sword`: best current proof is `outputs_controlnet_pdca/anima_00013/attack/attack_sword_identity_lock/pose_vs_generated_contact_sheet.png`. After fixing numeric pose-template ordering, a representative rerun also passed Godot at `outputs_controlnet_pdca_sorted/anima_00013/attack/attack_sword_baseline/pose_vs_generated_contact_sheet.png`. Sword appears and the pose follows the template, but weapon continuity and foreground fragmentation still need cleanup.
- `walk`: E2E generation works, but the contact sheet shows duplicated/crowd-like failure in part of the sequence. This is not an acceptable final walk cycle yet.
- `idle`: generated and loads in Godot, but foreground fragmentation triggers the quality gate.
- `attack_axe`: axe appears in the generated frames, but the active attack phase reads too much like standing or posing. Retake should strengthen active pose contrast and weapon guidance.
- `attack_bow`: rejected as a practical asset. The character does not reliably hold a bow/string/arrow even though OpenPose is supplied. This needs bow-specific control guidance beyond body OpenPose.
- `hit_light`, `hit_heavy`, `hit_knockback`: generated and load in Godot, but multiple/fragmented foreground issues remain. `hit_knockback` visibly creates extra face/character fragments and should be retaken.

## Quality Gate

Do not adopt a candidate based on heuristic score alone. A candidate must pass:

- side-by-side pose template review
- contact sheet review over the full 120-frame sequence
- `evaluation_report.json` issue-code review
- Godot playback validation

Current quality gates correctly mark most baseline candidates as `needs_retake_or_manual_review` even when the raw score is high.

## Next Retake Priorities

1. Add action-specific ControlNet guidance for weapons and hit reactions: bow/string/arrow, axe/sword swing arcs, hit displacement.
2. Add foreground-mask or segmentation cleanup to reduce duplicate character fragments.
3. Add a local visual semantic recognizer for weapon presence and extra-character detection; heuristic foreground metrics are not enough.
4. Keep `seed_step=0`, fixed framing, and `novaOrangeXL_v120.safetensors` as the default until a checkpoint comparison beats it on full-sequence readability.
