# PRD

## Request

Improve the material quality of the active nun skirt boots character sprite pack by running a
small PDCA cycle.

## Scope

- Diagnose current visual gate failures on the active adoptable pack.
- Improve real material defects where deterministic automation can safely do so.
- Tune visual gate rules only where the previous rule conflicts with action-expected motion.
- Keep the active Godot pack loadable and production-gate compatible.

## Non-Goals

- Do not redesign the character or change the accepted pack identity.
- Do not import external generation workflows or broad research tooling.
- Do not overwrite unrelated pre-existing worktree changes.

## Acceptance Criteria

- The active pack visual gate reports `production_ready`.
- Strict Godot pack validation passes with `--require-production-ready`.
- Focused and full Python tests pass.
- Remaining risk is documented as human art-direction review, not a known automated blocker.
