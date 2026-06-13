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
    profile_detail_ratio: float
    background_contamination_ratio: float
    lower_body_readiness: dict[str, Any]
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
    require_profile_detail: bool = False,
    require_lower_body_readiness: bool = False,
    min_profile_detail_ratio: float = 0.012,
    max_background_contamination_ratio: float = 0.08,
    min_foot_separation_ratio: float = 0.18,
    min_foot_zone_coverage: float = 0.018,
    min_lower_leg_visibility_ratio: float = 0.018,
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
            profile_detail_ratio=0.0,
            background_contamination_ratio=0.0,
            lower_body_readiness={},
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
    residue_codes = _secondary_residue_issue_codes(flattened, components[1:])
    issue_codes.extend(code for code in residue_codes if code not in issue_codes)
    if "guide_or_panel_residue" in residue_codes:
        notes.append("Thin colored guide/panel residue was detected outside the main character.")

    profile_detail = _profile_detail_ratio(flattened, main["bbox"])
    if require_profile_detail and profile_detail < min_profile_detail_ratio:
        issue_codes.append("possible_back_view_or_missing_profile_detail")
        notes.append("Head/profile detail is too weak for a reliable side-view start frame.")

    background_contamination = _background_contamination_ratio(flattened, mask, main["points"])
    if background_contamination > max_background_contamination_ratio:
        issue_codes.append("background_contamination_high")
        notes.append("Non-character background contamination is too high for Wan start-frame input.")

    lower_body = _lower_body_readiness(flattened.size, main["bbox"], main["points"])
    if require_lower_body_readiness:
        lower_body_codes = _lower_body_issue_codes(
            lower_body,
            min_foot_separation_ratio=min_foot_separation_ratio,
            min_foot_zone_coverage=min_foot_zone_coverage,
            min_lower_leg_visibility_ratio=min_lower_leg_visibility_ratio,
        )
        issue_codes.extend(code for code in lower_body_codes if code not in issue_codes)
        if lower_body_codes:
            notes.append("Lower-body/foot readability is too weak for a walk-ready start frame.")

    crop_box = _pad_bbox(main["bbox"], flattened.size, padding_ratio)
    crop = flattened.crop(crop_box)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    max_w = round(width * target_fill)
    max_h = round(height * target_fill)
    crop.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    canvas.paste(crop, ((width - crop.width) // 2, (height - crop.height) // 2))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)

    reject_codes = {
        "large_secondary_component",
        "guide_or_panel_residue",
        "background_contamination_high",
        "possible_back_view_or_missing_profile_detail",
        "feet_not_separated",
        "shoes_unreadable",
        "lower_legs_occluded",
        "foot_zone_merged",
    }
    status = "rejected" if reject_codes.intersection(issue_codes) else "prepared_with_warnings" if issue_codes else "prepared"
    return StartFrameReport(
        source=str(source),
        output=str(output),
        status=status,
        component_count=len(components),
        main_bbox=main["bbox"],
        main_coverage=round(main["pixels"] / (flattened.width * flattened.height), 5),
        largest_secondary_ratio=round(secondary_ratio, 5),
        profile_detail_ratio=round(profile_detail, 5),
        background_contamination_ratio=round(background_contamination, 5),
        lower_body_readiness=lower_body,
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


def _secondary_residue_issue_codes(image: Image.Image, secondary_components: list[dict[str, Any]]) -> list[str]:
    codes: list[str] = []
    pixels = image.load()
    for component in secondary_components:
        left, top, right, bottom = component["bbox"]
        width = right - left
        height = bottom - top
        touches_border = left <= 3 or top <= 3 or right >= image.width - 3 or bottom >= image.height - 3
        long_thin = width >= image.width * 0.32 and height <= image.height * 0.04
        tall_thin = height >= image.height * 0.32 and width <= image.width * 0.04
        colored = 0
        sampled = 0
        for x, y in component["points"][:: max(1, len(component["points"]) // 200)]:
            red, green, blue = pixels[x, y]
            channel_range = max(red, green, blue) - min(red, green, blue)
            if channel_range > 70 and max(red, green, blue) > 130:
                colored += 1
            sampled += 1
        colored_ratio = colored / max(1, sampled)
        if (touches_border or long_thin or tall_thin) and colored_ratio > 0.35:
            codes.append("guide_or_panel_residue")
            break
    return codes


def _profile_detail_ratio(image: Image.Image, bbox: tuple[int, int, int, int]) -> float:
    left, top, right, bottom = bbox
    head_bottom = top + max(1, round((bottom - top) * 0.24))
    head = image.crop((left, top, right, head_bottom)).convert("RGB")
    pixels = head.load()
    detail = 0
    total = head.width * head.height
    for y in range(head.height):
        for x in range(head.width):
            red, green, blue = pixels[x, y]
            near_white = red > 238 and green > 238 and blue > 238
            skin_like = (
                not near_white
                and red > 135
                and green > 80
                and blue > 55
                and red >= green
                and green >= blue * 0.72
            )
            warm_face_shadow = red > green + 18 and green > blue + 8 and red + green + blue > 260
            if skin_like or warm_face_shadow:
                detail += 1
    return detail / max(1, total)


def _background_contamination_ratio(
    image: Image.Image,
    foreground_mask: Image.Image,
    main_points: list[tuple[int, int]],
) -> float:
    bg = _estimate_background(image)
    main_mask = Image.new("L", image.size, 0)
    main_pixels = main_mask.load()
    for x, y in main_points:
        main_pixels[x, y] = 255
    from PIL import ImageFilter

    protected = main_mask.filter(ImageFilter.MaxFilter(19))
    fg = foreground_mask.load()
    protected_pixels = protected.load()
    pixels = image.load()
    contaminated = 0
    background = 0
    for y in range(image.height):
        for x in range(image.width):
            if protected_pixels[x, y] > 0:
                continue
            background += 1
            red, green, blue = pixels[x, y]
            distance = abs(red - bg[0]) + abs(green - bg[1]) + abs(blue - bg[2])
            if fg[x, y] > 0 or distance > 55:
                contaminated += 1
    return contaminated / max(1, background)


def _lower_body_readiness(
    size: tuple[int, int],
    bbox: tuple[int, int, int, int],
    main_points: list[tuple[int, int]],
) -> dict[str, Any]:
    canvas_w, canvas_h = size
    left, top, right, bottom = bbox
    width = max(1, right - left)
    height = max(1, bottom - top)
    main_mask = Image.new("L", size, 0)
    pixels = main_mask.load()
    for x, y in main_points:
        pixels[x, y] = 255

    foot_top = top + round(height * 0.76)
    leg_top = top + round(height * 0.55)
    leg_bottom = top + round(height * 0.88)
    foot_mask = _crop_mask_region(main_mask, (left, foot_top, right, bottom))
    leg_mask = _crop_mask_region(main_mask, (left, leg_top, right, leg_bottom))
    foot_components = _connected_components(foot_mask, min_pixels=max(12, round(width * height * 0.00035)))
    leg_components = _connected_components(leg_mask, min_pixels=max(16, round(width * height * 0.00045)))
    foot_boxes = [component["bbox"] for component in foot_components]
    foot_centers = [((box[0] + box[2]) / 2.0) for box in foot_boxes]
    foot_separation = 0.0
    if len(foot_centers) >= 2:
        foot_separation = (max(foot_centers) - min(foot_centers)) / width
    foot_bbox_width = 0.0
    if foot_boxes:
        foot_bbox_width = (max(box[2] for box in foot_boxes) - min(box[0] for box in foot_boxes)) / width
    foot_zone_area = max(1, foot_mask.width * foot_mask.height)
    leg_zone_area = max(1, leg_mask.width * leg_mask.height)
    foot_pixels = sum(int(component["pixels"]) for component in foot_components)
    leg_pixels = sum(int(component["pixels"]) for component in leg_components[:2])
    return {
        "foot_component_count": len(foot_components),
        "lower_leg_component_count": len(leg_components),
        "foot_separation_ratio": round(foot_separation, 5),
        "foot_zone_coverage": round(foot_pixels / foot_zone_area, 5),
        "foot_zone_width_ratio": round(foot_bbox_width, 5),
        "lower_leg_visibility_ratio": round(leg_pixels / leg_zone_area, 5),
        "foot_zone_box": [left, foot_top, right, bottom],
        "lower_leg_zone_box": [left, leg_top, right, leg_bottom],
        "canvas_size": [canvas_w, canvas_h],
    }


def _lower_body_issue_codes(
    metrics: dict[str, Any],
    *,
    min_foot_separation_ratio: float,
    min_foot_zone_coverage: float,
    min_lower_leg_visibility_ratio: float,
) -> list[str]:
    codes: list[str] = []
    foot_count = int(metrics.get("foot_component_count", 0) or 0)
    leg_count = int(metrics.get("lower_leg_component_count", 0) or 0)
    foot_separation = float(metrics.get("foot_separation_ratio", 0.0) or 0.0)
    foot_coverage = float(metrics.get("foot_zone_coverage", 0.0) or 0.0)
    foot_width = float(metrics.get("foot_zone_width_ratio", 0.0) or 0.0)
    lower_leg_visibility = float(metrics.get("lower_leg_visibility_ratio", 0.0) or 0.0)
    if foot_count < 2 or foot_separation < min_foot_separation_ratio:
        codes.append("feet_not_separated")
    if foot_coverage < min_foot_zone_coverage:
        codes.append("shoes_unreadable")
    if foot_count == 1 and foot_width > 0.34:
        codes.append("foot_zone_merged")
    if lower_leg_visibility < min_lower_leg_visibility_ratio or (leg_count < 2 and foot_count < 2):
        codes.append("lower_legs_occluded")
    return codes


def _crop_mask_region(mask: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = box
    region = Image.new("L", mask.size, 0)
    if right <= left or bottom <= top:
        return region
    region.paste(mask.crop(box), (left, top))
    return region


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
