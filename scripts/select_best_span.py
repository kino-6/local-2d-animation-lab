from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.quality import analyze_frame_quality, recommendation_table, select_best_span


def main() -> None:
    parser = argparse.ArgumentParser(description="Select the best contiguous animation span from generated frames.")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_span_selection"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--span-length", default=8, type=int)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--allow-hard-failures", action="store_true")
    parser.add_argument("--foreground-mask-dir", default=None, type=Path)
    parser.add_argument("--min-mean-motion-delta", default=0.0, type=float)
    parser.add_argument("--max-mean-foreground-mask-delta", default=None, type=float)
    parser.add_argument("--motion-metric", choices=("global", "foreground", "max"), default="global")
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_best_span")
    run_dir = args.output_root / time.strftime(f"{label}_%Y%m%d_%H%M%S")
    selected_dir = run_dir / "selected_frames"
    selected_dir.mkdir(parents=True, exist_ok=True)

    qualities = []
    previous = None
    for index, path in enumerate(frame_paths):
        qualities.append(analyze_frame_quality(path, index=index, previous_path=previous))
        previous = path
    foreground_mask_deltas = []
    if args.foreground_mask_dir:
        mask_paths = sorted(args.foreground_mask_dir.glob("*.png"), key=_frame_index)
        if len(mask_paths) != len(frame_paths):
            raise ValueError(
                f"foreground mask count mismatch: {len(mask_paths)} masks for {len(frame_paths)} frames"
            )
        foreground_mask_deltas = _foreground_mask_deltas(mask_paths)
        qualities = [
            replace(quality, foreground_mask_delta_prev=round(delta, 5))
            for quality, delta in zip(qualities, foreground_mask_deltas)
        ]

    selection = select_best_span(
        qualities,
        args.span_length,
        allow_hard_failures=args.allow_hard_failures,
        min_mean_motion_delta=args.min_mean_motion_delta,
        max_mean_foreground_mask_delta=args.max_mean_foreground_mask_delta,
        motion_metric=args.motion_metric,
    )
    selected_paths = []
    for output_index, source in enumerate(selection.frame_paths):
        source_path = Path(source)
        output = selected_dir / f"frame_{output_index:03d}.png"
        shutil.copy2(source_path, output)
        selected_paths.append(output)

    contact_sheet = make_contact_sheet(selected_paths, run_dir / "span_contact_sheet.png", columns=min(6, len(selected_paths)))
    preview = make_preview_gif(selected_paths, run_dir / "span_preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    report = {
        "status": "completed",
        "source_frames_dir": str(args.frames_dir),
        "settings": {
            "span_length": args.span_length,
            "fps": args.fps,
            "allow_hard_failures": args.allow_hard_failures,
            "foreground_mask_dir": str(args.foreground_mask_dir) if args.foreground_mask_dir else None,
            "min_mean_motion_delta": args.min_mean_motion_delta,
            "max_mean_foreground_mask_delta": args.max_mean_foreground_mask_delta,
            "motion_metric": args.motion_metric,
        },
        "selection": selection.to_dict(),
        "retake_recommendations": recommendation_table(qualities),
        "selected_frames_dir": str(selected_dir),
        "span_contact_sheet": str(contact_sheet),
        "span_preview_gif": str(preview),
        "frame_quality": [quality.to_dict() for quality in qualities],
    }
    report_path = run_dir / "span_selection_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(json.dumps({"selection": report["selection"], "span_preview_gif": str(preview)}, indent=2, ensure_ascii=False))


def _foreground_mask_deltas(mask_paths: list[Path]) -> list[float]:
    deltas = [0.0]
    previous = Image.open(mask_paths[0]).convert("L") if mask_paths else None
    for path in mask_paths[1:]:
        current = Image.open(path).convert("L").resize(previous.size, Image.Resampling.BICUBIC)  # type: ignore[union-attr]
        deltas.append(float(ImageStat.Stat(ImageChops.difference(previous, current)).mean[0]) / 255.0)  # type: ignore[arg-type]
        previous = current
    return deltas


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "best_span"


if __name__ == "__main__":
    main()
