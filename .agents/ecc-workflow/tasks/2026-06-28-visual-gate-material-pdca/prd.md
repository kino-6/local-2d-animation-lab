# PRD

## Request

Add visual quality gates for issues visible in the all-actions contact sheet, then run PDCA until
the active sprite pack either improves and passes or has clear remaining blockers.

## Scope

- Detect green/cyan edge fringing around transparent sprites.
- Detect weak sword readability in sword attack actions.
- Detect action-level style drift against the pack's baseline look.
- Apply safe automatic fixes to the active adoptable pack and verify the Godot workflow.

## Non-Goals

- Do not redesign poses or hand-author new frames.
- Do not replace the current pack generation pipeline.
- Do not hide true visual blockers by weakening existing gates.

## Acceptance Criteria

- New gates have focused tests.
- Active pack visual report includes the new metrics.
- Active pack passes strict visual and Godot production gates after safe fixes.
- Any remaining concern is documented as manual art-direction review.
