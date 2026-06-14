# Next Asset Generation Routes

## Context

`walk_8frame_sideview_baseline` has achieved its infrastructure goal:

- 8 frames are generated.
- `spritesheet.png` is generated.
- `preview.gif` is generated.
- `contact_sheet.png` is generated.
- `manifest.json` is generated.
- The output package is game-loadable.

Route conclusion:

```text
baseline_complete_but_not_artistically_viable
```

Keep this route as a technical baseline only. Do not continue minor parameter tuning on the
deterministic stylized renderer. Its failure mode is clear: it reads as a geometric puppet or
walk-cycle diagram rather than a viable 2D game character animation.

## Constraints For The Next Route

- Do not return to broad generative research.
- Do not add ComfyUI, Wan, video generation, ControlNet, or new model integrations in this planning step.
- Do not create 120-frame outputs.
- Do not continue the purely geometric body renderer.
- Do not attempt attack, hit, run, idle, or weapon actions.
- Stay focused on an 8-frame side-view walk asset.

## Route A: Artist-Authored Base Sprite + AI-Assisted Cleanup

Input:

- one manually created or manually edited 8-frame rough sprite;
- optional reference image.

Output:

- cleaned sprite sheet;
- preview GIF.

Purpose:

- most practical route for game assets;
- human controls pose and silhouette;
- AI only helps cleanup, color consistency, edge repair, and small corrections.

Evaluation:

| Criterion | Assessment |
| --- | --- |
| Can produce a game-loadable 8-frame walk cycle? | Yes. The human-authored rough already defines the frame count, canvas, and poses. |
| Avoids geometric puppet look? | Yes, if the rough sprite is drawn or edited as a real sprite rather than constructed from primitives. |
| Preserves character identity? | High. A human can preserve the important visual cues before AI cleanup. |
| Retake-friendly? | High. Individual frames can be fixed directly. |
| Human-fixable in Aseprite? | High. This route is designed around Aseprite-friendly frames. |
| Local-first? | Yes, if cleanup uses local tools or optional local image-to-image passes. |
| Avoids 120-frame research? | Yes. It stays at 8 frames. |

Risk:

- requires at least rough manual sprite work;
- AI cleanup must be constrained so it does not redraw pose or identity.

## Route B: Reference-Derived Character Redesign + Deterministic Animation

Input:

- one reference image.

Process:

1. Convert the character into a simplified game-sprite design sheet.
2. Animate that simplified design.

Purpose:

- avoid pretending the original illustration can directly become animation frames;
- produce a new game-suitable version of the character;
- make animation easier by simplifying proportions, silhouette, and costume detail first.

Evaluation:

| Criterion | Assessment |
| --- | --- |
| Can produce a game-loadable 8-frame walk cycle? | Yes, after the redesign sheet exists. |
| Avoids geometric puppet look? | Medium to high, if the redesign is artistically authored or strongly style-guided. |
| Preserves character identity? | Medium. Identity becomes an interpreted sprite version, not the original illustration. |
| Retake-friendly? | Medium. Fixes may require editing both the design sheet and animation frames. |
| Human-fixable in Aseprite? | Medium to high, depending on how clean the simplified sheet is. |
| Local-first? | Yes. The redesign and deterministic animation can be local. |
| Avoids 120-frame research? | Yes. It stays centered on an 8-frame cycle. |

Risk:

- can still drift into a puppet look if the redesign is not authored as real sprite art;
- requires a separate design-sheet acceptance gate before animation.

## Route C: Pose-Template Image Generation Per Keyframe

Input:

- reference image;
- 8 explicit pose templates;
- strong consistency constraints.

Output:

- 8 generated keyframes;
- contact sheet;
- rejection report.

Purpose:

- test whether image generation can produce usable individual frames;
- avoid video-model drift;
- reject quickly if identity, limbs, contact, or silhouette break.

Evaluation:

| Criterion | Assessment |
| --- | --- |
| Can produce a game-loadable 8-frame walk cycle? | Possible, but not reliable until consistency gates are strong. |
| Avoids geometric puppet look? | Yes when successful, because frames are image-generated rather than primitive-rendered. |
| Preserves character identity? | Medium to low risk. Identity consistency is the main failure point. |
| Retake-friendly? | Medium. Individual keyframes can be regenerated or edited, but failures may be frequent. |
| Human-fixable in Aseprite? | Medium. Fixability depends on whether limbs and silhouette are close enough. |
| Local-first? | Yes if using already available local generation tools, but no new backend should be added blindly. |
| Avoids 120-frame research? | Yes. It generates only 8 explicit keyframes and rejects bad sets quickly. |

Risk:

- identity and limb consistency may fail per frame;
- can produce attractive stills that do not loop cleanly;
- needs strict rejection reports to avoid accepting broken frames.

## Recommendation

Implement Route A first.

Route A is the most likely to produce an actual usable 2D game asset because it puts pose,
silhouette, and timing under human control. The current deterministic renderer proved that package
infrastructure is solved, but also showed that geometric construction is the wrong place to seek
artistically viable animation. Route A uses that infrastructure while moving the art-critical
decisions to a human-editable 8-frame rough.

Next implementation target:

```text
artist_authored_8frame_walk_cleanup
```

Success should mean:

- rough 8-frame input can be packaged;
- cleanup does not change frame count, pose intent, or contact timing;
- output remains Aseprite/Godot-friendly;
- failures are reported per frame rather than hidden behind a generated preview.

## Route A Implementation

Implemented entry point:

```text
scripts/package_artist_authored_walk_cleanup.py
```

Default output:

```text
outputs/adoptable/artist_authored_8frame_walk_cleanup/
```

This implementation is intentionally limited to deterministic cleanup and packaging. It does not
create the rough art. A human-authored 8-frame rough remains required input.
