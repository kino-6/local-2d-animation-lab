# PRD

## Goal

Treat visible highlight clipping in preview GIFs as a production quality problem, not as an
acceptable artifact.

## Problem

The previous gate passed the active nun pack even though the preview GIFs made white hair and skin
highlights look blown out. The static contact sheet understated the issue because the character was
reviewed mostly as still frames.

## Acceptance Criteria

- The visual gate reports foreground highlight clipping metrics.
- Actions with excessive foreground highlight clipping are blocked.
- Auto-fix reduces clipped highlights without changing canvas, action counts, or Godot loadability.
- Active preview GIFs are regenerated with a reviewable non-white background.
- The active nun pack passes the stricter gate after correction.

