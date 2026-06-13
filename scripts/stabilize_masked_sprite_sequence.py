from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize sprite foreground brightness/saturation using explicit foreground masks."
    )
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--masks-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--columns", default=11, type=int)
    parser.add_argument("--target", choices=("first", "median"), default="first")
    parser.add_argument(
        "--color-mode",
        choices=("luma_saturation", "rgb_mean", "histogram_match"),
        default="luma_saturation",
    )
    parser.add_argument("--mask-threshold", default=128, type=int)
    parser.add_argument("--brightness-strength", default=0.85, type=float)
    parser.add_argument("--saturation-strength", default=0.85, type=float)
    parser.add_argument("--min-factor", default=0.65, type=float)
    parser.add_argument("--max-factor", default=3.2, type=float)
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    mask_paths = sorted(args.masks_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")
    if len(frame_paths) != len(mask_paths):
        raise ValueError(f"Frame/mask count mismatch: {len(frame_paths)} frames, {len(mask_paths)} masks")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_masked_stabilized")
    run_dir = build_timestamped_run_dir(args.output_root, "sprite_postprocess", label)
    write_run_profile(
        run_dir,
        category="sprite_postprocess",
        label=label,
        args=args,
        memo="Masked foreground brightness/saturation normalization.",
    )
    frames_out = run_dir / "frames"
    frames_out.mkdir(parents=True, exist_ok=True)

    frames = [Image.open(path).convert("RGB") for path in frame_paths]
    masks = [_load_mask(path, frames[index].size, args.mask_threshold) for index, path in enumerate(mask_paths)]
    metrics = [_masked_metrics(frame, mask) for frame, mask in zip(frames, masks)]
    target_metrics = _target(metrics, args.target)
    target_histograms = _target_histograms(frames, masks, metrics, args.target)

    output_paths: list[Path] = []
    frame_reports: list[dict[str, Any]] = []
    for index, (frame_path, mask_path, frame, mask, metric) in enumerate(zip(frame_paths, mask_paths, frames, masks, metrics)):
        corrected, correction = _correct(
            frame,
            mask,
            metric,
            target_metrics=target_metrics,
            color_mode=args.color_mode,
            brightness_strength=args.brightness_strength,
            saturation_strength=args.saturation_strength,
            min_factor=args.min_factor,
            max_factor=args.max_factor,
            target_histograms=target_histograms,
        )
        output_path = frames_out / f"frame_{index:03d}.png"
        corrected.save(output_path)
        output_paths.append(output_path)
        frame_reports.append(
            {
                "index": index,
                "source": str(frame_path),
                "mask": str(mask_path),
                "output": str(output_path),
                "before": metric,
                "after": _masked_metrics(corrected, mask),
                "correction": correction,
            }
        )

    contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=args.columns)
    spritesheet = make_sprite_sheet(output_paths, run_dir / "spritesheet.png", columns=args.columns)
    preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    report = {
        "status": "completed",
        "source_frames_dir": str(args.frames_dir),
        "source_masks_dir": str(args.masks_dir),
        "frames_dir": str(frames_out),
        "contact_sheet": str(contact_sheet),
        "spritesheet": str(spritesheet),
        "preview_gif": str(preview),
        "settings": {
            "fps": args.fps,
            "target": args.target,
            "color_mode": args.color_mode,
            "mask_threshold": args.mask_threshold,
            "brightness_strength": args.brightness_strength,
            "saturation_strength": args.saturation_strength,
            "min_factor": args.min_factor,
            "max_factor": args.max_factor,
        },
        "target_metrics": {
            "foreground_luma": round(float(target_metrics["foreground_luma"]), 5),
            "foreground_saturation": round(float(target_metrics["foreground_saturation"]), 5),
            "foreground_rgb": [round(float(value), 5) for value in target_metrics["foreground_rgb"]],
        },
        "before_summary": _summarize([report["before"] for report in frame_reports]),
        "after_summary": _summarize([report["after"] for report in frame_reports]),
        "frame_reports": frame_reports,
    }
    report_path = run_dir / "stabilize_masked_sprite_sequence_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "contact_sheet": str(contact_sheet), "preview_gif": str(preview), "before_summary": report["before_summary"], "after_summary": report["after_summary"]}, indent=2, ensure_ascii=False))


def _load_mask(path: Path, size: tuple[int, int], threshold: int) -> Image.Image:
    mask = Image.open(path).convert("L").resize(size, Image.Resampling.BICUBIC)
    return mask.point(lambda value: 255 if value >= threshold else 0)


def _masked_metrics(frame: Image.Image, mask: Image.Image) -> dict[str, Any]:
    bbox = mask.getbbox()
    if bbox is None:
        return {"has_foreground": False, "foreground_luma": 0.0, "foreground_saturation": 0.0, "foreground_coverage": 0.0}
    stat = ImageStat.Stat(frame, mask)
    mean = stat.mean
    luma = 0.2126 * mean[0] + 0.7152 * mean[1] + 0.0722 * mean[2]
    saturation = _mean_saturation(frame, mask, bbox)
    coverage = float(ImageStat.Stat(mask).mean[0]) / 255.0
    return {
        "has_foreground": True,
        "bbox": list(bbox),
        "foreground_luma": round(luma, 5),
        "foreground_saturation": round(saturation, 5),
        "foreground_rgb": [round(float(value), 5) for value in mean],
        "foreground_coverage": round(coverage, 5),
    }


def _target(metrics: list[dict[str, Any]], target: str) -> dict[str, Any]:
    foreground = [metric for metric in metrics if metric["has_foreground"]]
    if not foreground:
        return {"foreground_luma": 1.0, "foreground_saturation": 1.0, "foreground_rgb": [1.0, 1.0, 1.0]}
    if target == "first":
        return foreground[0]
    return {
        "foreground_luma": statistics.median(float(metric["foreground_luma"]) for metric in foreground),
        "foreground_saturation": statistics.median(float(metric["foreground_saturation"]) for metric in foreground),
        "foreground_rgb": [
            statistics.median(float(metric["foreground_rgb"][channel]) for metric in foreground)
            for channel in range(3)
        ],
    }


def _target_histograms(
    frames: list[Image.Image],
    masks: list[Image.Image],
    metrics: list[dict[str, Any]],
    target: str,
) -> list[list[int]] | None:
    foreground_indexes = [index for index, metric in enumerate(metrics) if metric["has_foreground"]]
    if not foreground_indexes:
        return None
    if target == "first":
        target_index = foreground_indexes[0]
    else:
        lumas = [float(metrics[index]["foreground_luma"]) for index in foreground_indexes]
        median_luma = statistics.median(lumas)
        target_index = min(
            foreground_indexes,
            key=lambda index: abs(float(metrics[index]["foreground_luma"]) - median_luma),
        )
    return _masked_histograms(frames[target_index], masks[target_index])


def _correct(
    frame: Image.Image,
    mask: Image.Image,
    metric: dict[str, Any],
    *,
    target_metrics: dict[str, Any],
    color_mode: str,
    brightness_strength: float,
    saturation_strength: float,
    min_factor: float,
    max_factor: float,
    target_histograms: list[list[int]] | None = None,
) -> tuple[Image.Image, dict[str, float]]:
    if not metric["has_foreground"]:
        return frame.copy(), {"brightness_factor": 1.0, "saturation_factor": 1.0}
    if color_mode == "rgb_mean":
        adjusted, factors = _adjust_rgb_mean(
            frame,
            metric,
            target_metrics,
            strength=brightness_strength,
            min_factor=min_factor,
            max_factor=max_factor,
        )
        white = Image.new("RGB", frame.size, (255, 255, 255))
        out = Image.composite(adjusted, white, mask)
        return out, factors

    if color_mode == "histogram_match":
        adjusted, correction = _adjust_histogram_match(
            frame,
            mask,
            target_histograms,
            strength=brightness_strength,
        )
        white = Image.new("RGB", frame.size, (255, 255, 255))
        out = Image.composite(adjusted, white, mask)
        return out, correction

    target_luma = float(target_metrics["foreground_luma"])
    target_saturation = float(target_metrics["foreground_saturation"])
    luma = max(1e-6, float(metric["foreground_luma"]))
    saturation = max(1e-6, float(metric["foreground_saturation"]))
    brightness_factor = _clamp_float(_lerp(1.0, target_luma / luma, brightness_strength), min_factor, max_factor)
    saturation_factor = _clamp_float(_lerp(1.0, target_saturation / saturation, saturation_strength), min_factor, max_factor)

    adjusted = ImageEnhance.Brightness(frame).enhance(brightness_factor)
    adjusted = ImageEnhance.Color(adjusted).enhance(saturation_factor)
    white = Image.new("RGB", frame.size, (255, 255, 255))
    out = Image.composite(adjusted, white, mask)
    return out, {
        "brightness_factor": round(brightness_factor, 5),
        "saturation_factor": round(saturation_factor, 5),
    }


def _adjust_rgb_mean(
    frame: Image.Image,
    metric: dict[str, Any],
    target_metrics: dict[str, Any],
    *,
    strength: float,
    min_factor: float,
    max_factor: float,
) -> tuple[Image.Image, dict[str, float]]:
    current_rgb = [max(1e-6, float(value)) for value in metric["foreground_rgb"]]
    target_rgb = [float(value) for value in target_metrics["foreground_rgb"]]
    factors = [
        _clamp_float(_lerp(1.0, target_rgb[channel] / current_rgb[channel], strength), min_factor, max_factor)
        for channel in range(3)
    ]
    red, green, blue = frame.split()
    channels = [
        channel.point(lambda value, factor=factor: int(_clamp_float(value * factor, 0, 255)))
        for channel, factor in zip((red, green, blue), factors)
    ]
    return Image.merge("RGB", channels), {
        "red_factor": round(factors[0], 5),
        "green_factor": round(factors[1], 5),
        "blue_factor": round(factors[2], 5),
    }


def _adjust_histogram_match(
    frame: Image.Image,
    mask: Image.Image,
    target_histograms: list[list[int]] | None,
    *,
    strength: float,
) -> tuple[Image.Image, dict[str, float]]:
    if target_histograms is None:
        return frame.copy(), {"histogram_strength": 0.0}
    source_histograms = _masked_histograms(frame, mask)
    lookups = [
        _histogram_lookup(source_histograms[channel], target_histograms[channel])
        for channel in range(3)
    ]
    channels = []
    for channel, lookup in zip(frame.split(), lookups):
        mapped = channel.point(lookup)
        if strength >= 1.0:
            channels.append(mapped)
            continue
        channels.append(Image.blend(channel, mapped, _clamp_float(strength, 0.0, 1.0)))
    return Image.merge("RGB", channels), {"histogram_strength": round(_clamp_float(strength, 0.0, 1.0), 5)}


def _masked_histograms(frame: Image.Image, mask: Image.Image) -> list[list[int]]:
    channels = frame.split()
    return [channel.histogram(mask=mask) for channel in channels]


def _histogram_lookup(source_histogram: list[int], target_histogram: list[int]) -> list[int]:
    source_total = max(1, sum(source_histogram))
    target_total = max(1, sum(target_histogram))
    source_cdf = _cdf(source_histogram, source_total)
    target_cdf = _cdf(target_histogram, target_total)
    lookup: list[int] = []
    target_value = 0
    for source_value in range(256):
        while target_value < 255 and target_cdf[target_value] < source_cdf[source_value]:
            target_value += 1
        lookup.append(target_value)
    return lookup


def _cdf(histogram: list[int], total: int) -> list[float]:
    cumulative = 0
    values = []
    for count in histogram:
        cumulative += count
        values.append(cumulative / total)
    return values


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


def _summarize(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    foreground = [metric for metric in metrics if metric["has_foreground"]]
    lumas = [float(metric["foreground_luma"]) for metric in foreground]
    saturations = [float(metric["foreground_saturation"]) for metric in foreground]
    return {
        "frames": len(metrics),
        "foreground_frames": len(foreground),
        "foreground_luma_stdev": round(statistics.pstdev(lumas) if lumas else 0.0, 5),
        "foreground_saturation_stdev": round(statistics.pstdev(saturations) if saturations else 0.0, 5),
        "foreground_luma_mean": round(statistics.mean(lumas) if lumas else 0.0, 5),
        "foreground_saturation_mean": round(statistics.mean(saturations) if saturations else 0.0, 5),
    }


def _lerp(left: float, right: float, amount: float) -> float:
    return left + (right - left) * amount


def _clamp_float(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "masked_stabilized"


if __name__ == "__main__":
    main()
