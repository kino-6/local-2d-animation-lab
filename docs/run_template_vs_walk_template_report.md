# Run Template vs Walk-Template Run Report

Date: 2026-06-11
Branch: `codex/next-asset-quality-plan`

## Purpose

Compare the previous `run` experiment that reused `pose_templates/walk` against the new dedicated `pose_templates/run` generation path.

The comparison is about workflow behavior, not final adoption quality. Neither result is production-ready.

## Compared Evidence

### Prior Run Using Walk Template

- Source report: `docs/wan_i2v_walk_findings.md`
- Output: `outputs_wan_action_repro/walk_i2v_20260611_004335/`
- Pose template: `walk`
- Prompt intent: running
- Curated frames: 8
- Mean frame delta: `16.624`
- Max frame delta: `20.437`
- Min frame delta: `7.198`
- Verdict: `research_only`

Observed behavior:

- The workflow transferred from walk to run at a rough motion level.
- Motion amplitude was stronger than the latest run-template probes.
- The output remained below adoption quality because fast-limb ghosting and background problems persisted.
- Reusing `walk` for run required prompt pressure and did not encode run-specific contact/airborne phases.

### New Run Using Dedicated Run Template

- Source report: `docs/next_phase_run_generation_pdca_report.md`
- Direct reference output: `outputs_next_phase_pdca/run_template_probe_20260611_025948`
- Best controlled output: `outputs_next_phase_pdca/run_from_cleaned_single_start_probe_20260611_030927`
- Final review package: `review_packages/run_cleaned_start_refined_review_20260611_031442`
- Pose template: `run`
- Selected frames: 8
- Best span score: `0.1644`
- Mean frame delta before img2img: `9.311`
- Mean frame delta after img2img: `10.57`
- Godot validation: `ok=true`
- Verdict: `needs_retake`

Observed behavior:

- The dedicated `run` template is reusable and now exists as a real control asset.
- Directly feeding the bust-up reference into Wan failed because Wan preserved the input framing.
- A single clean full-body side-view start frame improved the generated action readability.
- The output became more clearly side-view running than the direct reference attempt, but lower-body structure still failed.
- Low-denoise `novaOrangeXL` img2img polished the frames slightly but did not repair white-out legs, ghosting, or duplicate silhouette issues.

## Comparison Summary

| Topic | Walk Template Run | Dedicated Run Template |
| --- | --- | --- |
| Reusable action control | Weak; run is forced by prompt | Better; run phases are explicit |
| Motion amplitude | Higher | Lower in the best controlled probe |
| Full-body framing | Depended on start/reference selection | Requires a valid full-body start frame |
| Lower-body quality | Ghosting remained | Ghosting and white-out legs remain |
| Adoption quality | Not adoptable | Not adoptable |
| Main lesson | Workflow transfers, but action control is too generic | Template is correct direction, but start-frame and lower-body control are now bottlenecks |

## Decision

Keep `pose_templates/run` as the main path for run requests. Do not fall back to `walk` pose templates for running except as a baseline comparison.

The next quality improvement should focus on the input to Wan:

1. Automatically obtain one clean full-body side-view start frame.
2. Reject start frames with multiple foreground components.
3. Add foreground/person masking and character-mask support before background cleanup.
4. Tune run pose/video rendering for leg separation before trying more img2img.

## Cleanup Note

The compared output folders are local generated evidence and should remain uncommitted unless the user explicitly requests generated artifacts in git. This report and the compact review packages are the durable evidence for the branch.
