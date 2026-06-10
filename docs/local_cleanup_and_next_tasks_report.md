# Local Cleanup And Next Tasks Report

Date: 2026-06-11
Branch: `codex/asset-generation-workflow-pdca`

## Purpose

This report preserves the useful findings from the local PDCA runs before cleaning generated intermediate output folders.

Generated `outputs*` directories are intentionally not part of the source artifact for this branch. The durable branch artifacts are:

- source scripts
- reusable pose templates
- Skill documentation
- findings reports
- tests
- `Tasks.md`

## Cleanup Scope

The following local generated folders were considered cleanup targets because they are gitignored intermediate outputs:

| Folder | Approx. size |
| --- | ---: |
| `outputs` | 137.15 MB |
| `outputs_action_variants_effect_pdca` | 176.70 MB |
| `outputs_action_variants_pdca` | 111.98 MB |
| `outputs_artifact_repair_pdca` | 130.82 MB |
| `outputs_checkpoint_sweep` | 155.91 MB |
| `outputs_controlnet_pdca` | 2025.39 MB |
| `outputs_controlnet_pdca_sorted` | 200.99 MB |
| `outputs_multi_asset_pdca` | 122.41 MB |
| `outputs_multi_asset_pdca_refined` | 14.16 MB |
| `outputs_pdca` | 44.21 MB |
| `outputs_rigged_pdca` | 9.72 MB |
| `outputs_sfc_motion_pdca` | 24.96 MB |
| `outputs_video_walk_probe` | 136.67 MB |
| `outputs_wan_action_repro` | 24.47 MB |
| `outputs_wan_artifact_pdca` | 5.57 MB |
| `outputs_wan_img2img_refine` | 79.69 MB |
| `outputs_wan_walk_i2v` | 75.60 MB |

Total approximate cleanup target: `3475.40 MB`.

`outputs/.gitkeep` should remain so the canonical output root exists in a fresh checkout.

## Preserved Findings

The following reports preserve the main technical findings:

- `docs/controlnet_pdca_findings.md`
- `docs/wan_i2v_walk_findings.md`
- `docs/img2img_refine_pdca_findings.md`
- `docs/artifact_repair_pdca_findings.md`
- `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`

Key conclusions:

- `novaOrangeXL` remains the preferred SDXL checkpoint for this project.
- OpenPose/ControlNet templates are useful reusable controls, but body pose alone is insufficient for weapon structure.
- Wan `WanAnimateToVideo` with `reference_image + pose_video + TrimVideoLatent + post-trim` is the best local video-consistent path found so far.
- SDXL Image2Image helps polish frames after plausible motion exists, but it does not repair structural errors.
- Explicit masked inpaint can clean small ghost artifacts while preserving unmasked character pixels.
- Duplicate legs, large duplicate silhouettes, fragmented weapons, and missing weapon contact should be treated as retake/retrim or generation-control failures.

## Current Workflow State

The practical local workflow is:

```text
reference image + natural-language request
-> structured action/spec
-> reusable pose/action controls
-> local ComfyUI generation
-> trim/select plausible span
-> Image2Image polish when motion is plausible
-> explicit artifact repair gate
-> Godot/contact-sheet review before adoption
```

The workflow exists, but generated quality is not yet adoption-grade for production game assets.

## Recommended Next Tasks

These are candidates for the next `Tasks.md` planning pass:

- [ ] Add automatic best-span selection before Image2Image.
- [ ] Add a dedicated `run` pose template instead of reusing `walk`.
- [ ] Add weapon-specific control assets for `attack_sword`, `attack_axe`, and `attack_bow`.
- [ ] Generate weapon masks or line guides before Wan/video generation.
- [ ] Add foreground/person masking so background cleanup does not touch the character.
- [ ] Add a batch PDCA runner that compares Wan settings, trim spans, img2img settings, and artifact gates in one summary.
- [ ] Add a compact adoption package exporter that copies only selected `preview.gif`, `contact_sheet.png`, `comparison_sheet.png`, and reports into a small review folder.
- [ ] Add local quality metrics for duplicate silhouette area, lower-body blob count, weapon continuity, and background contamination.
- [ ] Add Godot playback validation for the selected Wan/refined/repaired candidate, not only older manifest-based outputs.
- [ ] Keep generated output cleanup as a repeatable script or documented maintenance step.

## Cleanup Rule Going Forward

After each PDCA run:

1. Promote durable findings into `docs/`.
2. Keep source code, workflow scripts, pose templates, tests, and Skills in git.
3. Do not commit heavy generated frames unless explicitly requested.
4. Delete or archive `outputs*` folders after representative findings are documented.

