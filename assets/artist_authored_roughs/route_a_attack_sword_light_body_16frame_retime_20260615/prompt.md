# Route A Attack Sword Light Body 16 Frame Retime

- tool/source: local retime from committed accepted 12-frame body roughs
- local: true
- input: `assets/artist_authored_roughs/imagegen_attack_sword_light_body_12frame_tiles_20260615/rough_frames/`
- action: `attack_sword_light`
- direction: `right`
- view: `side`
- frame_count: `16`
- loop: `false`
- background: green-key source frames, cleaned by the pack builder
- layers: body-only source; sword and slash effect are generated as native separate layers during packaging

## Phase Spec

1. ready
2. anticipation 1
3. anticipation 2
4. draw back
5. windup
6. slash start
7. active slash 1
8. active slash 2
9. active follow-through
10. overshoot
11. recoil 1
12. recoil 2
13. settle 1
14. settle 2
15. recover
16. ready return

## Notes

This is not cross-fade interpolation. It is a conservative source-frame retime using the previously
accepted body-only rough frames, with tiny foreground shifts on repeated source poses so timing can be
reviewed without ghosted blended frames.

The purpose is to separate anticipation, active frames, overshoot, and recovery for Godot/Aseprite
review while keeping the current accepted pack style and native weapon/effect layer route.
