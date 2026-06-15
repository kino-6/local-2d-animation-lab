from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a right-facing side-view sprite from a 3-view design sheet.")
    parser.add_argument("--sheet", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--label", default="side_view")
    parser.add_argument("--left", default=0.34, type=float)
    parser.add_argument("--top", default=0.04, type=float)
    parser.add_argument("--right", default=0.66, type=float)
    parser.add_argument("--bottom", default=0.98, type=float)
    parser.add_argument("--background-threshold", default=42, type=int)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(args.sheet).convert("RGBA")
    crop_box = _fraction_box(sheet.size, args.left, args.top, args.right, args.bottom)
    crop = sheet.crop(crop_box)
    rgba = _remove_connected_light_background(crop, threshold=args.background_threshold)
    rgba = _tight_crop_with_padding(rgba, pad=28)

    side_path = args.output_dir / f"{args.label}.png"
    rgba.save(side_path)

    review = _make_review_sheet(sheet, crop_box, rgba, args.output_dir / f"{args.label}_review.png")
    manifest = {
        "route": "reference_faithful_design_sheet_side_view",
        "status": "design_sheet_candidate_needs_human_review",
        "source_sheet": str(args.sheet),
        "side_view": str(side_path),
        "review_sheet": str(review),
        "crop_box": list(crop_box),
        "background_threshold": args.background_threshold,
        "frame_size": {"width": rgba.width, "height": rgba.height},
        "identity_targets": [
            "sleepy pale anime face",
            "long white/silver hair",
            "glossy black hood/veil",
            "small gold forehead band/trim",
            "red collar at neck",
            "glossy black gothic cloth/leather outfit",
        ],
        "human_review_required": [
            "does not read as a different character",
            "saturation/value remains close to the design sheet",
            "side-view full body is usable for walk animation",
            "no extra character or weapon",
            "costume does not drift into generic knight armor",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.output_dir / "notes.md").write_text(_notes(manifest), encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), **manifest}, indent=2, ensure_ascii=False))


def _fraction_box(size: tuple[int, int], left: float, top: float, right: float, bottom: float) -> tuple[int, int, int, int]:
    width, height = size
    return (
        max(0, round(width * left)),
        max(0, round(height * top)),
        min(width, round(width * right)),
        min(height, round(height * bottom)),
    )


def _remove_connected_light_background(image: Image.Image, threshold: int) -> Image.Image:
    rgb = image.convert("RGB")
    rgba = image.convert("RGBA")
    background = _estimate_background(rgb)
    width, height = rgb.size
    rgb_pixels = rgb.load()
    out_pixels = rgba.load()
    visited: set[tuple[int, int]] = set()
    stack: list[tuple[int, int]] = []
    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height or (x, y) in visited:
            continue
        visited.add((x, y))
        red, green, blue = rgb_pixels[x, y]
        distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
        bright = min(red, green, blue) >= 188
        if distance > threshold or not bright:
            continue
        out_pixels[x, y] = (red, green, blue, 0)
        stack.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    return rgba


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    pixels = image.load()
    width, height = image.size
    samples = []
    for x in range(0, width, max(1, width // 12)):
        samples.append(pixels[x, 0])
        samples.append(pixels[x, height - 1])
    for y in range(0, height, max(1, height // 12)):
        samples.append(pixels[0, y])
        samples.append(pixels[width - 1, y])
    bright_samples = [sample for sample in samples if min(sample) >= 180]
    if bright_samples:
        samples = bright_samples
    return tuple(round(sum(sample[channel] for sample in samples) / len(samples)) for channel in range(3))


def _tight_crop_with_padding(image: Image.Image, pad: int) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        return image
    left, top, right, bottom = bbox
    box = (
        max(0, left - pad),
        max(0, top - pad),
        min(image.width, right + pad),
        min(image.height, bottom + pad),
    )
    return image.crop(box)


def _make_review_sheet(
    sheet: Image.Image,
    crop_box: tuple[int, int, int, int],
    side_view: Image.Image,
    output: Path,
) -> Path:
    preview = sheet.copy().convert("RGBA")
    draw = ImageDraw.Draw(preview)
    draw.rectangle(crop_box, outline=(255, 0, 0, 255), width=5)
    preview.thumbnail((900, 600))
    side_preview = _checkerboard(side_view.size)
    side_preview.alpha_composite(side_view)
    side_preview.thumbnail((360, 600))
    canvas = Image.new("RGBA", (preview.width + side_preview.width + 32, max(preview.height, side_preview.height)), (245, 245, 245, 255))
    canvas.alpha_composite(preview, (0, 0))
    canvas.alpha_composite(side_preview, (preview.width + 32, 0))
    canvas.save(output)
    return output


def _checkerboard(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, (235, 235, 235, 255))
    draw = ImageDraw.Draw(image)
    tile = 16
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            if (x // tile + y // tile) % 2 == 0:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(210, 210, 210, 255))
    return image


def _notes(manifest: dict[str, Any]) -> str:
    return f"""# Reference-Faithful Side View Candidate

- status: `{manifest['status']}`
- source sheet: `{manifest['source_sheet']}`
- side view: `{manifest['side_view']}`
- review sheet: `{manifest['review_sheet']}`
- frame size: `{manifest['frame_size']['width']}x{manifest['frame_size']['height']}`

This is a design-source candidate, not a walk animation yet.

Human review must confirm:

- same-character read before motion generation
- saturated black/white/red/gold palette is preserved
- side-view full body is usable for later walk-cycle work
- no weapon, duplicate character, or generic knight redesign
"""


if __name__ == "__main__":
    main()
