from __future__ import annotations

import argparse
import json
from pathlib import Path

from natural_sprite_lab.models import Action
from natural_sprite_lab.postprocess.action_effects import make_action_effect_layers
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate local action effect layers for existing runs.")
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()

    updated = []
    for spec_path in args.output_root.rglob("animation_spec.json"):
        run_dir = spec_path.parent
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        action = Action(spec["action"])
        if action not in {Action.ATTACK, Action.HIT}:
            continue
        frames = sorted((run_dir / "frames").glob("*.png"))
        effect_paths, composited_paths = make_action_effect_layers(
            frames,
            spec.get("frame_plan", []),
            action,
            run_dir / "effects",
            run_dir / "frames_with_effects",
        )
        if effect_paths:
            make_contact_sheet(effect_paths, run_dir / "effect_contact_sheet.png")
        if composited_paths:
            make_contact_sheet(composited_paths, run_dir / "contact_sheet_with_effects.png")
        updated.append(str(run_dir))

    print(f"Updated {len(updated)} run(s)")
    for run_dir in updated:
        print(run_dir)


if __name__ == "__main__":
    main()
