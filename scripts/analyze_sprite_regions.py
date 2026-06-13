from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw

from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


REGION_COLORS = {
    "lower_body": (70, 160, 255, 105),
    "feet_contact": (255, 120, 60, 120),
    "cloak_or_hair_trail": (180, 80, 255, 105),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze bbox-relative local sprite artifact regions.")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--columns", default=11, type=int)
    parser.add_argument("--alpha-threshold", default=24, type=int)
    parser.add_argument("--pale-threshold", default=0.018, type=float)
    parser.add_argument("--contact-threshold", default=0.012, type=float)
    parser.add_argument("--temporal-delta-threshold", default=0.115, type=float)
    parser.add_argument("--trail-threshold", default=0.018, type=float)
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_regions")
    run_dir = build_timestamped_run_dir(args.output_root, "region_diagnostics", label)
    write_run_profile(
        run_dir,
        category="region_diagnostics",
        label=label,
        args=args,
        memo="Deterministic region diagnostics for sprite animation artifacts and local correction planning.",
    )
    masks_dir = run_dir / "region_masks"
    artifact_masks_dir = run_dir / "artifact_masks"
    overlays_dir = run_dir / "overlays"
    masks_dir.mkdir(parents=True, exist_ok=True)
    artifact_masks_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, Any]] = []
    overlay_paths: list[Path] = []
    artifact_mask_paths: list[Path] = []
    region_mask_paths: dict[str, list[Path]] = {name: [] for name in REGION_COLORS}
    previous_masks: dict[str, Image.Image] = {}
    for index, frame_path in enumerate(frame_paths):
        image = Image.open(frame_path).convert("RGBA")
        foreground = _foreground_mask(image, args.alpha_threshold)
        bbox = foreground.getbbox()
        regions = _region_boxes(bbox, image.size) if bbox else {}
        frame_report: dict[str, Any] = {
            "index": index,
            "source": str(frame_path),
            "foreground_bbox": list(bbox) if bbox else None,
            "regions": {},
            "issue_labels": [],
            "decision": "postprocess_only",
        }
        overlay = image.copy()
        artifact_mask = Image.new("L", image.size, 0)
        for region_name, box in regions.items():
            region_mask = _box_mask(image.size, box)
            mask_path = masks_dir / region_name / f"frame_{index:03d}.png"
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            region_mask.save(mask_path)
            region_mask_paths[region_name].append(mask_path)
            metrics = _region_metrics(
                image,
                foreground,
                region_mask,
                previous_masks.get(region_name),
                region_name,
            )
            frame_report["regions"][region_name] = {"box": list(box), **metrics}
            previous_masks[region_name] = ImageChops.multiply(foreground, region_mask)
            active = ImageChops.multiply(foreground, region_mask)
            artifact_mask = ImageChops.lighter(
                artifact_mask,
                _artifact_mask_for_region(image, active, region_mask, region_name),
            )
            _draw_overlay(overlay, box, REGION_COLORS[region_name])
        frame_report["issue_labels"] = _issue_labels(frame_report["regions"], args)
        frame_report["decision"] = _frame_decision(frame_report["issue_labels"], frame_report["regions"])
        artifact_mask_path = artifact_masks_dir / f"frame_{index:03d}.png"
        artifact_mask.save(artifact_mask_path)
        frame_report["artifact_mask"] = str(artifact_mask_path)
        artifact_mask_paths.append(artifact_mask_path)
        reports.append(frame_report)

        overlay_path = overlays_dir / f"frame_{index:03d}.png"
        overlay.save(overlay_path)
        overlay_paths.append(overlay_path)

    overlay_contact = make_contact_sheet(overlay_paths, run_dir / "region_overlay_contact_sheet.png", columns=args.columns)
    mask_contacts = {}
    for region_name, paths in region_mask_paths.items():
        if paths:
            mask_contacts[region_name] = str(
                make_contact_sheet(paths, run_dir / f"{region_name}_mask_contact_sheet.png", columns=args.columns)
            )
    artifact_mask_contact = make_contact_sheet(
        artifact_mask_paths,
        run_dir / "artifact_mask_contact_sheet.png",
        columns=args.columns,
    )

    report = {
        "status": "completed",
        "source_frames_dir": str(args.frames_dir),
        "frame_count": len(frame_paths),
        "overlay_contact_sheet": str(overlay_contact),
        "artifact_mask_contact_sheet": str(artifact_mask_contact),
        "mask_contact_sheets": mask_contacts,
        "settings": {
            "alpha_threshold": args.alpha_threshold,
            "pale_threshold": args.pale_threshold,
            "contact_threshold": args.contact_threshold,
            "temporal_delta_threshold": args.temporal_delta_threshold,
            "trail_threshold": args.trail_threshold,
        },
        "summary": _summarize(reports),
        "frame_reports": reports,
    }
    report_path = run_dir / "region_diagnostics_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "report": str(report_path), **report}, indent=2, ensure_ascii=False))


def _foreground_mask(image: Image.Image, alpha_threshold: int) -> Image.Image:
    alpha = image.getchannel("A")
    alpha_bbox = alpha.point(lambda value: 255 if value >= alpha_threshold else 0).getbbox()
    full_bbox = (0, 0, image.width, image.height)
    if alpha_bbox is not None and alpha_bbox != full_bbox and max(alpha.getextrema()) > alpha_threshold:
        return alpha.point(lambda value: 255 if value >= alpha_threshold else 0)
    rgb = image.convert("RGB")
    bg = _estimate_background(rgb)
    out = Image.new("L", image.size, 0)
    pixels = rgb.load()
    mask = out.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            if abs(red - bg[0]) + abs(green - bg[1]) + abs(blue - bg[2]) > 88:
                mask[x, y] = 255
    return out


def _region_boxes(bbox: tuple[int, int, int, int], size: tuple[int, int]) -> dict[str, tuple[int, int, int, int]]:
    left, top, right, bottom = bbox
    width, height = right - left, bottom - top
    canvas_w, canvas_h = size
    lower_top = top + round(height * 0.54)
    feet_top = top + round(height * 0.76)
    side_pad = round(width * 0.22)
    trail_left = max(0, left - round(width * 0.34))
    trail_right = min(canvas_w, right + round(width * 0.34))
    return {
        "lower_body": (
            max(0, left - round(width * 0.12)),
            max(0, lower_top),
            min(canvas_w, right + round(width * 0.12)),
            min(canvas_h, bottom),
        ),
        "feet_contact": (
            max(0, left - side_pad),
            max(0, feet_top),
            min(canvas_w, right + side_pad),
            min(canvas_h, bottom + round(height * 0.08)),
        ),
        "cloak_or_hair_trail": (
            trail_left,
            max(0, top + round(height * 0.18)),
            trail_right,
            min(canvas_h, top + round(height * 0.74)),
        ),
    }


def _region_metrics(
    image: Image.Image,
    foreground: Image.Image,
    region_mask: Image.Image,
    previous_region_foreground: Image.Image | None,
    region_name: str,
) -> dict[str, float]:
    active = ImageChops.multiply(foreground, region_mask)
    region_area = max(1, _mask_pixels(region_mask))
    active_pixels = _mask_pixels(active)
    temporal_delta = 0.0
    if previous_region_foreground is not None:
        temporal_delta = _mask_pixels(ImageChops.difference(active, previous_region_foreground)) / region_area
    return {
        "coverage": round(active_pixels / region_area, 5),
        "temporal_delta": round(temporal_delta, 5),
        "pale_afterimage_coverage": round(_pale_afterimage_coverage(image, active, region_mask), 5),
        "contact_shadow_coverage": round(_contact_shadow_coverage(image, active, region_mask), 5),
        "trail_coverage": round(_trail_coverage(image, active, region_mask, region_name), 5),
    }


def _pale_afterimage_coverage(image: Image.Image, active: Image.Image, region_mask: Image.Image) -> float:
    rgb = image.convert("RGB")
    pixels = rgb.load()
    active_pixels = active.load()
    region_pixels = region_mask.load()
    count = 0
    total = 0
    for y in range(image.height):
        for x in range(image.width):
            if region_pixels[x, y] == 0:
                continue
            total += 1
            red, green, blue = pixels[x, y]
            high = max(red, green, blue)
            low = min(red, green, blue)
            saturation = high - low
            brightness = (red + green + blue) / 3
            white_distance = abs(red - 255) + abs(green - 255) + abs(blue - 255)
            pale = 35 < white_distance < 320 and 85 < brightness < 242 and saturation < 62
            if active_pixels[x, y] > 0 and pale:
                count += 1
    return count / max(1, total)


def _contact_shadow_coverage(image: Image.Image, active: Image.Image, region_mask: Image.Image) -> float:
    rgb = image.convert("RGB")
    pixels = rgb.load()
    active_pixels = active.load()
    region_pixels = region_mask.load()
    count = 0
    total = 0
    for y in range(image.height):
        for x in range(image.width):
            if region_pixels[x, y] == 0:
                continue
            total += 1
            red, green, blue = pixels[x, y]
            high = max(red, green, blue)
            low = min(red, green, blue)
            brightness = (red + green + blue) / 3
            gray_smear = 55 < brightness < 236 and high - low < 55
            if active_pixels[x, y] > 0 and gray_smear:
                count += 1
    return count / max(1, total)


def _trail_coverage(image: Image.Image, active: Image.Image, region_mask: Image.Image, region_name: str) -> float:
    if region_name != "cloak_or_hair_trail":
        return 0.0
    alpha = image.getchannel("A")
    alpha_pixels = alpha.load()
    active_pixels = active.load()
    region_pixels = region_mask.load()
    count = 0
    total = 0
    for y in range(image.height):
        for x in range(image.width):
            if region_pixels[x, y] == 0:
                continue
            total += 1
            if active_pixels[x, y] > 0 and alpha_pixels[x, y] < 210:
                count += 1
    return count / max(1, total)


def _artifact_mask_for_region(
    image: Image.Image,
    active: Image.Image,
    region_mask: Image.Image,
    region_name: str,
) -> Image.Image:
    rgb = image.convert("RGB")
    alpha = image.getchannel("A")
    pixels = rgb.load()
    alpha_pixels = alpha.load()
    active_pixels = active.load()
    region_pixels = region_mask.load()
    out = Image.new("L", image.size, 0)
    out_pixels = out.load()
    for y in range(image.height):
        for x in range(image.width):
            if region_pixels[x, y] == 0 or active_pixels[x, y] == 0:
                continue
            red, green, blue = pixels[x, y]
            high = max(red, green, blue)
            low = min(red, green, blue)
            saturation = high - low
            brightness = (red + green + blue) / 3
            white_distance = abs(red - 255) + abs(green - 255) + abs(blue - 255)
            pale = 35 < white_distance < 320 and 85 < brightness < 242 and saturation < 62
            gray_smear = 55 < brightness < 236 and saturation < 55
            translucent_trail = region_name == "cloak_or_hair_trail" and alpha_pixels[x, y] < 210
            if (region_name == "lower_body" and pale) or (region_name == "feet_contact" and gray_smear) or translucent_trail:
                out_pixels[x, y] = 255
    return out


def _issue_labels(regions: dict[str, dict[str, Any]], args: argparse.Namespace) -> list[str]:
    labels: list[str] = []
    if not regions:
        return ["foreground_missing_or_unreadable_sprite"]
    lower = regions.get("lower_body", {})
    feet = regions.get("feet_contact", {})
    trail = regions.get("cloak_or_hair_trail", {})
    if float(lower.get("pale_afterimage_coverage", 0.0)) >= args.pale_threshold:
        labels.append("lower_body_pale_afterimage_review")
    if float(feet.get("contact_shadow_coverage", 0.0)) >= args.contact_threshold:
        labels.append("foot_shadow_or_contact_artifact_review")
    if max(float(region.get("temporal_delta", 0.0)) for region in regions.values()) >= args.temporal_delta_threshold:
        labels.append("silhouette_redraw_jitter_review")
    if float(trail.get("trail_coverage", 0.0)) >= args.trail_threshold:
        labels.append("cloak_or_hair_trail_review")
    return labels


def _frame_decision(labels: list[str], regions: dict[str, dict[str, Any]]) -> str:
    if "foreground_missing_or_unreadable_sprite" in labels:
        return "retake_required"
    if "silhouette_redraw_jitter_review" in labels and (
        "lower_body_pale_afterimage_review" in labels or "foot_shadow_or_contact_artifact_review" in labels
    ):
        return "retake_required"
    max_region = max((float(region.get("coverage", 0.0)) for region in regions.values()), default=0.0)
    if max_region > 0.78:
        return "retake_required"
    if labels:
        return "local_inpaint_candidate"
    return "postprocess_only"


def _summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    labels: dict[str, int] = {}
    decisions: dict[str, int] = {}
    region_temporal: dict[str, list[float]] = {}
    for report in reports:
        decisions[report["decision"]] = decisions.get(report["decision"], 0) + 1
        for label in report["issue_labels"]:
            labels[label] = labels.get(label, 0) + 1
        for region_name, metrics in report["regions"].items():
            region_temporal.setdefault(region_name, []).append(float(metrics["temporal_delta"]))
    return {
        "frame_count": len(reports),
        "issue_label_counts": labels,
        "decision_counts": decisions,
        "mean_temporal_delta": {
            name: round(statistics.mean(values), 5) if values else 0.0
            for name, values in region_temporal.items()
        },
    }


def _draw_overlay(image: Image.Image, box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(box, outline=color[:3] + (230,), width=3, fill=color)
    image.alpha_composite(overlay)


def _box_mask(size: tuple[int, int], box: tuple[int, int, int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    return mask


def _mask_pixels(mask: Image.Image) -> int:
    histogram = mask.histogram()
    return sum(histogram[1:])


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    pixels = image.load()
    samples = [
        pixels[0, 0],
        pixels[image.width - 1, 0],
        pixels[0, image.height - 1],
        pixels[image.width - 1, image.height - 1],
    ]
    return tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "region_diagnostics"


if __name__ == "__main__":
    main()
