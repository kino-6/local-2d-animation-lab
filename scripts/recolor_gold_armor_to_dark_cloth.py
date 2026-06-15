from __future__ import annotations

import argparse
import colorsys
import json
from pathlib import Path
from typing import Any

from PIL import Image

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recolor gold armor-like accents in sprite frames into dark cloth/leather accents."
    )
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--fps", default=10, type=int)
    parser.add_argument("--columns", default=8, type=int)
    parser.add_argument("--status", default="production_candidate_identity_recolored")
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_gold_to_cloth")
    run_dir = build_timestamped_run_dir(args.output_root, "sprite_postprocess", label)
    write_run_profile(
        run_dir,
        category="sprite_postprocess",
        label=label,
        args=args,
        memo="Identity cleanup: reduce gold armor drift by converting yellow metal accents to dark cloth/leather.",
    )
    out_dir = run_dir / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []
    frame_reports: list[dict[str, Any]] = []
    for index, path in enumerate(frame_paths):
        image = Image.open(path).convert("RGBA")
        recolored, report = _recolor_frame(image)
        output = out_dir / f"frame_{index:03d}.png"
        recolored.save(output)
        output_paths.append(output)
        frame_reports.append({"index": index, "source": str(path), "output": str(output), **report})

    spritesheet = make_sprite_sheet(output_paths, run_dir / "spritesheet.png", columns=args.columns)
    contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=args.columns)
    preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    report = {
        "status": args.status,
        "source_frames_dir": str(args.frames_dir),
        "frames_dir": str(out_dir),
        "frame_count": len(output_paths),
        "fps": args.fps,
        "spritesheet": str(spritesheet),
        "contact_sheet": str(contact_sheet),
        "preview_gif": str(preview),
        "frame_reports": frame_reports,
        "summary": {
            "recolored_pixels": sum(item["recolored_pixels"] for item in frame_reports),
            "gold_pixels_before": sum(item["gold_pixels_before"] for item in frame_reports),
            "gold_pixels_after": sum(item["gold_pixels_after"] for item in frame_reports),
        },
        "review_notes": [
            "This is a color/identity cleanup only; it does not change silhouette or pose.",
            "Use visual review to confirm the character now reads as black gothic cloth/leather, not gold armor.",
        ],
    }
    report_path = run_dir / "recolor_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "frames": str(out_dir),
                "spritesheet": str(spritesheet),
                "contact_sheet": str(contact_sheet),
                "preview_gif": str(preview),
                "report": str(report_path),
                "summary": report["summary"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _recolor_frame(image: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    rgba = image.convert("RGBA")
    alpha_bbox = rgba.getchannel("A").getbbox()
    pixels = rgba.load()
    width, height = rgba.size
    recolored = 0
    regional_recolored = 0
    before = 0
    after = 0
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 24:
                continue
            if (_is_gold_like(red, green, blue) or _is_gold_like_after(red, green, blue)) and not _is_skin_like(
                red, green, blue
            ):
                before += 1
                nr, ng, nb = _to_dark_cloth(red, green, blue)
                pixels[x, y] = (nr, ng, nb, alpha)
                recolored += 1
            elif alpha_bbox is not None and _is_upper_side_armor_highlight(x, y, red, green, blue, alpha_bbox):
                nr, ng, nb = _to_dark_cloth(red, green, blue)
                pixels[x, y] = (nr, ng, nb, alpha)
                recolored += 1
                regional_recolored += 1
            elif _is_gold_like_after(red, green, blue):
                before += 1
            nr, ng, nb, _ = pixels[x, y]
            if _is_gold_like_after(nr, ng, nb):
                after += 1
    return rgba, {
        "recolored_pixels": recolored,
        "regional_upper_side_recolored_pixels": regional_recolored,
        "gold_pixels_before": before,
        "gold_pixels_after": after,
        "recolored_ratio": round(recolored / max(1, width * height), 6),
    }


def _is_gold_like(red: int, green: int, blue: int) -> bool:
    hue, sat, val = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    yellow_hue = 0.075 <= hue <= 0.17
    warm_metal = red >= 95 and green >= 72 and blue <= 115 and red >= blue + 28 and green >= blue + 18
    bright_yellow = red >= 150 and green >= 120 and blue <= 135 and sat >= 0.18
    pale_gold_highlight = (
        yellow_hue
        and sat >= 0.08
        and val >= 0.38
        and red >= 95
        and green >= 78
        and green >= blue + 16
        and red >= blue + 10
        and abs(red - green) <= 70
    )
    return bool((yellow_hue and sat >= 0.22 and val >= 0.25 and warm_metal) or bright_yellow or pale_gold_highlight)


def _is_gold_like_after(red: int, green: int, blue: int) -> bool:
    hue, sat, val = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    return bool(0.075 <= hue <= 0.17 and sat >= 0.1 and val >= 0.35 and green >= blue + 12)


def _is_skin_like(red: int, green: int, blue: int) -> bool:
    hue, sat, val = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    warm_skin = 0.0 <= hue <= 0.07 and sat >= 0.16 and val >= 0.45
    pale_skin = red >= 150 and green >= 115 and blue >= 100 and red >= green and green >= blue
    return bool(warm_skin and pale_skin)


def _is_upper_side_armor_highlight(
    x: int,
    y: int,
    red: int,
    green: int,
    blue: int,
    alpha_bbox: tuple[int, int, int, int],
) -> bool:
    left, top, right, bottom = alpha_bbox
    width = max(1, right - left)
    height = max(1, bottom - top)
    side_region = x >= left + width * 0.60 and top + height * 0.14 <= y <= top + height * 0.43
    if not side_region:
        return False
    if _is_skin_like(red, green, blue):
        return False
    luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    hue, sat, _ = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    warm_or_bright = (
        0.06 <= hue <= 0.18
        or (red >= green >= blue and sat >= 0.08)
        or (sat <= 0.18 and luma >= 96)
    )
    return bool(luma >= 74 and warm_or_bright)


def _to_dark_cloth(red: int, green: int, blue: int) -> tuple[int, int, int]:
    luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    highlight = max(0.0, min(1.0, (luma - 70) / 150))
    base = 18 + round(highlight * 38)
    # Cool black-brown leather. Keep a tiny warm edge so details are not lost.
    return (
        max(10, min(72, base + 8)),
        max(10, min(66, base + 3)),
        max(12, min(76, base + 10)),
    )


def _frame_index(path: Path) -> tuple[int, str]:
    digits = "".join(char for char in path.stem if char.isdigit())
    return (int(digits) if digits else 0, path.name)


def _safe_label(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_") or "gold_to_cloth"


if __name__ == "__main__":
    main()
