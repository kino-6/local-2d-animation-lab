from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


@dataclass(frozen=True)
class StartFrameReport:
    source: str
    output: str
    status: str
    component_count: int
    main_bbox: tuple[int, int, int, int] | None
    main_coverage: float
    largest_secondary_ratio: float
    issue_codes: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.main_bbox is not None:
            data["main_bbox"] = list(self.main_bbox)
        return data


def prepare_clean_start_frame(
    source: Path,
    output: Path,
    *,
    width: int = 1024,
    height: int = 1024,
    threshold: int = 42,
    min_component_pixels: int = 80,
    padding_ratio: float = 0.09,
    max_secondary_ratio: float = 0.30,
    target_fill: float = 0.88,
) -> StartFrameReport:
    image = Image.open(source).convert("RGBA")
    flattened = _flatten_on_white(image)
    mask = _foreground_mask(flattened.convert("RGB"), threshold)
    components = _connected_components(mask, min_pixels=min_component_pixels)
    issue_codes: list[str] = []
    notes: list[str] = []
    if not components:
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (width, height), (255, 255, 255)).save(output)
        return StartFrameReport(
            source=str(source),
            output=str(output),
            status="rejected",
            component_count=0,
            main_bbox=None,
            main_coverage=0.0,
            largest_secondary_ratio=0.0,
            issue_codes=["missing_foreground"],
            notes=["No foreground component was detected."],
        )

    main = components[0]
    secondary_ratio = components[1]["pixels"] / main["pixels"] if len(components) > 1 else 0.0
    if len(components) > 1:
        issue_codes.append("extra_foreground_components_removed")
        notes.append("Only the largest foreground component is kept for the Wan start frame.")
    if secondary_ratio > max_secondary_ratio:
        issue_codes.append("large_secondary_component")

    crop_box = _pad_bbox(main["bbox"], flattened.size, padding_ratio)
    crop = flattened.crop(crop_box)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    max_w = round(width * target_fill)
    max_h = round(height * target_fill)
    crop.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    canvas.paste(crop, ((width - crop.width) // 2, (height - crop.height) // 2))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)

    status = "prepared_with_warnings" if issue_codes else "prepared"
    return StartFrameReport(
        source=str(source),
        output=str(output),
        status=status,
        component_count=len(components),
        main_bbox=main["bbox"],
        main_coverage=round(main["pixels"] / (flattened.width * flattened.height), 5),
        largest_secondary_ratio=round(secondary_ratio, 5),
        issue_codes=issue_codes,
        notes=notes,
    )


def make_character_mask(
    source: Path,
    output: Path,
    *,
    threshold: int = 42,
    grow: int = 11,
    blur_radius: int = 3,
) -> Path:
    image = Image.open(source).convert("RGBA")
    flattened = _flatten_on_white(image)
    mask = _foreground_mask(flattened.convert("RGB"), threshold)
    components = _connected_components(mask, min_pixels=80)
    if components:
        mask = Image.new("L", flattened.size, 0)
        pixels = mask.load()
        for x, y in components[0]["points"]:
            pixels[x, y] = 255
    if grow > 0:
        from PIL import ImageFilter

        mask = mask.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    if blur_radius > 0:
        from PIL import ImageFilter

        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))
    output.parent.mkdir(parents=True, exist_ok=True)
    mask.save(output)
    return output


def make_start_frame_debug_sheet(source: Path, cleaned: Path, output: Path) -> Path:
    source_image = Image.open(source).convert("RGB")
    cleaned_image = Image.open(cleaned).convert("RGB")
    thumb_w = 420
    thumb_h = 420
    sheet = Image.new("RGB", (thumb_w * 2, thumb_h + 24), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate((("source", source_image), ("cleaned", cleaned_image))):
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = index * thumb_w + (thumb_w - image.width) // 2
        y = (thumb_h - image.height) // 2
        sheet.paste(image, (x, y))
        draw.text((index * thumb_w + 4, thumb_h + 4), label, fill=(20, 20, 20))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return output


def _flatten_on_white(image: Image.Image) -> Image.Image:
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    return background.convert("RGB")


def _foreground_mask(image: Image.Image, threshold: int) -> Image.Image:
    background = _estimate_background(image)
    out = Image.new("L", image.size, 0)
    pixels = image.load()
    mask = out.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            if distance >= threshold:
                mask[x, y] = 255
    return out


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
    return sorted(components, key=lambda item: item["pixels"], reverse=True)


def _pad_bbox(
    bbox: tuple[int, int, int, int],
    size: tuple[int, int],
    padding_ratio: float,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    width, height = size
    pad_x = round((right - left) * padding_ratio)
    pad_y = round((bottom - top) * padding_ratio)
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(width, right + pad_x),
        min(height, bottom + pad_y),
    )
