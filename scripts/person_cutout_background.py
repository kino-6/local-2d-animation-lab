from __future__ import annotations

import argparse
import json
import time
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="Keep the main character component and replace outside background with white.")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_person_cutout_background"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--subject-threshold", default=92, type=int)
    parser.add_argument("--grow", default=5, type=int)
    parser.add_argument("--blur", default=1, type=int)
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_person_cutout_background")
    run_dir = args.output_root / time.strftime(f"{label}_%Y%m%d_%H%M%S")
    frames_out = run_dir / "frames"
    masks_out = run_dir / "person_masks"
    frames_out.mkdir(parents=True, exist_ok=True)
    masks_out.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []
    mask_paths: list[Path] = []
    frame_reports: list[dict[str, Any]] = []
    for index, frame_path in enumerate(frame_paths):
        output_path = frames_out / f"frame_{index:03d}.png"
        mask_path = masks_out / f"person_mask_{index:03d}.png"
        report = cutout_background_frame(
            frame_path,
            output_path,
            mask_path,
            subject_threshold=args.subject_threshold,
            grow=args.grow,
            blur=args.blur,
        )
        output_paths.append(output_path)
        mask_paths.append(mask_path)
        frame_reports.append(report)

    contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=min(6, len(output_paths)))
    mask_contact_sheet = make_contact_sheet(mask_paths, run_dir / "person_mask_contact_sheet.png", columns=min(6, len(mask_paths)))
    preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    report = {
        "status": "completed",
        "source_frames_dir": str(args.frames_dir),
        "frames_dir": str(frames_out),
        "person_masks_dir": str(masks_out),
        "contact_sheet": str(contact_sheet),
        "person_mask_contact_sheet": str(mask_contact_sheet),
        "preview_gif": str(preview),
        "settings": {
            "subject_threshold": args.subject_threshold,
            "grow": args.grow,
            "blur": args.blur,
            "fps": args.fps,
        },
        "summary": _summarize(frame_reports),
        "frame_reports": frame_reports,
    }
    report_path = run_dir / "person_cutout_background_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(json.dumps({"summary": report["summary"], "preview_gif": str(preview)}, indent=2, ensure_ascii=False))


def cutout_background_frame(
    frame_path: Path,
    output_path: Path,
    mask_path: Path,
    *,
    subject_threshold: int,
    grow: int,
    blur: int,
) -> dict[str, Any]:
    image = Image.open(frame_path).convert("RGB")
    bg = _estimate_background(image)
    subject = _subject_candidate_mask(image, bg, subject_threshold)
    person = _largest_component_mask(subject)
    person = _grow_mask(person, grow)
    hard_person = person
    if blur > 0:
        person = person.filter(ImageFilter.GaussianBlur(blur))
    white = Image.new("RGB", image.size, (255, 255, 255))
    output = Image.composite(image, white, person)
    output.save(output_path)
    hard_person.save(mask_path)
    coverage = _mask_coverage(hard_person)
    return {
        "index": _frame_index(frame_path),
        "source": str(frame_path),
        "output": str(output_path),
        "person_mask": str(mask_path),
        "estimated_background": bg,
        "person_coverage": round(coverage, 5),
        "background_replaced_coverage": round(1.0 - coverage, 5),
    }


def _subject_candidate_mask(image: Image.Image, bg: tuple[int, int, int], threshold: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    pixels = image.load()
    out = mask.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            channel_range = max(red, green, blue) - min(red, green, blue)
            dark_subject = red + green + blue < 430
            saturated_subject = channel_range > 60
            distance_subject = _color_distance((red, green, blue), bg) > threshold
            if dark_subject or saturated_subject or distance_subject:
                out[x, y] = 255
    return mask


def _largest_component_mask(mask: Image.Image) -> Image.Image:
    components = _connected_components(mask, min_pixels=48)
    out = Image.new("L", mask.size, 0)
    if not components:
        return out
    pixels = out.load()
    for x, y in components[0]["points"]:
        pixels[x, y] = 255
    return out


def _connected_components(mask: Image.Image, min_pixels: int) -> list[dict[str, Any]]:
    width, height = mask.size
    pixels = mask.load()
    visited: set[tuple[int, int]] = set()
    components: list[dict[str, Any]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in visited:
                continue
            points: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited.add((x, y))
            while queue:
                px, py = queue.popleft()
                points.append((px, py))
                for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    if pixels[nx, ny] == 0 or (nx, ny) in visited:
                        continue
                    visited.add((nx, ny))
                    queue.append((nx, ny))
            if len(points) >= min_pixels:
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                components.append(
                    {
                        "points": points,
                        "pixels": len(points),
                        "bbox": (min(xs), min(ys), max(xs) + 1, max(ys) + 1),
                    }
                )
    return sorted(components, key=lambda item: int(item["pixels"]), reverse=True)


def _grow_mask(mask: Image.Image, pixels: int) -> Image.Image:
    if pixels <= 0:
        return mask.copy()
    return mask.filter(ImageFilter.MaxFilter(pixels * 2 + 1))


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    points = [
        (0, 0),
        (image.width - 1, 0),
        (0, image.height - 1),
        (image.width - 1, image.height - 1),
        (image.width // 2, 0),
        (image.width // 2, image.height - 1),
    ]
    pixels = image.load()
    samples = [pixels[x, y] for x, y in points]
    return tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1]) + abs(left[2] - right[2])


def _mask_coverage(mask: Image.Image) -> float:
    pixels = mask.load()
    active = 0
    for y in range(mask.height):
        for x in range(mask.width):
            if pixels[x, y] > 0:
                active += 1
    return active / (mask.width * mask.height)


def _summarize(frame_reports: list[dict[str, Any]]) -> dict[str, Any]:
    mean_person = sum(float(report["person_coverage"]) for report in frame_reports) / len(frame_reports)
    return {"mean_person_coverage": round(mean_person, 5), "frames": len(frame_reports)}


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "person_cutout_background"


if __name__ == "__main__":
    main()
