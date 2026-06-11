from __future__ import annotations

import argparse
import json
import time
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize border-connected background pixels to white.")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_background_normalize"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--distance-threshold", default=70, type=int)
    parser.add_argument("--protect-threshold", default=110, type=int)
    parser.add_argument("--protect-grow", default=5, type=int)
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_background_normalize")
    run_dir = args.output_root / time.strftime(f"{label}_%Y%m%d_%H%M%S")
    frames_out = run_dir / "frames"
    masks_out = run_dir / "background_masks"
    frames_out.mkdir(parents=True, exist_ok=True)
    masks_out.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []
    mask_paths: list[Path] = []
    frame_reports: list[dict[str, Any]] = []
    for index, frame_path in enumerate(frame_paths):
        output_path = frames_out / f"frame_{index:03d}.png"
        mask_path = masks_out / f"background_mask_{index:03d}.png"
        report = normalize_frame_background(
            frame_path,
            output_path,
            mask_path,
            distance_threshold=args.distance_threshold,
            protect_threshold=args.protect_threshold,
            protect_grow=args.protect_grow,
        )
        output_paths.append(output_path)
        mask_paths.append(mask_path)
        frame_reports.append(report)

    contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=min(6, len(output_paths)))
    mask_contact_sheet = make_contact_sheet(mask_paths, run_dir / "background_mask_contact_sheet.png", columns=min(6, len(mask_paths)))
    preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    report = {
        "status": "completed",
        "source_frames_dir": str(args.frames_dir),
        "frames_dir": str(frames_out),
        "background_masks_dir": str(masks_out),
        "contact_sheet": str(contact_sheet),
        "background_mask_contact_sheet": str(mask_contact_sheet),
        "preview_gif": str(preview),
        "settings": {
            "distance_threshold": args.distance_threshold,
            "protect_threshold": args.protect_threshold,
            "protect_grow": args.protect_grow,
            "fps": args.fps,
        },
        "summary": _summarize(frame_reports),
        "frame_reports": frame_reports,
    }
    report_path = run_dir / "background_normalize_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(json.dumps({"summary": report["summary"], "preview_gif": str(preview)}, indent=2, ensure_ascii=False))


def normalize_frame_background(
    frame_path: Path,
    output_path: Path,
    mask_path: Path,
    *,
    distance_threshold: int,
    protect_threshold: int,
    protect_grow: int,
) -> dict[str, Any]:
    image = Image.open(frame_path).convert("RGB")
    bg = _estimate_background(image)
    protect = _protect_mask(image, bg, protect_threshold)
    protect = _grow_mask(protect, protect_grow)
    background_mask = _border_connected_background(image, bg, distance_threshold, protect)
    output = image.copy()
    output_pixels = output.load()
    mask_pixels = background_mask.load()
    changed = 0
    for y in range(image.height):
        for x in range(image.width):
            if mask_pixels[x, y] > 0:
                output_pixels[x, y] = (255, 255, 255)
                changed += 1
    output.save(output_path)
    background_mask.save(mask_path)
    return {
        "index": _frame_index(frame_path),
        "source": str(frame_path),
        "output": str(output_path),
        "background_mask": str(mask_path),
        "estimated_background": bg,
        "changed_coverage": round(changed / (image.width * image.height), 5),
    }


def _border_connected_background(
    image: Image.Image,
    bg: tuple[int, int, int],
    threshold: int,
    protect: Image.Image,
) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    protect_pixels = protect.load()
    mask = Image.new("L", image.size, 0)
    mask_pixels = mask.load()
    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        if protect_pixels[x, y] > 0 or _color_distance(pixels[x, y], bg) > threshold:
            continue
        mask_pixels[x, y] = 255
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                queue.append((nx, ny))
    return mask


def _protect_mask(image: Image.Image, bg: tuple[int, int, int], threshold: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    pixels = image.load()
    out = mask.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            channel_range = max(red, green, blue) - min(red, green, blue)
            if _color_distance((red, green, blue), bg) > threshold or channel_range > 55 or red + green + blue < 430:
                out[x, y] = 255
    return mask


def _grow_mask(mask: Image.Image, pixels: int) -> Image.Image:
    if pixels <= 0:
        return mask.copy()
    from PIL import ImageFilter

    return mask.filter(ImageFilter.MaxFilter(pixels * 2 + 1))


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    samples = []
    pixels = image.load()
    margin_x = max(1, image.width // 8)
    margin_y = max(1, image.height // 8)
    for y in list(range(margin_y)) + list(range(image.height - margin_y, image.height)):
        for x in range(image.width):
            samples.append(pixels[x, y])
    for x in list(range(margin_x)) + list(range(image.width - margin_x, image.width)):
        for y in range(image.height):
            samples.append(pixels[x, y])
    return tuple(round(sum(sample[channel] for sample in samples) / len(samples)) for channel in range(3))


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1]) + abs(left[2] - right[2])


def _summarize(frame_reports: list[dict[str, Any]]) -> dict[str, Any]:
    mean_changed = sum(float(report["changed_coverage"]) for report in frame_reports) / len(frame_reports)
    return {"mean_changed_coverage": round(mean_changed, 5), "frames": len(frame_reports)}


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "background_normalize"


if __name__ == "__main__":
    main()
