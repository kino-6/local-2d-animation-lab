# Aseprite Import Notes

Keep the transparent canvas size unchanged for every action.
Use one Aseprite tag per action and keep the bottom-center canvas origin stable in the game runtime.

| action | frames | fps | loop | role |
| --- | ---: | ---: | --- | --- |
| walk | 8 | 8 | True | baseline locomotion loop |
| idle | 4 | 8 | True | subtle standing loop |
| run | 8 | 8 | True | faster locomotion loop |
| jump | 12 | 8 | False | non-looping jump arc |
| hurt | 8 | 8 | False | non-looping small damage reaction |
| attack_sword_light | 12 | 8 | False | non-looping light one-handed sword attack |

This pack is ready for runtime import review, not a guarantee that every future action is solved.
