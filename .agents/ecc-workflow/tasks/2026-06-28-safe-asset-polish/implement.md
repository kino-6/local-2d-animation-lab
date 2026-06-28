# Implementation

## Plan

1. Inspect the active pack contact sheet and visual metrics.
2. Trial targeted weapon-readability polish, but reject it if it creates visible double-line artifacts.
3. Trial the non-destructive safe auto-fix candidate.
4. Adopt the candidate only if it remains production-ready and improves measurable material metrics.

## Decisions

- Rejected the manual blade-highlight candidate because it made some attack frames look like they
  had duplicate blades.
- Adopted the safe auto-fix candidate because it kept the contact sheet visually stable while
  reducing residual fringe and saturation drift.
