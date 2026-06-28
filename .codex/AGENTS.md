# Codex Gate Baseline

This repository is a local-first 2D animation asset lab. Treat the active deliverables as
`character_sprite_asset_pack` outputs with explicit manifests, visual gates, and Godot playback
checks.

## Gate Rules

- Keep existing user or generated worktree changes intact unless the user explicitly asks for a
  revert or cleanup.
- For substantial repo changes, run the `ecc-final-check` behavior before the final response:
  inspect branch, changed files, scope, secrets/private state, and verification.
- Do not commit, push, publish, install global tools, or change external resources unless the user
  explicitly asks.
- Treat networked tools as read-only by default. Use them to inspect or verify, not to mutate
  third-party state without explicit approval.
- Keep host-specific credentials, tokens, local paths, and private machine state out of tracked
  files.
- Prefer adding small project-local workflow documents over importing large external harnesses or
  broad skill packs.

## Repo-Specific Verification

Choose checks based on the files touched:

- Python code: `uv run pytest` or focused `uv run pytest tests/<file>.py`.
- Sprite pack changes: `uv run python scripts/visual_asset_gate.py --manifest <manifest> --report <report>`.
- Godot import/playback changes: `godot --headless --path godot --script res://tests/pack_e2e_runner.gd -- --manifest <manifest>`.
- Formatting/diff hygiene: `git diff --check`.

If a relevant check cannot run in the current environment, record that honestly in the final
response.

## Structured Workflow

Use `.agents/ecc-workflow/` only for broad, risky, multi-file, multi-session, or agent-behavior
changes. Small one-shot edits do not need task artifacts.

