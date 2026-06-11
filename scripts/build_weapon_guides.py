from __future__ import annotations

import argparse
import json
from pathlib import Path

from natural_sprite_lab.weapon_guides import write_default_weapon_guides


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reusable weapon guide assets for action generation.")
    parser.add_argument("--output-root", default=Path("weapon_guides"), type=Path)
    parser.add_argument("--frame-count", default=120, type=int)
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--height", default=512, type=int)
    args = parser.parse_args()

    written = write_default_weapon_guides(
        root=args.output_root,
        frame_count=args.frame_count,
        width=args.width,
        height=args.height,
    )
    validation = {name: {"frames": len(data["frames"]), "ok": True} for name, data in written.items()}
    (args.output_root / "validation.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(args.output_root)


if __name__ == "__main__":
    main()
