# ECC Workflow Specs

Stable context for agents working in this repository.

## Repository Role

`natural-sprite-lab` is a local-first Python/Godot prototype for producing 2D game sprite
animation assets. The current production-facing target is a `character_sprite_asset_pack` with
transparent frames, spritesheets, preview GIFs, runtime metadata, visual gate reports, and Godot
playback validation.

## Durable Rules

- Keep generated/reviewable asset packages under `outputs/adoptable/` when they are intended as
  active deliverables.
- Keep one-off experiments, PDCA notes, and historical findings in `docs/` rather than overloading
  the README.
- Preserve source identity and accepted-pack style rules when changing production asset packs.
- Do not reintroduce broad 120-frame/video/ControlNet research paths into a task whose scope is
  pack maintenance, Gate workflow, or production-ready action cleanup.
- Godot-visible manifests should stay loadable by the existing headless pack validation.
- Local workflow and agent rules should be additive and small. Avoid importing large external
  harnesses, broad MCP sets, or machine-wide setup scripts into this repo.

## When To Create Task Artifacts

Create a task folder under `.agents/ecc-workflow/tasks/` when any of these are true:

- The work touches multiple files or workflows.
- The work may continue across sessions.
- The work changes agent behavior, skills, setup rules, or other durable automation.
- Acceptance criteria are not obvious from the user prompt.

Skip task artifacts for tiny answers, one-line edits, or direct command output.

## Default Final Gate

Before finalizing substantial work, verify:

- Branch name and changed files are understood.
- Diff scope matches the newest user request.
- No secrets, credentials, host-private paths, or unrelated generated churn were added.
- Relevant Python/Godot/visual-gate checks ran, or a clear reason is recorded.
- Follow-ups are named instead of silently bundled.

