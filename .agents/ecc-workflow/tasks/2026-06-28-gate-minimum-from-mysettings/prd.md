# PRD

## Request

Bring in only the useful Gate / AgenticOS-adjacent parts from `kino-6/MySettings`, then run the
existing project workflow.

## Scope

- Add a small project-local Codex safety baseline.
- Add lightweight structured workflow docs and skills for substantial work.
- Avoid importing large skill packs, broad MCP defaults, WSL/Mac setup scripts, or external
  harness tooling.
- Preserve unrelated existing worktree changes.

## Non-Goals

- Do not install anything.
- Do not run MySettings setup scripts.
- Do not replace the user's global Codex config.
- Do not change sprite assets as part of the Gate workflow import.

## Acceptance Criteria

- The repo has a minimal `.codex/` Gate baseline.
- The repo has lightweight `.agents/ecc-workflow/` task/check structure.
- The useful ECC skills are available project-locally.
- Existing Python/Godot/visual-gate workflows are run and outcomes recorded.

