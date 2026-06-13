from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageEnhance, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stabilize transparent sprite frames and normalize foreground brightness/saturation."
    )
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--fps", default=12, type=int)
    parser.add_argument("--columns", default=11, type=int)
    parser.add_argument("--alpha-threshold", default=24, type=int)
    parser.add_argument("--anchor", choices=("bottom_center", "center"), default="bottom_center")
    parser.add_argument("--max-shift", default=48, type=int)
    parser.add_argument("--brightness-strength", default=0.72, type=float)
    parser.add_argument("--saturation-strength", default=0.72, type=float)
    parser.add_argument("--min-factor", default=0.72, type=float)
    parser.add_argument("--max-factor", default=1.34, type=float)
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_stabilized")
    run_dir = build_timestamped_run_dir(args.output_root, "sprite_postprocess", label)
    write_run_profile(
        run_dir,
        category="sprite_postprocess",
        label=label,
        args=args,
        memo="Postprocess run for anchor stabilization and brightness/saturation normalization.",
    )
    frames_out = run_dir / "frames"
    frames_out.mkdir(parents=True, exist_ok=True)

    source_frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    source_metrics = [_frame_metrics(image, args.alpha_threshold) for image in source_frames]
    target_anchor = _median_anchor(source_metrics, args.anchor)
    target_luma = statistics.median(metric["foreground_luma"] for metric in source_metrics if metric["has_foreground"])
    target_sat = statistics.median(metric["foreground_saturation"] for metric in source_metrics if metric["has_foreground"])

    output_paths: list[Path] = []
    frame_reports: list[dict[str, Any]] = []
    for index, (path, image, metrics) in enumerate(zip(frame_paths, source_frames, source_metrics)):
        corrected, correction = _correct_frame(
            image,
            metrics,
            target_anchor=target_anchor,
            target_luma=target_luma,
            target_sat=target_sat,
            anchor=args.anchor,
            max_shift=args.max_shift,
            brightness_strength=args.brightness_strength,
            saturation_strength=args.saturation_strength,
            min_factor=args.min_factor,
            max_factor=args.max_factor,
        )
        out = frames_out / f"frame_{index:03d}.png"
        corrected.save(out)
        output_paths.append(out)
        frame_reports.append(
            {
                "index": index,
                "source": str(path),
                "output": str(out),
                "before": metrics,
                "after": _frame_metrics(corrected, args.alpha_threshold),
                "correction": correction,
            }
        )

    contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=args.columns)
    spritesheet = make_sprite_sheet(output_paths, run_dir / "spritesheet.png", columns=args.columns)
    preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    before_summary = _summarize([report["before"] for report in frame_reports], args.anchor)
    after_summary = _summarize([report["after"] for report in frame_reports], args.anchor)
    report = {
        "status": "completed",
        "source_frames_dir": str(args.frames_dir),
        "frames_dir": str(frames_out),
        "contact_sheet": str(contact_sheet),
        "spritesheet": str(spritesheet),
        "preview_gif": str(preview),
        "settings": {
            "fps": args.fps,
            "alpha_threshold": args.alpha_threshold,
            "anchor": args.anchor,
            "max_shift": args.max_shift,
            "brightness_strength": args.brightness_strength,
            "saturation_strength": args.saturation_strength,
            "min_factor": args.min_factor,
            "max_factor": args.max_factor,
        },
        "target": {
            "anchor": list(target_anchor),
            "foreground_luma": round(target_luma, 5),
            "foreground_saturation": round(target_sat, 5),
        },
        "before_summary": before_summary,
        "after_summary": after_summary,
        "frame_reports": frame_reports,
    }
    report_path = run_dir / "stabilize_sprite_sequence_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "frames": str(frames_out),
                "preview_gif": str(preview),
                "contact_sheet": str(contact_sheet),
                "spritesheet": str(spritesheet),
                "before_summary": before_summary,
                "after_summary": after_summary,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _correct_frame(
    image: Image.Image,
    metrics: dict[str, Any],
    *,
    target_anchor: tuple[float, float],
    target_luma: float,
    target_sat: float,
    anchor: str,
    max_shift: int,
    brightness_strength: float,
    saturation_strength: float,
    min_factor: float,
    max_factor: float,
) -> tuple[Image.Image, dict[str, Any]]:
    if not metrics["has_foreground"]:
        return image.copy(), {"shift": [0, 0], "brightness_factor": 1.0, "saturation_factor": 1.0}

    current_anchor = _anchor(metrics, anchor)
    dx = _clamp(round(target_anchor[0] - current_anchor[0]), -max_shift, max_shift)
    dy = _clamp(round(target_anchor[1] - current_anchor[1]), -max_shift, max_shift)
    shifted = ImageChops.offset(image, dx, dy)
    shifted = _clear_wrapped_edges(shifted, dx, dy)

    luma = max(1e-6, float(metrics["foreground_luma"]))
    sat = max(1e-6, float(metrics["foreground_saturation"]))
    brightness_factor = _lerp(1.0, target_luma / luma, brightness_strength)
    saturation_factor = _lerp(1.0, target_sat / sat, saturation_strength)
    brightness_factor = _clamp_float(brightness_factor, min_factor, max_factor)
    saturation_factor = _clamp_float(saturation_factor, min_factor, max_factor)
    corrected = _adjust_rgba(shifted, brightness_factor, saturation_factor)
    return corrected, {
        "shift": [dx, dy],
        "brightness_factor": round(brightness_factor, 5),
        "saturation_factor": round(saturation_factor, 5),
    }


def _adjust_rgba(image: Image.Image, brightness_factor: float, saturation_factor: float) -> Image.Image:
    alpha = image.getchannel("A")
    rgb = image.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(brightness_factor)
    rgb = ImageEnhance.Color(rgb).enhance(saturation_factor)
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def _frame_metrics(image: Image.Image, alpha_threshold: int) -> dict[str, Any]:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    mask = alpha.point(lambda value: 255 if value >= alpha_threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return {
            "has_foreground": False,
            "bbox": None,
            "anchor_bottom_center": None,
            "anchor_center": None,
            "foreground_luma": 0.0,
            "foreground_saturation": 0.0,
        }
    left, top, right, bottom = bbox
    rgb = rgba.convert("RGB")
    stat = ImageStat.Stat(rgb, mask)
    mean = stat.mean
    luma = 0.2126 * mean[0] + 0.7152 * mean[1] + 0.0722 * mean[2]
    saturation = _mean_saturation(rgb, mask, bbox)
    return {
        "has_foreground": True,
        "bbox": [left, top, right, bottom],
        "anchor_bottom_center": [round((left + right) / 2, 5), float(bottom)],
        "anchor_center": [round((left + right) / 2, 5), round((top + bottom) / 2, 5)],
        "foreground_luma": round(luma, 5),
        "foreground_saturation": round(saturation, 5),
    }


def _mean_saturation(rgb: Image.Image, mask: Image.Image, bbox: tuple[int, int, int, int]) -> float:
    pixels = rgb.load()
    mask_pixels = mask.load()
    left, top, right, bottom = bbox
    total = 0.0
    count = 0
    for y in range(top, bottom):
        for x in range(left, right):
            if mask_pixels[x, y] == 0:
                continue
            red, green, blue = pixels[x, y]
            total += max(red, green, blue) - min(red, green, blue)
            count += 1
    return total / max(1, count)


def _median_anchor(metrics: list[dict[str, Any]], anchor: str) -> tuple[float, float]:
    anchors = [_anchor(metric, anchor) for metric in metrics if metric["has_foreground"]]
    if not anchors:
        return (0.0, 0.0)
    return (
        statistics.median(point[0] for point in anchors),
        statistics.median(point[1] for point in anchors),
    )


def _anchor(metric: dict[str, Any], anchor: str) -> tuple[float, float]:
    key = "anchor_bottom_center" if anchor == "bottom_center" else "anchor_center"
    value = metric[key]
    return (float(value[0]), float(value[1]))


def _summarize(metrics: list[dict[str, Any]], anchor: str) -> dict[str, Any]:
    foreground = [metric for metric in metrics if metric["has_foreground"]]
    anchors = [_anchor(metric, anchor) for metric in foreground]
    lumas = [float(metric["foreground_luma"]) for metric in foreground]
    sats = [float(metric["foreground_saturation"]) for metric in foreground]
    return {
        "frames": len(metrics),
        "foreground_frames": len(foreground),
        "anchor_x_stdev": round(statistics.pstdev([point[0] for point in anchors]) if anchors else 0.0, 5),
        "anchor_y_stdev": round(statistics.pstdev([point[1] for point in anchors]) if anchors else 0.0, 5),
        "foreground_luma_stdev": round(statistics.pstdev(lumas) if lumas else 0.0, 5),
        "foreground_saturation_stdev": round(statistics.pstdev(sats) if sats else 0.0, 5),
        "foreground_luma_mean": round(statistics.mean(lumas) if lumas else 0.0, 5),
        "foreground_saturation_mean": round(statistics.mean(sats) if sats else 0.0, 5),
    }


def _clear_wrapped_edges(image: Image.Image, dx: int, dy: int) -> Image.Image:
    out = image.copy()
    transparent = Image.new("RGBA", out.size, (0, 0, 0, 0))
    if dx > 0:
        out.paste(transparent.crop((0, 0, dx, out.height)), (0, 0))
    elif dx < 0:
        out.paste(transparent.crop((0, 0, -dx, out.height)), (out.width + dx, 0))
    if dy > 0:
        out.paste(transparent.crop((0, 0, out.width, dy)), (0, 0))
    elif dy < 0:
        out.paste(transparent.crop((0, 0, out.width, -dy)), (0, out.height + dy))
    return out


def _lerp(left: float, right: float, weight: float) -> float:
    return left + (right - left) * _clamp_float(weight, 0.0, 1.0)


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "stabilized"


if __name__ == "__main__":
    main()
