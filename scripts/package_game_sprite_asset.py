from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Package PNG frames as a game-ready 2D sprite asset.")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--asset-name", default="character")
    parser.add_argument("--animation", default="idle")
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--frame-width", default=512, type=int)
    parser.add_argument("--frame-height", default=768, type=int)
    parser.add_argument("--target-height", default=704, type=int)
    parser.add_argument("--background-threshold", default=88, type=int)
    parser.add_argument("--background-min-channel", default=205, type=int)
    parser.add_argument("--pad", default=24, type=int)
    parser.add_argument("--columns", default=None, type=int)
    parser.add_argument("--status", default=None)
    parser.add_argument("--quality-report", action="append", default=[], type=Path)
    args = parser.parse_args()

    source_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not source_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.asset_name}_{args.animation}_game_asset")
    run_dir = build_timestamped_run_dir(args.output_root, "game_sprite_asset", label)
    write_run_profile(
        run_dir,
        category="game_sprite_asset",
        label=label,
        args=args,
        memo="Packaged 2D game sprite asset. Check manifest status before treating this as adopted output.",
    )
    full_dir = run_dir / "frames_rgba_source_size"
    trim_dir = run_dir / "frames_trimmed"
    game_dir = run_dir / "frames"
    for directory in (full_dir, trim_dir, game_dir):
        directory.mkdir(parents=True, exist_ok=True)

    full_frames = []
    source_reports = []
    for index, source in enumerate(source_paths):
        rgba, report = _remove_background(
            source,
            threshold=args.background_threshold,
            min_channel=args.background_min_channel,
        )
        output = full_dir / f"frame_{index:03d}.png"
        rgba.save(output)
        full_frames.append(output)
        source_reports.append({"index": index, "source": str(source), "rgba": str(output), **report})

    union = _union_alpha_bbox(full_frames)
    if union is None:
        raise RuntimeError("No foreground alpha found after background removal.")
    union = _pad_bbox(union, Image.open(full_frames[0]).size, args.pad)

    trimmed_frames = []
    game_frames = []
    frame_entries = []
    for index, frame_path in enumerate(full_frames):
        frame = Image.open(frame_path).convert("RGBA")
        trimmed = frame.crop(union)
        trim_path = trim_dir / f"frame_{index:03d}.png"
        trimmed.save(trim_path)
        trimmed_frames.append(trim_path)

        game = _fit_to_game_canvas(trimmed, args.frame_width, args.frame_height, args.target_height)
        game_path = game_dir / f"frame_{index:03d}.png"
        game.save(game_path)
        game_frames.append(game_path)
        frame_entries.append(
            {
                "index": index,
                "file": str(game_path.relative_to(run_dir)).replace("\\", "/"),
                "duration_ms": round(1000 / args.fps),
                "pivot": {"x": 0.5, "y": 1.0},
                "source_bbox": list(union),
            }
        )

    spritesheet = make_sprite_sheet(game_frames, run_dir / "spritesheet.png", columns=args.columns or len(game_frames))
    contact_sheet = make_contact_sheet(game_frames, run_dir / "contact_sheet.png", columns=min(6, len(game_frames)))
    preview = make_preview_gif(game_frames, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    alpha_contact = _make_alpha_contact_sheet(game_frames, run_dir / "alpha_contact_sheet.png")

    status = args.status or ("still_sprite_proof_only" if len(game_frames) <= 2 else "animation_candidate")
    manifest = {
        "asset_name": args.asset_name,
        "animation": args.animation,
        "asset_kind": "2d_game_sprite",
        "status": status,
        "frame_count": len(game_frames),
        "fps": args.fps,
        "frame_size": {"width": args.frame_width, "height": args.frame_height},
        "pivot": {"x": 0.5, "y": 1.0},
        "spritesheet": str(spritesheet.relative_to(run_dir)).replace("\\", "/"),
        "preview_gif": str(preview.relative_to(run_dir)).replace("\\", "/"),
        "contact_sheet": str(contact_sheet.relative_to(run_dir)).replace("\\", "/"),
        "alpha_contact_sheet": str(alpha_contact.relative_to(run_dir)).replace("\\", "/"),
        "frames": frame_entries,
        "source": {
            "frames_dir": str(args.frames_dir),
            "source_frame_count": len(source_paths),
            "union_alpha_bbox": list(union),
        },
        "quality_reports": [str(path) for path in args.quality_report],
        "import_notes": [
            "Use frames/*.png or spritesheet.png in engine import.",
            "Pivot is bottom-center for character placement.",
            "Manifest status records whether the animation is adoptable; packaging alone is not proof of action readability.",
        ],
        "background_removal": {
            "threshold": args.background_threshold,
            "min_channel": args.background_min_channel,
            "source_reports": source_reports,
        },
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "README.md").write_text(_readme(manifest), encoding="utf-8")

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "frames": str(game_dir),
                "spritesheet": str(spritesheet),
                "manifest": str(manifest_path),
                "preview": str(preview),
                "contact_sheet": str(contact_sheet),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _remove_background(source: Path, threshold: int, min_channel: int) -> tuple[Image.Image, dict[str, Any]]:
    image = Image.open(source).convert("RGBA")
    rgb = _flatten(image).convert("RGB")
    background = _estimate_background(rgb)
    rgba = rgb.convert("RGBA")
    background_mask = _connected_background_mask(rgb, background, threshold, min_channel)
    pixels = rgba.load()
    bg_pixels = background_mask.load()
    alpha_count = 0
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, _ = pixels[x, y]
            if bg_pixels[x, y] > 0:
                pixels[x, y] = (red, green, blue, 0)
            else:
                pixels[x, y] = (red, green, blue, 255)
                alpha_count += 1
    alpha = rgba.getchannel("A").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    rgba.putalpha(alpha)
    bbox = alpha.getbbox()
    return rgba, {
        "estimated_background": list(background),
        "alpha_bbox": list(bbox) if bbox else None,
        "alpha_coverage": round(alpha_count / (rgba.width * rgba.height), 5),
    }


def _flatten(image: Image.Image) -> Image.Image:
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    return background


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    pixels = image.load()
    width, height = image.size
    samples = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
        pixels[width // 2, 0],
        pixels[width // 2, height - 1],
    ]
    return tuple(round(sum(sample[channel] for sample in samples) / len(samples)) for channel in range(3))


def _connected_background_mask(
    image: Image.Image,
    background: tuple[int, int, int],
    threshold: int,
    min_channel: int,
) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    candidate = Image.new("L", image.size, 0)
    candidate_pixels = candidate.load()
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            if distance <= threshold and min(red, green, blue) >= min_channel:
                candidate_pixels[x, y] = 255

    out = Image.new("L", image.size, 0)
    out_pixels = out.load()
    stack: list[tuple[int, int]] = []
    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height:
            continue
        if out_pixels[x, y] > 0 or candidate_pixels[x, y] == 0:
            continue
        out_pixels[x, y] = 255
        stack.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    return out


def _union_alpha_bbox(frame_paths: list[Path]) -> tuple[int, int, int, int] | None:
    boxes = [Image.open(path).convert("RGBA").getchannel("A").getbbox() for path in frame_paths]
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _pad_bbox(bbox: tuple[int, int, int, int], size: tuple[int, int], pad: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    width, height = size
    return (max(0, left - pad), max(0, top - pad), min(width, right + pad), min(height, bottom + pad))


def _fit_to_game_canvas(image: Image.Image, width: int, height: int, target_height: int) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))
    subject = image.crop(bbox)
    scale = min(width * 0.92 / subject.width, target_height / subject.height)
    resized = subject.resize(
        (max(1, round(subject.width * scale)), max(1, round(subject.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    x = (width - resized.width) // 2
    y = height - resized.height
    canvas.alpha_composite(resized, (x, y))
    return canvas


def _make_alpha_contact_sheet(frame_paths: list[Path], output: Path) -> Path:
    masks = []
    for path in frame_paths:
        alpha = Image.open(path).convert("RGBA").getchannel("A")
        masks.append(Image.merge("RGBA", (alpha, alpha, alpha, alpha)))
    temp_dir = output.parent / "_alpha_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_paths = []
    for index, mask in enumerate(masks):
        path = temp_dir / f"alpha_{index:03d}.png"
        mask.save(path)
        temp_paths.append(path)
    make_contact_sheet(temp_paths, output, columns=min(6, len(temp_paths)))
    for path in temp_paths:
        path.unlink(missing_ok=True)
    temp_dir.rmdir()
    return output


def _readme(manifest: dict[str, Any]) -> str:
    return f"""# {manifest['asset_name']} / {manifest['animation']}

Game-ready 2D sprite asset package.

- status: `{manifest['status']}`
- frame_count: `{manifest['frame_count']}`
- fps: `{manifest['fps']}`
- frame_size: `{manifest['frame_size']['width']}x{manifest['frame_size']['height']}`
- pivot: bottom-center `(0.5, 1.0)`
- spritesheet: `{manifest['spritesheet']}`
- manifest: `manifest.json`

Use `frames/*.png` for individual transparent frames or `spritesheet.png` for atlas import.

Note: this package is a sprite asset package. If `status` is `still_sprite_proof_only`, it is not an action-readable animation.
"""


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "game_sprite_asset"


if __name__ == "__main__":
    main()
