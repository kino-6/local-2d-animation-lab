from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove pale lower-body guide/shadow artifacts from transparent walk sprite frames."
    )
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--columns", default=6, type=int)
    parser.add_argument("--lower-start-ratio", default=0.50, type=float)
    parser.add_argument("--alpha-threshold", default=24, type=int)
    parser.add_argument("--pale-luma-min", default=72, type=int)
    parser.add_argument("--pale-saturation-max", default=74, type=int)
    parser.add_argument("--green-cast-margin", default=10, type=int)
    parser.add_argument("--protect-grow", default=7, type=int)
    parser.add_argument("--status", default="production_candidate_after_cleanup")
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_lower_body_cleaned")
    run_dir = build_timestamped_run_dir(args.output_root, "sprite_postprocess", label)
    write_run_profile(
        run_dir,
        category="sprite_postprocess",
        label=label,
        args=args,
        memo="Lower-body artifact cleanup for walk motion probes. Review visually before ProductionOK.",
    )
    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []
    frame_reports: list[dict[str, Any]] = []
    for index, source in enumerate(frame_paths):
        image = Image.open(source).convert("RGBA")
        cleaned, report = _clean_frame(
            image,
            lower_start_ratio=args.lower_start_ratio,
            alpha_threshold=args.alpha_threshold,
            pale_luma_min=args.pale_luma_min,
            pale_saturation_max=args.pale_saturation_max,
            green_cast_margin=args.green_cast_margin,
            protect_grow=args.protect_grow,
        )
        output = frames_dir / f"frame_{index:03d}.png"
        cleaned.save(output)
        output_paths.append(output)
        frame_reports.append({"index": index, "source": str(source), "output": str(output), **report})

    spritesheet = make_sprite_sheet(output_paths, run_dir / "spritesheet.png", columns=args.columns)
    contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=args.columns)
    preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    report = {
        "status": args.status,
        "source_frames_dir": str(args.frames_dir),
        "frames_dir": str(frames_dir),
        "frame_count": len(output_paths),
        "fps": args.fps,
        "spritesheet": str(spritesheet),
        "contact_sheet": str(contact_sheet),
        "preview_gif": str(preview),
        "settings": {
            "lower_start_ratio": args.lower_start_ratio,
            "alpha_threshold": args.alpha_threshold,
            "pale_luma_min": args.pale_luma_min,
            "pale_saturation_max": args.pale_saturation_max,
            "green_cast_margin": args.green_cast_margin,
            "protect_grow": args.protect_grow,
        },
        "frame_reports": frame_reports,
        "review_notes": [
            "This removes pale/green lower-body remnants only; it does not fix broken anatomy.",
            "ProductionOK still requires visual review of foot contact, loop closure, and identity.",
        ],
    }
    report_path = run_dir / "lower_body_cleanup_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "frames": str(frames_dir),
                "spritesheet": str(spritesheet),
                "contact_sheet": str(contact_sheet),
                "preview_gif": str(preview),
                "report": str(report_path),
                "removed_pixels": sum(item["removed_pixels"] for item in frame_reports),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _clean_frame(
    image: Image.Image,
    *,
    lower_start_ratio: float,
    alpha_threshold: int,
    pale_luma_min: int,
    pale_saturation_max: int,
    green_cast_margin: int,
    protect_grow: int,
) -> tuple[Image.Image, dict[str, Any]]:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    foreground = alpha.point(lambda value: 255 if value >= alpha_threshold else 0)
    protected = _protected_character_mask(rgba, foreground, protect_grow)
    pixels = rgba.load()
    protected_pixels = protected.load()
    width, height = rgba.size
    lower_start = round(height * lower_start_ratio)
    removed = 0
    candidates = 0

    for y in range(lower_start, height):
        for x in range(width):
            red, green, blue, alpha_value = pixels[x, y]
            if alpha_value < alpha_threshold:
                continue
            luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            saturation = max(red, green, blue) - min(red, green, blue)
            pale_residue = luma >= pale_luma_min and saturation <= pale_saturation_max
            green_residue = (
                luma >= 42
                and green >= red + green_cast_margin
                and blue >= red + max(0, green_cast_margin - 4)
            )
            if not (pale_residue or green_residue):
                continue
            candidates += 1
            if protected_pixels[x, y] > 0 and luma < 150:
                continue
            pixels[x, y] = (red, green, blue, 0)
            removed += 1

    cleaned_alpha = rgba.getchannel("A").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    rgba.putalpha(cleaned_alpha)
    return rgba, {
        "removed_pixels": removed,
        "candidate_pixels": candidates,
        "removed_ratio": round(removed / max(1, width * height), 6),
        "alpha_bbox": list(cleaned_alpha.getbbox()) if cleaned_alpha.getbbox() else None,
    }


def _protected_character_mask(image: Image.Image, foreground: Image.Image, grow: int) -> Image.Image:
    rgb = image.convert("RGB")
    stat = ImageStat.Stat(rgb, foreground)
    mean = stat.mean if stat.count and stat.count[0] else [0, 0, 0]
    mask = Image.new("L", image.size, 0)
    pixels = image.load()
    fg_pixels = foreground.load()
    out = mask.load()
    for y in range(image.height):
        for x in range(image.width):
            if fg_pixels[x, y] == 0:
                continue
            red, green, blue, alpha_value = pixels[x, y]
            if alpha_value == 0:
                continue
            luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            saturation = max(red, green, blue) - min(red, green, blue)
            close_to_mean = sum(abs(channel - base) for channel, base in zip((red, green, blue), mean)) < 90
            if luma < 80 or saturation > 76 or close_to_mean:
                out[x, y] = 255
    for _ in range(max(0, grow // 2)):
        mask = mask.filter(ImageFilter.MaxFilter(3))
    return mask


def _frame_index(path: Path) -> tuple[int, str]:
    digits = "".join(char for char in path.stem if char.isdigit())
    return (int(digits) if digits else 0, path.name)


def _safe_label(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_") or "lower_body_cleaned"


if __name__ == "__main__":
    main()
