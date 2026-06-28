---
name: ecc-final-check
description: Use before finishing substantial repo work. Reviews the diff against scope, repo specs, verification, and private-state boundaries.
---

# ECC Final Check

Use this skill before finalizing substantial changes in this repository.

## Inputs

- User request and newest constraints.
- Current branch and git diff.
- Relevant `.agents/ecc-workflow/spec/` files.
- Task artifacts under `.agents/ecc-workflow/tasks/`, when present.

## Check Procedure

1. Confirm the branch and changed files.
2. Compare the diff against the requested scope and any task `prd.md`.
3. Check for accidental secrets, credentials, host-private paths, or external action side effects.
4. Confirm relevant verification ran. If no automated check applies, record the manual or
   documentation check instead.
5. Identify follow-ups that should not be silently bundled into this change.

## Output

Report only actionable findings. If no blocking issue remains, say so and include the verification
that was run.

