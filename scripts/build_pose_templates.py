from __future__ import annotations

import argparse
import json
from pathlib import Path

from natural_sprite_lab.pose_templates import load_pose_sequence, write_default_templates


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reusable OpenPose keypoint templates.")
    parser.add_argument("--output-root", default=Path("pose_templates"), type=Path)
    parser.add_argument("--frame-count", default=120, type=int)
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--height", default=512, type=int)
    args = parser.parse_args()

    written = write_default_templates(
        root=args.output_root,
        frame_count=args.frame_count,
        width=args.width,
        height=args.height,
    )
    validation = {}
    for name in written:
        sequence = load_pose_sequence(args.output_root, name)
        validation[name] = {"frames": len(sequence), "ok": True}
    validation_path = args.output_root / "validation.json"
    validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.output_root)


if __name__ == "__main__":
    main()
