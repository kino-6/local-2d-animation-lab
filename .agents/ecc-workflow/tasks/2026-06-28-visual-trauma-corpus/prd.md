# PRD

## Request

Reduce visual-gate whack-a-mole by turning known material failures into a durable regression corpus
and making automatic fixes non-destructive.

## Scope

- Add a past-trauma corpus for known sprite-pack visual failures.
- Ensure all known cases are checked together in tests, not only as isolated one-off tests.
- Add a safety gate so auto-fix candidates are adopted only when they do not introduce new blocking
  visual findings.

## Acceptance Criteria

- Past trauma cases cover jump scale/contact-sheet sizing, hurt overlap/side panel, hurt hard cut,
  green/cyan fringe, weak weapon readability, and action style drift.
- Auto-fix does not make a hurt side-panel case worse by introducing hard vertical cuts.
- Active adoptable pack still passes visual/Godot production gates.
