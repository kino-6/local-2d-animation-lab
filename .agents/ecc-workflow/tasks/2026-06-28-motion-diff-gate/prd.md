# PRD

## Goal

Improve sprite asset quality gates so they catch motion-only visual failures that are hard to see
from a static contact sheet.

## Problem

The contact sheet is useful for scale, crop, and overlap review, but it can miss failures that only
become obvious when the action is played as an animation:

- A single frame jumps away from the previous and next frames.
- An action ends in a pose that cannot recover cleanly into `idle`.
- Generated `preview.gif` files drift from the manifest or silently become non-reviewable.

## Acceptance Criteria

- The visual gate reports adjacent frame ImageDiff metrics for each action.
- The visual gate blocks isolated abrupt frame deltas.
- Non-loop recovery actions compare their first and last frames against `idle`.
- Preview GIFs are validated E2E for frame count, canvas size, and visible frame-to-frame motion.
- The active nun sprite pack remains production-ready after the new checks.

