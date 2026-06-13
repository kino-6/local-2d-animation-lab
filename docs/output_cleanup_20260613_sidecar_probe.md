# Output Cleanup: 2026-06-13 Sidecar Probe

Date: 2026-06-13

## Scope

This cleanup records the last local `outputs/` sessions before deletion. The goal is to keep durable knowledge in versioned docs and avoid making future work depend on stale local run folders.

Archived task checkpoint:

```text
docs/archive/Tasks_20260613_lower_body_sidecar_control_probe_completed.md
```

## Local Output Sessions Before Cleanup

| Session | Purpose | Size | Files | Decision |
| --- | --- | ---: | ---: | --- |
| `outputs/20260613_222505/` | synthetic side-view foot-contact v3 source and `lower_body_sidecar` | `2.28 MB` | `365` | knowledge recorded; can be regenerated |
| `outputs/20260613_223902/` | OpenPose-only foot-contact v3 8-frame generation | `5.72 MB` | `33` | `rejected_diagnostic` |
| `outputs/20260613_224018/` | OpenPose-only v3 gates | `34.36 MB` | `143` | knowledge recorded |
| `outputs/20260613_225444/` | secondary OpenPose-family sidecar035 8-frame generation | `5.48 MB` | `42` | `rejected_diagnostic` |
| `outputs/20260613_225559/` | sidecar035 gates | `32.48 MB` | `143` | knowledge recorded |

Additional old package root:

```text
source_probe_packages/
```

Size before cleanup: `5.41 MB`, `59` files. This root violates the current output policy because new generated artifacts should live under `outputs/<timestamp>/...`. It is treated as stale local evidence after the durable findings below have been recorded.

## Durable Findings Kept In Git

Detailed documents:

- `docs/reference_lock_motion_template_deep_dive.md`
- `docs/walk_candidate_comparison.md`
- `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`

Key retained facts:

- Best current reference-locked ControlNet proof is still:
  - `outputs/20260613_214841/reference_pose_regen/walk_ipadv_style_precise_upper_mask_sideview_v2_8f/`
  - Status: `selected_proof_only`, not adopted.
- Foot-contact metadata is useful for validating the synthetic template, but OpenPose-only does not transmit toe, heel, or foot-box semantics into generated shoes/contact.
- Secondary OpenPose-family sidecar control was active, but not good enough:
  - sidecar output: `outputs/20260613_225444/reference_pose_regen/walk_ipadv_upper_mask_foot_contact_v3_sidecar035_8f/`
  - artifact hard failures improved against OpenPose-only v3: `3/8 -> 2/8`
  - span motion improved against OpenPose-only v3: `8.918 -> 10.505`
  - region retakes worsened: `2/8 -> 3/8`
  - feet/contact temporal instability worsened: `0.02694 -> 0.0582`
  - visual review found shoe/leg recolor, lower-body ghosting, and unstable foot rendering.

Conclusion:

```text
Do not continue scalar tuning of an OpenPose-family secondary sidecar ControlNet as the mainline.
The next mechanism must carry lower-body constraints with a more suitable signal:
lineart, softedge, canny/sketch, depth/normal, segmentation, or mask/evaluation use.
```

## External Model Notes

The next model probe should not assume compatibility until tested locally.

- `lllyasviel/sd_control_collection` lists already-renamed SDXL control files, including canny, depth, softedge, T2I Adapter lineart, sketch, and openpose variants.
- `xinsir/controlnet-union-sdxl-1.0` documents support for many conditions including depth, canny, lineart, anime lineart, softedge, segment, normal, and multi-control examples.
- A GitHub discussion for the SDXL union model notes that the model can be downloaded from Hugging Face and recommends a `controlnet++_union_sdxl` style rename for filter compatibility.

Practical implication for this repo:

```text
First test a single-purpose sidecar carrier, preferably T2I Adapter lineart/sketch or SDXL softedge.
Use union only after the local ComfyUI loader/control-type behavior is verified.
```

## Cleanup Action

After this report is committed, the stale local run folders may be deleted:

- `outputs/20260613_222505/`
- `outputs/20260613_223902/`
- `outputs/20260613_224018/`
- `outputs/20260613_225444/`
- `outputs/20260613_225559/`
- `source_probe_packages/`

Future generation must create fresh, auditable runs under:

```text
outputs/<YYYYMMDD_HHMMSS>/<category>/<run-label>/
```
