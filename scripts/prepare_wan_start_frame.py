from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from natural_sprite_lab.quality.start_frame import make_character_mask, make_start_frame_debug_sheet, prepare_clean_start_frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare one clean full-body start frame for Wan video generation.")
    parser.add_argument("--input-frame", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_next_phase_startframe"), type=Path)
    parser.add_argument("--run-label", default="wan_start_frame")
    parser.add_argument("--width", default=1024, type=int)
    parser.add_argument("--height", default=1024, type=int)
    parser.add_argument("--threshold", default=42, type=int)
    parser.add_argument("--padding-ratio", default=0.09, type=float)
    parser.add_argument("--max-secondary-ratio", default=0.30, type=float)
    args = parser.parse_args()

    label = _safe_label(args.run_label)
    run_dir = args.output_root / time.strftime(f"{label}_%Y%m%d_%H%M%S")
    output = run_dir / "start_frame.png"
    mask_output = run_dir / "character_mask.png"
    report = prepare_clean_start_frame(
        args.input_frame,
        output,
        width=args.width,
        height=args.height,
        threshold=args.threshold,
        padding_ratio=args.padding_ratio,
        max_secondary_ratio=args.max_secondary_ratio,
    )
    make_character_mask(output, mask_output)
    debug_sheet = make_start_frame_debug_sheet(args.input_frame, output, run_dir / "start_frame_debug_sheet.png")
    payload = report.to_dict()
    payload["character_mask"] = str(mask_output)
    payload["debug_sheet"] = str(debug_sheet)
    report_path = run_dir / "start_frame_report.json"
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "wan_start_frame"


if __name__ == "__main__":
    main()
