# PRD

## Goal

Integrate the accepted character sprite pack into a minimal Godot game-facing player node, not only
the review viewer.

## Acceptance Criteria

- A Godot `CharacterBody2D` can load the adopted sprite pack manifest.
- The player exposes game states for `idle`, `walk`, `run`, `jump`, `hurt`, and
  `attack_sword_light`.
- Runtime origin and collision metadata from the manifest are applied to the in-game node.
- The integration refuses non-production-ready packs when required.
- Headless Godot verification proves the player can load the active nun pack and transition through
  key gameplay actions.

