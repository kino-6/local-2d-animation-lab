# Walk 8-Frame Review Checklist

Use this checklist for `walk_8frame_sideview_baseline` review. The route is still an MVP baseline,
not production art.

## Contract

- [ ] Exactly 8 frames exist.
- [ ] All frames share the same canvas size.
- [ ] PNG frames use transparent background.
- [ ] `spritesheet.png` exists.
- [ ] `preview.gif` exists and loops.
- [ ] `contact_sheet.png` exists and is easy to inspect.
- [ ] `manifest.json` includes `walk_readability`.
- [ ] The output is under `outputs/adoptable/walk_8frame_sideview_baseline/`.

## Animation Readability

- [ ] One character only.
- [ ] Foot contact is readable.
- [ ] No obvious foot sliding on contact/down frames.
- [ ] Contact, passing, and opposite-contact phases are visually distinct.
- [ ] Head remains mostly stable.
- [ ] Torso and hips feel connected.
- [ ] Arms swing opposite to legs.
- [ ] Loop closure is plausible from frame 7 back to frame 0.

## Identity Cues

- [ ] Pink hair remains visible.
- [ ] Side profile remains visible.
- [ ] Sailor-style white top remains visible.
- [ ] Red tie remains visible.
- [ ] Dark socks remain visible.
- [ ] Brown shoes remain visible.

## Import Suitability

- [ ] Suitable for Godot or Aseprite preview.
- [ ] Still labeled `baseline_not_production`.
- [ ] Still labeled `review_worthy_mvp_not_production`.
- [ ] Not claimed as production-ready art.
