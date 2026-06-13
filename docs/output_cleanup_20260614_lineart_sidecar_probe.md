# Output Cleanup: 2026-06-14 Lineart Sidecar Probe

Date: 2026-06-14

## Scope

This cleanup records the local `outputs/` sessions produced by the lineart sidecar carrier probe before deleting them. The durable knowledge is kept in tracked docs so future work does not depend on stale generated folders.

Archived task checkpoint:

```text
docs/archive/Tasks_20260614_sidecar_suitable_lower_body_control_probe_completed.md
```

## Local Output Sessions Before Cleanup

| Session | Purpose | Size | Files | Decision |
| --- | --- | ---: | ---: | --- |
| `outputs/20260613_234244/` | sidecar ControlNet model inventory before download | `0 MB` | `3` | knowledge recorded |
| `outputs/20260613_234258/` | `t2i_lineart_sdxl` acquisition report | `0 MB` | `3` | model installed |
| `outputs/20260613_234308/` | sidecar ControlNet model inventory after download | `0 MB` | `3` | knowledge recorded |
| `outputs/20260613_234318/` | rebuilt 120-frame lineart lower-body sidecar source | `1.48 MB` | `365` | source diagnostics passed |
| `outputs/20260613_234423/` | Probe A generation, `Anima_00013_.png` + lineart sidecar `0.35` | `14.70 MB` | `42` | `rejected_diagnostic` |
| `outputs/20260613_234634/` | Probe A gates | `68.42 MB` | `143` | `rejected_diagnostic` |
| `outputs/20260613_234732/` | Probe B generation, `ComfyUI2025_131891_trim.png` + lineart sidecar `0.15` | `12.47 MB` | `42` | `rejected_diagnostic` |
| `outputs/20260613_234839/` | Probe B gates | `57.57 MB` | `143` | `rejected_diagnostic` |

## Durable Findings Kept In Git

Detailed documents:

- `docs/reference_lock_motion_template_deep_dive.md`
- `docs/walk_candidate_comparison.md`
- `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
- `Tasks.md`

Key retained facts:

- `t2i-adapter_diffusers_xl_lineart.safetensors` was downloaded to:
  - `C:\LocalWork\StabilityMatrix\Data\Packages\ComfyUI\models\controlnet\SDXL\t2i-adapter_diffusers_xl_lineart.safetensors`
- ComfyUI listed the model under `ControlNetLoader`.
- The `foot_contact_lineart` sidecar source was valid as a source-control image:
  - `sampled_min_ankle_x_separation: 0.1205`
  - `sampled_min_foot_box_x_gap: 0.03002`
  - `unclear_ankle_separation_count: 0`
  - `unclear_foot_box_count: 0`
- Probe A failed:
  - artifact `retake_required: 8/8`
  - visible guide leakage `7/8`
  - span hard failures `8/8`
  - visual result: guide/line leakage, fragments, and no usable walk asset.
- Probe B failed:
  - artifact `retake_required: 8/8`
  - span hard failures `8/8`
  - region retake `8/8`
  - visual result: fewer explicit line leaks, but composition/action collapsed around the reference rather than becoming a readable 2D walk.

Conclusion:

```text
Lineart sidecar can load and influence the image.
But sidecar strength/model type is not the next bottleneck.
The start/reference image must first be walk-ready, full-body, side-view, and sprite-framed.
```

## Cleanup Action

After this report is committed, the following local folders may be deleted:

- `outputs/20260613_234244/`
- `outputs/20260613_234258/`
- `outputs/20260613_234308/`
- `outputs/20260613_234318/`
- `outputs/20260613_234423/`
- `outputs/20260613_234634/`
- `outputs/20260613_234732/`
- `outputs/20260613_234839/`

Future generation must again create fresh, auditable runs under:

```text
outputs/<YYYYMMDD_HHMMSS>/<category>/<run-label>/
```
