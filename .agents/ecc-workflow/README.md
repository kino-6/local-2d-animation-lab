# ECC Structured Workflow

This directory contains a small, project-local workflow borrowed from the useful parts of
`kino-6/MySettings`. It is intentionally not a full external harness install.

Use it when work benefits from durable task context, explicit verification, or a final gate review.
Routine one-shot edits can continue to use the normal Codex flow.

## Layout

- `spec/`: durable repository standards and reusable project knowledge.
- `templates/task/`: lightweight `prd.md`, `implement.md`, `check.md`, and `journal.md` shapes.
- `tasks/`: optional task folders named like `YYYY-mm-dd-short-slug/`.
- `workspace/`: local session notes. This is gitignored except for its README.

## Lifecycle

1. Start with `ecc-task-workflow` when work is broad, risky, or likely to span sessions.
2. Create a task folder only when durable artifacts would make the work easier to resume or review.
3. Keep artifacts small: scope, decisions, acceptance criteria, and verification.
4. Use `ecc-final-check` before summarizing substantial work.
5. Use `ecc-finish-work` when closing a structured task or preparing a handoff.

## Guardrails

- Do not install or run external harness tooling from this workflow.
- Do not create vendor-owned workflow directories unless the user explicitly asks for a trial.
- Keep secrets, host credentials, and private machine state out of tracked task artifacts.
- Treat networked tools as read-only unless the user explicitly approves an external action.
- Preserve existing worktree changes that are unrelated to the task.

