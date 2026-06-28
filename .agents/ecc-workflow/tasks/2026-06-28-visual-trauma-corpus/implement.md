# Implementation

## Plan

1. Add non-destructive auto-fix adoption checks in `scripts/visual_asset_gate.py`.
2. Add a corpus-style pytest module for known visual trauma cases.
3. Run focused and full validation, including strict Godot pack validation.

## Decisions

- Keep the trauma corpus synthetic for now so it is small, deterministic, and does not add binary
  fixture churn.
- Evaluate auto-fix candidates before adopting them. A candidate is rejected when it introduces any
  new finding, increases finding count, substantially increases hard vertical cut run length, or
  meaningfully reduces the main foreground component ratio.
- Re-check actions after pack-level style normalization. If normalization makes an action unsafe,
  restore that action's pre-normalization adopted frames.

## Files

- `scripts/visual_asset_gate.py`
- `tests/test_visual_trauma_corpus.py`
