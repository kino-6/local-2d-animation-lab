# Implementation

## Plan

1. Create a branch for the Gate import.
2. Add only the minimal useful project-local Codex and ECC workflow files.
3. Ignore private local workspace notes.
4. Run existing verification workflows.
5. Report any workflow findings separately from this Gate import.

## Decisions

- Kept MySettings MCP defaults out of this repo to avoid hidden network/process startup costs.
- Kept MySettings setup scripts out of this repo because they modify machine state.
- Added a small `.codex/config.toml` with safety defaults and profiles only.
- Added task/check skills instead of the full vendored skill catalog.

## Files

- `.codex/AGENTS.md`
- `.codex/config.toml`
- `.agents/ecc-workflow/**`
- `.agents/skills/ecc-task-workflow/SKILL.md`
- `.agents/skills/ecc-final-check/SKILL.md`
- `.agents/skills/ecc-finish-work/SKILL.md`
- `.gitignore`

