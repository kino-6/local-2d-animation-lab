from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply deterministic white-background cleanup using precomputed artifact masks."
    )
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--masks-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--mask-threshold", default=128, type=int)
    parser.add_argument("--mask-erode", default=0, type=int)
    parser.add_argument("--max-coverage", default=0.65, type=float)
    parser.add_argument("--correction-plan", default=None, type=Path)
    parser.add_argument("--only-plan-action", default=None)
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    mask_by_index = {_frame_index(path): path for path in args.masks_dir.glob("*.png")}
    plan_actions = _plan_action_by_index(args.correction_plan)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")
    indexed_frames = _select_indexed_frames(frame_paths, plan_actions, args.only_plan_action)
    missing_masks = [index for index, _ in indexed_frames if index not in mask_by_index]
    if missing_masks:
        raise ValueError(f"Missing masks for frame indices: {missing_masks[:8]}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_mask_cleanup")
    run_dir = build_timestamped_run_dir(args.output_root, "mask_cleanup", label)
    write_run_profile(run_dir, category="mask_cleanup", label=label, args=args)
    frames_out = run_dir / "frames"
    frames_out.mkdir(parents=True, exist_ok=True)

    frame_reports: list[dict[str, Any]] = []
    output_paths: list[Path] = []
    for index, frame_path in indexed_frames:
        mask_path = mask_by_index[index]
        output_path = frames_out / f"frame_{index:03d}.png"
        report = _cleanup_frame(
            frame_path,
            mask_path,
            output_path,
            threshold=args.mask_threshold,
            erode=args.mask_erode,
            max_coverage=args.max_coverage,
        )
        output_paths.append(output_path)
        frame_reports.append(report)

    contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=min(6, len(output_paths)))
    preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    report = {
        "status": "completed",
        "source_frames_dir": str(args.frames_dir),
        "masks_dir": str(args.masks_dir),
        "frames_dir": str(frames_out),
        "contact_sheet": str(contact_sheet),
        "preview_gif": str(preview),
        "settings": {
            "mask_threshold": args.mask_threshold,
            "mask_erode": args.mask_erode,
            "max_coverage": args.max_coverage,
            "fps": args.fps,
            "correction_plan": str(args.correction_plan) if args.correction_plan else None,
            "only_plan_action": args.only_plan_action,
        },
        "summary": _summarize(frame_reports),
        "frame_reports": frame_reports,
    }
    report_path = run_dir / "mask_cleanup_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(json.dumps({"summary": report["summary"], "preview_gif": str(preview)}, indent=2, ensure_ascii=False))


def _cleanup_frame(
    frame_path: Path,
    mask_path: Path,
    output_path: Path,
    *,
    threshold: int,
    erode: int,
    max_coverage: float,
) -> dict[str, Any]:
    frame = _flatten_on_white(Image.open(frame_path))
    mask = Image.open(mask_path).convert("L").resize(frame.size, Image.Resampling.NEAREST)
    binary = mask.point(lambda value: 255 if value >= threshold else 0)
    for _ in range(max(0, erode)):
        binary = binary.filter(ImageFilter.MinFilter(3))
    coverage = _mask_coverage(binary)
    if coverage > max_coverage:
        shutil.copy2(frame_path, output_path)
        mode = "copied_mask_too_large"
    elif coverage == 0.0:
        shutil.copy2(frame_path, output_path)
        mode = "copied_empty_mask"
    else:
        white = Image.new("RGB", frame.size, (255, 255, 255))
        cleaned = Image.composite(white, frame, binary)
        cleaned.save(output_path)
        mode = "white_mask_cleanup"
    return {
        "index": _frame_index(frame_path),
        "source": str(frame_path),
        "mask": str(mask_path),
        "output": str(output_path),
        "mask_coverage": round(coverage, 5),
        "mode": mode,
    }


def _flatten_on_white(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    background.alpha_composite(rgba)
    return background.convert("RGB")


def _summarize(frame_reports: list[dict[str, Any]]) -> dict[str, Any]:
    modes: dict[str, int] = {}
    for report in frame_reports:
        modes[report["mode"]] = modes.get(report["mode"], 0) + 1
    mean_coverage = sum(float(report["mask_coverage"]) for report in frame_reports) / len(frame_reports)
    return {"modes": modes, "mean_mask_coverage": round(mean_coverage, 5)}


def _plan_action_by_index(path: Path | None) -> dict[int, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    actions: dict[int, str] = {}
    for item in payload.get("frame_plans", []):
        if "index" in item:
            actions[int(item["index"])] = str(item.get("action", ""))
    return actions


def _select_indexed_frames(
    frame_paths: list[Path],
    plan_actions: dict[int, str],
    only_plan_action: str | None,
) -> list[tuple[int, Path]]:
    indexed = [(_frame_index(path), path) for path in frame_paths]
    if not only_plan_action:
        return indexed
    return [(index, path) for index, path in indexed if plan_actions.get(index) == only_plan_action]


def _mask_coverage(mask: Image.Image) -> float:
    pixels = mask.load()
    active = 0
    for y in range(mask.height):
        for x in range(mask.width):
            if pixels[x, y] > 0:
                active += 1
    return active / (mask.width * mask.height)


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "mask_cleanup"


if __name__ == "__main__":
    main()
