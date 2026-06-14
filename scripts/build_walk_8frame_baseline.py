from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps

try:
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


ROUTE = "walk_8frame_sideview_baseline"
ROUTE_STATUS = "baseline_not_production"
DEFAULT_REFERENCE = Path("assets/reference/generated/anima_00013_sidecar_walk_start_source_20260614.png")
DEFAULT_OUTPUT = Path("outputs/adoptable/walk_8frame_sideview_baseline")
ACTION_SPEC = {
    "action": "walk",
    "direction": "right",
    "frame_count": 8,
    "view": "side",
    "loop": True,
    "background": "transparent",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic 8-frame side-view walk MVP package from one character reference."
    )
    parser.add_argument("--input", default=DEFAULT_REFERENCE, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--instruction", default="Create an 8-frame side-view walk cycle facing right.")
    parser.add_argument("--frame-width", default=512, type=int)
    parser.add_argument("--frame-height", default=512, type=int)
    parser.add_argument("--target-height", default=430, type=int)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--background-threshold", default=88, type=int)
    parser.add_argument("--background-min-channel", default=205, type=int)
    parser.add_argument("--pad", default=24, type=int)
    parser.add_argument("--mirror-to-right", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    manifest = build_walk_8frame_baseline(
        source_path=args.input,
        output_dir=args.output_dir,
        instruction=args.instruction,
        frame_width=args.frame_width,
        frame_height=args.frame_height,
        target_height=args.target_height,
        fps=args.fps,
        background_threshold=args.background_threshold,
        background_min_channel=args.background_min_channel,
        pad=args.pad,
        mirror_to_right=args.mirror_to_right,
        clean=args.clean,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def build_walk_8frame_baseline(
    source_path: Path,
    output_dir: Path = DEFAULT_OUTPUT,
    instruction: str = "Create an 8-frame side-view walk cycle facing right.",
    frame_width: int = 512,
    frame_height: int = 512,
    target_height: int = 430,
    fps: int = 8,
    background_threshold: int = 88,
    background_min_channel: int = 205,
    pad: int = 24,
    mirror_to_right: bool = True,
    clean: bool = True,
) -> dict[str, Any]:
    if ACTION_SPEC["frame_count"] != 8:
        raise RuntimeError("This route is fixed to exactly 8 frames.")
    if not source_path.exists():
        raise FileNotFoundError(f"Reference image not found: {source_path}")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cutout, cutout_report = _load_reference_cutout(
        source_path,
        background_threshold=background_threshold,
        background_min_channel=background_min_channel,
        pad=pad,
    )
    if mirror_to_right:
        cutout = ImageOps.mirror(cutout)
    cutout_report["mirror_to_direction_right"] = mirror_to_right
    fitted = _fit_cutout_to_canvas(cutout, frame_width, frame_height, target_height)
    frame_paths = _write_walk_frames(fitted, frames_dir)

    spritesheet = make_sprite_sheet(frame_paths, output_dir / "spritesheet.png", columns=8)
    preview = make_preview_gif(frame_paths, output_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    contact_sheet = make_contact_sheet(frame_paths, output_dir / "contact_sheet.png", columns=4)

    manifest = {
        "route": ROUTE,
        "route_status": ROUTE_STATUS,
        "asset_kind": "2d_game_sprite",
        "output_status": "adoptable_mvp_baseline",
        "instruction": instruction,
        "action_spec": ACTION_SPEC,
        "frame_count": 8,
        "fps": fps,
        "loop": True,
        "frame_size": {"width": frame_width, "height": frame_height},
        "pivot": {"x": 0.5, "y": 1.0},
        "background": "transparent",
        "source_reference": str(source_path).replace("\\", "/"),
        "outputs": {
            "frames": [str(path.relative_to(output_dir)).replace("\\", "/") for path in frame_paths],
            "spritesheet": str(spritesheet.relative_to(output_dir)).replace("\\", "/"),
            "preview_gif": str(preview.relative_to(output_dir)).replace("\\", "/"),
            "contact_sheet": str(contact_sheet.relative_to(output_dir)).replace("\\", "/"),
        },
        "method": {
            "type": "deterministic_cutout_baseline",
            "uses_comfyui": False,
            "uses_wan_video": False,
            "uses_120_frame_generation": False,
            "motion": "whole-body bob plus small lower-body offset; no generative redraw",
            "cutout": cutout_report,
        },
        "quality_bar": {
            "exactly_one_character_expected": True,
            "canvas_size_consistent": True,
            "transparent_frames": True,
            "production_grade_art": False,
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "notes.md").write_text(_notes(manifest), encoding="utf-8")
    return manifest


def _load_reference_cutout(
    source_path: Path,
    background_threshold: int,
    background_min_channel: int,
    pad: int,
) -> tuple[Image.Image, dict[str, Any]]:
    image = Image.open(source_path).convert("RGBA")
    alpha = image.getchannel("A")
    alpha_min, alpha_max = alpha.getextrema()
    if alpha_min < 255 and alpha_max > 0:
        rgba = image
        mask_mode = "existing_alpha"
    else:
        rgb = _flatten(image).convert("RGB")
        background = _estimate_background(rgb)
        mask = _connected_background_mask(rgb, background, background_threshold, background_min_channel)
        rgba = rgb.convert("RGBA")
        pixels = rgba.load()
        bg_pixels = mask.load()
        for y in range(rgba.height):
            for x in range(rgba.width):
                red, green, blue, _ = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0 if bg_pixels[x, y] else 255)
        alpha = rgba.getchannel("A").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
        rgba.putalpha(alpha)
        mask_mode = "connected_background"

    bbox = rgba.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError(f"No foreground detected in reference: {source_path}")
    bbox = _pad_bbox(bbox, rgba.size, pad)
    cutout = rgba.crop(bbox)
    return cutout, {
        "mask_mode": mask_mode,
        "source_size": {"width": image.width, "height": image.height},
        "alpha_bbox": list(bbox),
        "pad": pad,
    }


def _fit_cutout_to_canvas(
    cutout: Image.Image,
    frame_width: int,
    frame_height: int,
    target_height: int,
) -> Image.Image:
    bbox = cutout.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError("Cutout has no alpha foreground.")
    subject = cutout.crop(bbox)
    max_width = int(frame_width * 0.86)
    scale = min(max_width / subject.width, target_height / subject.height)
    resized = subject.resize(
        (max(1, round(subject.width * scale)), max(1, round(subject.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    x = (frame_width - resized.width) // 2
    y = frame_height - resized.height
    canvas.alpha_composite(resized, (x, y))
    return canvas


def _write_walk_frames(base: Image.Image, frames_dir: Path) -> list[Path]:
    # Keep the effect deliberately small: this is an adoptable baseline, not animation synthesis.
    cycle = [
        {"body_x": 0, "body_y": 0, "lower_x": 0},
        {"body_x": 1, "body_y": -2, "lower_x": 3},
        {"body_x": 1, "body_y": -4, "lower_x": 6},
        {"body_x": 0, "body_y": -2, "lower_x": 3},
        {"body_x": 0, "body_y": 0, "lower_x": 0},
        {"body_x": -1, "body_y": 1, "lower_x": -3},
        {"body_x": -1, "body_y": 2, "lower_x": -6},
        {"body_x": 0, "body_y": 1, "lower_x": -3},
    ]
    frame_paths: list[Path] = []
    for index, motion in enumerate(cycle):
        frame = _compose_walk_frame(base, motion["body_x"], motion["body_y"], motion["lower_x"])
        path = frames_dir / f"walk_{index:03d}.png"
        frame.save(path)
        frame_paths.append(path)
    return frame_paths


def _compose_walk_frame(base: Image.Image, body_x: int, body_y: int, lower_x: int) -> Image.Image:
    width, height = base.size
    bbox = base.getchannel("A").getbbox()
    if bbox is None:
        return Image.new("RGBA", base.size, (0, 0, 0, 0))

    left, top, right, bottom = bbox
    hip_y = top + round((bottom - top) * 0.56)
    overlap = 10
    upper = base.crop((left, top, right, min(bottom, hip_y + overlap)))
    lower = base.crop((left, max(top, hip_y - overlap), right, bottom))

    frame = Image.new("RGBA", base.size, (0, 0, 0, 0))
    frame.alpha_composite(lower, (left + body_x + lower_x, max(top, hip_y - overlap) + body_y))
    frame.alpha_composite(upper, (left + body_x, top + body_y))
    return frame


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


def _pad_bbox(bbox: tuple[int, int, int, int], size: tuple[int, int], pad: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    width, height = size
    return (max(0, left - pad), max(0, top - pad), min(width, right + pad), min(height, bottom + pad))


def _notes(manifest: dict[str, Any]) -> str:
    return f"""# Walk 8-Frame Side-View Baseline

This is a deliberately conservative MVP package for game import review.

- route: `{manifest["route"]}`
- route_status: `{manifest["route_status"]}`
- frame_count: `{manifest["frame_count"]}`
- fps: `{manifest["fps"]}`
- frame_size: `{manifest["frame_size"]["width"]}x{manifest["frame_size"]["height"]}`
- action: `walk`
- direction: `right`
- view: `side`
- loop: `true`
- background: `transparent`

## What This Is

The package starts from one reference cutout and applies a tiny deterministic walk-cycle baseline:
whole-body bob plus a small lower-body offset. It preserves one character silhouette and stable canvas
layout over motion realism.

## What This Is Not

- Not production-grade animation.
- Not Wan/video generation.
- Not a 120-frame candidate.
- Not attack, hit, run, weapon, or broad action generation.
- Not proof that the generative pipeline can make final-quality walk cycles.

Use this as the boring concrete artifact route: `frames/*.png`, `spritesheet.png`, and `preview.gif`
are the review targets.
"""


if __name__ == "__main__":
    main()
