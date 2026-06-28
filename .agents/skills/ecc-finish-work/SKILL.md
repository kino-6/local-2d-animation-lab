---
name: ecc-finish-work
description: Use when ending a structured ECC task or when context is filling up. Performs final review, records resume notes, and promotes reusable learning.
---

# ECC Finish Work

Use this skill when a structured task is done or the session needs a clean handoff.

## Finish Ritual

1. Run `ecc-final-check` behavior against the current diff.
2. Update the task `check.md` if a task folder exists.
3. Write local resume notes under `.agents/ecc-workflow/workspace/` only if useful.
4. Promote durable, non-private lessons to `.agents/ecc-workflow/spec/`.
5. Summarize:
   - branch name
   - files changed
   - verification run
   - unresolved risks or follow-ups

## Boundaries

- Do not commit, push, publish, or install tools unless the user asks.
- Do not archive or delete task folders automatically.
- Do not copy private journal details into tracked files.

