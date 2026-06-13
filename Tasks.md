# Tasks: Start-Reference Retake With LocalVL Review

Archived checkpoint:

```text
docs/archive/Tasks_20260614_walk_ready_start_reference_gate_completed.md
```

Cleanup report:

```text
docs/output_cleanup_20260614_start_reference_gate.md
```

## Rules

- [x] Generate local-first 2D game animation assets from a character reference image plus a natural-language action request.
- [x] Treat the input image as a design reference, not pixels to directly puppet.
- [x] Save all new generated run artifacts only under `outputs/<timestamp>/...`.
- [x] Target adopted animation source length is 120 frames; short probes are evidence only.
- [x] Long-running ComfyUI scripts must expose queue controls and progress visibility.
- [x] Do not promote outputs where guide lines, duplicate lower limbs, broken feet, strong afterimages, shoe unreadability, front-view drift, model-sheet residue, composition collapse, or identity drift are visible.

## Current Interpretation

- [x] The current blocker is not sidecar strength or lineart model availability.
- [x] The reference/start image must first be a walk-ready full-body side-view sprite frame.
- [x] The last Anima start-reference run produced no `candidate_ok`.
- [x] Auto-selection can choose a clean still image that is not walk-ready; start-reference selection needs stronger semantic review.
- [x] LocalVL must not be the sole adoption gate, but it can help flag front-view, model-sheet, and walk-readiness failures before animation spend.

## Plan

The next loop improves the start-reference stage, not animation:

```text
design reference
-> stricter candidate prompts
-> deterministic start-frame gate
-> LocalVL start-reference semantic review
-> Agent visual review
-> animation probe only if candidate_ok + visually walk-ready
```

Primary route:

- Improve `scripts/generate_fullbody_reference_candidates.py` with stricter side-profile/contact-pose candidates and explicit animation-probe blocking metadata.
- Add a dedicated start-reference LocalVL prompt or wrapper so LocalVL reviews still candidates for:
  - full-body;
  - right-facing side/profile;
  - not front view;
  - not model sheet;
  - readable separated shoes;
  - walk-cycle contact pose;
  - plain background.

## Active PDCA

- [ ] Cleanup stale local outputs.
  - Archive old `Tasks.md`.
  - Write `docs/output_cleanup_20260614_start_reference_gate.md`.
  - Delete `outputs/20260614_000549/` after durable findings are recorded.
- [ ] Add a start-reference LocalVL evaluator.
  - Reuse Ollama local models and JSON normalization patterns from `scripts/evaluate_sprite_with_ollama_vl.py`.
  - Accept one or more candidate/contact-sheet images.
  - Output `start_reference_vl_eval.json`.
  - Mark LocalVL as `secondary_start_reference_review`, not adoption authority.
  - Add tests for consistency rules when LocalVL reports front-view or non-walk-ready issues.
- [ ] Tighten candidate prompts for retake.
  - Add candidate variants that avoid "standing portrait" and "model sheet".
  - Emphasize one full-body character, right-facing profile, walk-contact pose, shoes apart, knees/ankles visible.
  - Strengthen negative prompt against bicycles, props, secondary figures, model sheets, frontal pose, and cropped/hidden shoes.
  - Keep deterministic gate unchanged unless a concrete gap is found.
- [ ] Generate fresh start-reference candidates.
  - Primary input: `assets/reference/Anima_00013_.png`.
  - Use `novaOrangeXL_v120.safetensors` and `SDXL\OpenPoseXL2.safetensors`.
  - Check ComfyUI `/queue` before submitting.
  - Save under `outputs/<timestamp>/fullbody_reference/...`.
- [ ] Run start-reference LocalVL review.
  - Evaluate `contact_sheet.png` and selected `start_frame.png`.
  - Record LocalVL verdict and compare with deterministic gate and Agent review.
- [ ] Agent visual review.
  - Inspect contact sheet and selected start frame.
  - Decide one of:
    - `candidate_ok_for_short_probe`;
    - `blocked_start_reference_quality`;
    - `rejected_diagnostic`.
- [ ] Optional short animation probe only if allowed.
  - Do not run if selected candidate is front-facing, foot-ambiguous, or model-sheet-like.
  - If allowed, run one 8-frame proof and gate it.
- [ ] Update durable knowledge.
  - `docs/start_frame_first_walk_pdca.md`
  - `docs/local_vl_asset_evaluation_pdca.md`
  - `docs/reference_lock_motion_template_deep_dive.md`
  - `docs/walk_candidate_comparison.md`
  - `docs/local_skills/natural-sprite-controlnet-pdca/SKILL.md`
  - `Tasks.md`

## Success Criteria

- [ ] Old output clutter is removed after knowledge capture.
- [ ] Tests pass for touched code.
- [ ] Fresh start-reference generation exists, or queue/model blocker is recorded.
- [ ] LocalVL start-reference review exists or Ollama blocker is recorded.
- [ ] No animation generation is run from an obviously bad start/reference.
- [ ] Result is labeled honestly as one of:
  - `candidate_ok_for_short_probe`;
  - `blocked_start_reference_quality`;
  - `blocked_local_vl_unavailable`;
  - `rejected_diagnostic`;
  - `selected_proof_only`.
