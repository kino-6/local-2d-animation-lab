from __future__ import annotations

from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from PIL import Image, ImageStat


def evaluate_animation(frame_paths: list[Path]) -> dict[str, Any]:
    """Local heuristic evaluation for generated animation runs."""
    frame_reports = [_evaluate_frame(path) for path in frame_paths]
    if not frame_reports:
        return {"score": 0.0, "issues": ["no frames"], "frames": []}

    areas = [report["foreground_area_ratio"] for report in frame_reports]
    widths = [report["bbox_width_ratio"] for report in frame_reports]
    heights = [report["bbox_height_ratio"] for report in frame_reports]
    centers = [report["center_x_ratio"] for report in frame_reports]
    color_distances = [
        _color_distance(frame_reports[index]["mean_rgb"], frame_reports[index - 1]["mean_rgb"])
        for index in range(1, len(frame_reports))
    ]
    pose_deltas = [
        abs(frame_reports[index]["center_x_ratio"] - frame_reports[index - 1]["center_x_ratio"])
        + abs(frame_reports[index]["bbox_height_ratio"] - frame_reports[index - 1]["bbox_height_ratio"])
        for index in range(1, len(frame_reports))
    ]

    issues: list[str] = []
    if max(report["component_count"] for report in frame_reports) > 2:
        issues.append("possible multi-character or fragmented foreground")
    if pstdev(centers) > 0.16:
        issues.append("character center drifts too much between frames")
    if pstdev(heights) > 0.12:
        issues.append("character scale changes too much between frames")
    if mean(color_distances or [0.0]) > 60:
        issues.append("character colors are inconsistent between frames")
    if max(areas) < 0.08:
        issues.append("foreground character is too small")
    if max(pose_deltas or [0.0]) < 0.04:
        issues.append("motion variation is weak")

    score = 1.0
    score -= min(0.35, pstdev(centers) * 1.2)
    score -= min(0.30, pstdev(heights) * 1.2)
    score -= min(0.25, mean(color_distances or [0.0]) / 260)
    score -= 0.08 * sum(max(0, report["component_count"] - 1) for report in frame_reports) / len(frame_reports)
    score += min(0.12, max(pose_deltas or [0.0]))
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 3),
        "issues": issues,
        "summary": {
            "mean_foreground_area_ratio": round(mean(areas), 3),
            "center_x_stdev": round(pstdev(centers), 3),
            "height_stdev": round(pstdev(heights), 3),
            "mean_color_distance": round(mean(color_distances or [0.0]), 3),
            "max_pose_delta": round(max(pose_deltas or [0.0]), 3),
        },
        "frames": frame_reports,
    }


def _evaluate_frame(path: Path) -> dict[str, Any]:
    image = Image.open(path).convert("RGBA")
    mask = _foreground_mask(image)
    bbox = mask.getbbox()
    if not bbox:
        return {
            "path": str(path),
            "foreground_area_ratio": 0.0,
            "bbox_width_ratio": 0.0,
            "bbox_height_ratio": 0.0,
            "center_x_ratio": 0.5,
            "mean_rgb": [0, 0, 0],
            "component_count": 0,
        }

    left, top, right, bottom = bbox
    width, height = image.size
    foreground = image.crop(bbox)
    foreground_mask = mask.crop(bbox)
    stat = ImageStat.Stat(foreground.convert("RGB"), foreground_mask)
    area = sum(mask.histogram()[1:])
    return {
        "path": str(path),
        "foreground_area_ratio": round(area / (width * height), 4),
        "bbox_width_ratio": round((right - left) / width, 4),
        "bbox_height_ratio": round((bottom - top) / height, 4),
        "center_x_ratio": round(((left + right) / 2) / width, 4),
        "mean_rgb": [round(value) for value in stat.mean],
        "component_count": _component_count(mask, min_pixels=max(80, int(width * height * 0.002))),
    }


def _foreground_mask(image: Image.Image) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    samples = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
    ]
    background = tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))
    mask = Image.new("L", image.size, 0)
    mask_pixels = mask.load()
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            if alpha > 10 and distance > 58:
                mask_pixels[x, y] = 255
    return mask


def _component_count(mask: Image.Image, min_pixels: int) -> int:
    width, height = mask.size
    pixels = mask.load()
    seen: set[tuple[int, int]] = set()
    count = 0
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if pixels[x, y] == 0 or (x, y) in seen:
                continue
            size = _flood(mask, x, y, seen)
            if size >= min_pixels:
                count += 1
    return count


def _flood(mask: Image.Image, start_x: int, start_y: int, seen: set[tuple[int, int]]) -> int:
    width, height = mask.size
    pixels = mask.load()
    stack = [(start_x, start_y)]
    size = 0
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height or (x, y) in seen or pixels[x, y] == 0:
            continue
        seen.add((x, y))
        size += 4
        stack.extend([(x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2)])
    return size


def _color_distance(left: list[int], right: list[int]) -> float:
    return sum(abs(left[index] - right[index]) for index in range(3)) / 3
