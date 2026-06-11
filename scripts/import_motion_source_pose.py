from __future__ import annotations

import argparse
import json
from pathlib import Path

from natural_sprite_lab.motion_source import write_motion_source_template


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert extracted OpenPose/DWPose-style JSON into local 120-frame pose templates."
    )
    parser.add_argument("--source", required=True, type=Path, help="Pose JSON file or directory of JSON frames.")
    parser.add_argument("--output-root", default=Path("pose_templates"), type=Path)
    parser.add_argument("--action", required=True, help="Action name such as run, walk, attack, or hit.")
    parser.add_argument("--variant", default=None, help="Optional variant name. Defaults to the action.")
    parser.add_argument("--frame-count", default=120, type=int)
    parser.add_argument("--target-template-root", default=Path("pose_templates"), type=Path)
    parser.add_argument("--target-template-name", default=None)
    parser.add_argument("--render-width", default=512, type=int)
    parser.add_argument("--render-height", default=512, type=int)
    parser.add_argument(
        "--render-style",
        default="wan_confidence_lower",
        choices=(
            "controlnet",
            "controlnet_thin",
            "wan_line",
            "wan_lower",
            "wan_confidence_lower",
            "wan_balanced",
            "vace_walk_silhouette",
            "vace_walk_lower_hint",
        ),
    )
    parser.add_argument("--min-confidence", default=0.05, type=float)
    parser.add_argument("--source-start-index", default=None, type=int)
    parser.add_argument("--source-end-index", default=None, type=int)
    parser.add_argument("--min-frame-mean-confidence", default=None, type=float)
    parser.add_argument(
        "--min-ankle-x-separation",
        default=None,
        type=float,
        help="Drop source frames where left/right ankle x distance is below this fraction of source pose width.",
    )
    args = parser.parse_args()

    report = write_motion_source_template(
        args.source,
        args.output_root,
        action=args.action,
        variant=args.variant,
        frame_count=args.frame_count,
        target_template_root=args.target_template_root,
        target_template_name=args.target_template_name,
        render_width=args.render_width,
        render_height=args.render_height,
        render_style=args.render_style,
        min_confidence=args.min_confidence,
        source_start_index=args.source_start_index,
        source_end_index=args.source_end_index,
        min_frame_mean_confidence=args.min_frame_mean_confidence,
        min_ankle_x_separation=args.min_ankle_x_separation,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
