from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat


@dataclass(frozen=True)
class FrameQuality:
    index: int
    path: str
    foreground_coverage: float
    background_contamination_ratio: float
    dark_ratio: float
    duplicate_silhouette_area: float
    lower_body_blob_count: int
    mask_coverage: float
    upper_body_center_shift: float
    motion_delta_prev: float
    score: float
    hard_failure: bool
    issue_codes: tuple[str, ...]
    foreground_motion_delta_prev: float = 0.0
    foreground_mask_delta_prev: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SpanSelection:
    start_index: int
    end_index: int
    score: float
    hard_failures: int
    frame_indices: tuple[int, ...]
    frame_paths: tuple[str, ...]
    mean_motion_delta: float = 0.0
    mean_foreground_mask_delta: float = 0.0
    selection_penalties: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def analyze_frame_quality(
    path: Path,
    index: int,
    previous_path: Path | None = None,
    weak_threshold: int = 34,
    strong_threshold: int = 92,
) -> FrameQuality:
    image = Image.open(path).convert("RGB")
    weak_mask = foreground_by_background_distance(image, weak_threshold)
    strong_mask = foreground_by_background_distance(image, strong_threshold)
    protected_mask = _main_component_mask(ImageChops.lighter(_core_subject_mask(image), _light_subject_mask(image)))
    if protected_mask.getbbox() is None:
        protected_mask = _main_component_mask(strong_mask)
    artifact_protect_mask = grow_mask(protected_mask, 10)
    background_protect_mask = grow_mask(protected_mask, 24)
    artifact_mask = ImageChops.subtract(weak_mask, artifact_protect_mask)
    artifact_mask = artifact_mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(3))
    foreground_coverage = mask_coverage(strong_mask)
    duplicate_area = mask_coverage(artifact_mask)
    lower_blobs = count_lower_body_blobs(strong_mask)
    dark_ratio = _dark_ratio(image)
    background_contamination = _background_contamination_ratio(image, background_protect_mask)
    motion_delta = mean_delta(previous_path, path) if previous_path else 0.0
    foreground_motion_delta = foreground_normalized_delta(previous_path, path) if previous_path else 0.0
    upper_shift = _upper_body_center_shift(previous_path, strong_mask) if previous_path else 0.0

    issue_codes: list[str] = []
    if foreground_coverage < 0.025:
        issue_codes.append("foreground_too_small")
    if foreground_coverage > 0.35:
        issue_codes.append("foreground_too_large")
    if duplicate_area > 0.020:
        issue_codes.append("duplicate_silhouette_area_high")
    if lower_blobs > 2:
        issue_codes.append("lower_body_blob_count_high")
    if dark_ratio > 0.18:
        issue_codes.append("dark_frame_ratio_high")
    if background_contamination > 0.08:
        issue_codes.append("background_contamination_high")
    if upper_shift > 0.18:
        issue_codes.append("upper_body_center_shift_high")

    hard_failure = any(
        code in issue_codes
        for code in (
            "foreground_too_small",
            "foreground_too_large",
            "duplicate_silhouette_area_high",
            "lower_body_blob_count_high",
            "dark_frame_ratio_high",
        )
    )
    score = 1.0
    score -= min(0.45, duplicate_area * 5.0)
    score -= min(0.25, background_contamination * 1.8)
    score -= min(0.25, dark_ratio * 1.2)
    score -= min(0.20, upper_shift * 0.9)
    score -= max(0, lower_blobs - 2) * 0.18
    if foreground_coverage < 0.045:
        score -= 0.20
    if foreground_coverage > 0.24:
        score -= 0.20
    if hard_failure:
        score -= 0.35
    return FrameQuality(
        index=index,
        path=str(path),
        foreground_coverage=round(foreground_coverage, 5),
        background_contamination_ratio=round(background_contamination, 5),
        dark_ratio=round(dark_ratio, 5),
        duplicate_silhouette_area=round(duplicate_area, 5),
        lower_body_blob_count=lower_blobs,
        mask_coverage=round(mask_coverage(artifact_mask), 5),
        upper_body_center_shift=round(upper_shift, 5),
        motion_delta_prev=round(motion_delta, 3),
        score=round(max(0.0, score), 5),
        hard_failure=hard_failure,
        issue_codes=tuple(issue_codes),
        foreground_motion_delta_prev=round(foreground_motion_delta, 3),
    )


def prepare_analysis_frame(source: Path, output: Path, max_size: int) -> Path:
    if max_size <= 0:
        return source
    image = Image.open(source).convert("RGB")
    longest = max(image.size)
    if longest <= max_size:
        return source
    scale = max_size / longest
    output.parent.mkdir(parents=True, exist_ok=True)
    image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.BICUBIC,
    ).save(output)
    return output


def select_best_span(
    qualities: list[FrameQuality],
    span_length: int,
    allow_hard_failures: bool = False,
    min_mean_motion_delta: float = 0.0,
    max_mean_foreground_mask_delta: float | None = None,
    motion_metric: str = "global",
) -> SpanSelection:
    if not qualities:
        raise ValueError("qualities must not be empty")
    if span_length <= 0:
        raise ValueError("span_length must be positive")
    span_length = min(span_length, len(qualities))
    candidates: list[SpanSelection] = []
    for start in range(0, len(qualities) - span_length + 1):
        frames = qualities[start : start + span_length]
        hard_failures = sum(1 for frame in frames if frame.hard_failure)
        if hard_failures and not allow_hard_failures:
            continue
        motion_values = [_frame_motion_delta(frame, motion_metric) for frame in frames[1:]]
        continuity_penalty = _continuity_penalty(motion_values)
        mean_motion = _mean(motion_values)
        mean_mask_delta = _mean([frame.foreground_mask_delta_prev for frame in frames[1:]])
        selection_penalty, penalty_codes = _selection_penalty(
            mean_motion,
            mean_mask_delta,
            min_mean_motion_delta=min_mean_motion_delta,
            max_mean_foreground_mask_delta=max_mean_foreground_mask_delta,
        )
        score = sum(frame.score for frame in frames) / len(frames) - continuity_penalty - selection_penalty
        candidates.append(
            SpanSelection(
                start_index=frames[0].index,
                end_index=frames[-1].index,
                score=round(score, 5),
                hard_failures=hard_failures,
                frame_indices=tuple(frame.index for frame in frames),
                frame_paths=tuple(frame.path for frame in frames),
                mean_motion_delta=round(mean_motion, 3),
                mean_foreground_mask_delta=round(mean_mask_delta, 5),
                selection_penalties=tuple(penalty_codes),
            )
        )
    if candidates:
        return max(candidates, key=lambda span: (span.score, -span.hard_failures))

    fallback_start = max(
        range(0, len(qualities) - span_length + 1),
        key=lambda start: sum(frame.score for frame in qualities[start : start + span_length]),
    )
    frames = qualities[fallback_start : fallback_start + span_length]
    mean_motion = _mean([_frame_motion_delta(frame, motion_metric) for frame in frames[1:]])
    mean_mask_delta = _mean([frame.foreground_mask_delta_prev for frame in frames[1:]])
    selection_penalty, penalty_codes = _selection_penalty(
        mean_motion,
        mean_mask_delta,
        min_mean_motion_delta=min_mean_motion_delta,
        max_mean_foreground_mask_delta=max_mean_foreground_mask_delta,
    )
    return SpanSelection(
        start_index=frames[0].index,
        end_index=frames[-1].index,
        score=round(sum(frame.score for frame in frames) / len(frames) - selection_penalty, 5),
        hard_failures=sum(1 for frame in frames if frame.hard_failure),
        frame_indices=tuple(frame.index for frame in frames),
        frame_paths=tuple(frame.path for frame in frames),
        mean_motion_delta=round(mean_motion, 3),
        mean_foreground_mask_delta=round(mean_mask_delta, 5),
        selection_penalties=tuple(penalty_codes),
    )


def recommendation_table(qualities: list[FrameQuality]) -> list[dict[str, object]]:
    issue_counts: dict[str, int] = {}
    for quality in qualities:
        for issue_code in quality.issue_codes:
            issue_counts[issue_code] = issue_counts.get(issue_code, 0) + 1
    recommendations = []
    rules = {
        "foreground_too_small": "retake_with_full_body_framing",
        "foreground_too_large": "retake_with_more_canvas_margin",
        "duplicate_silhouette_area_high": "retrim_or_regenerate_before_img2img",
        "lower_body_blob_count_high": "reject_span_or_retake_pose_phase",
        "dark_frame_ratio_high": "retake_with_bright_plain_background",
        "background_contamination_high": "run_background_cleanup_or_retake",
        "upper_body_center_shift_high": "retrim_span_or_retake_identity_stability",
    }
    for issue_code, count in sorted(issue_counts.items()):
        recommendations.append(
            {
                "issue_code": issue_code,
                "count": count,
                "recommendation": rules.get(issue_code, "manual_review"),
            }
        )
    return recommendations


def foreground_by_background_distance(image: Image.Image, threshold: int) -> Image.Image:
    bg = estimate_background(image)
    out = Image.new("L", image.size, 0)
    pixels = image.load()
    mask = out.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            distance = abs(red - bg[0]) + abs(green - bg[1]) + abs(blue - bg[2])
            if distance >= threshold:
                mask[x, y] = 255
    return out


def estimate_background(image: Image.Image) -> tuple[int, int, int]:
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


def count_lower_body_blobs(mask: Image.Image) -> int:
    bbox = mask.getbbox()
    if bbox is None:
        return 0
    left, top, right, bottom = bbox
    lower_top = round(top + (bottom - top) * 0.58)
    foot_zone_top = round(top + (bottom - top) * 0.74)
    lower = Image.new("L", mask.size, 0)
    lower.paste(mask.crop((left, lower_top, right, bottom)), (left, lower_top))
    components = connected_components(lower, min_pixels=80)
    return sum(1 for component in components if _is_foot_like(component, lower_top, foot_zone_top))


def connected_components(mask: Image.Image, min_pixels: int) -> list[dict[str, object]]:
    width, height = mask.size
    pixels = mask.load()
    visited: set[tuple[int, int]] = set()
    components: list[dict[str, object]] = []
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
    return sorted(components, key=lambda item: int(item["pixels"]), reverse=True)


def grow_mask(mask: Image.Image, pixels: int) -> Image.Image:
    if pixels <= 0:
        return mask.copy()
    return mask.filter(ImageFilter.MaxFilter(pixels * 2 + 1))


def mask_coverage(mask: Image.Image) -> float:
    return round(ImageStat.Stat(mask).sum[0] / 255) / (mask.width * mask.height)


def mean_delta(left_path: Path | None, right_path: Path) -> float:
    if left_path is None:
        return 0.0
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB").resize(left.size, Image.Resampling.BICUBIC)
    pairs = zip(left.tobytes(), right.tobytes())
    return sum(abs(left_byte - right_byte) for left_byte, right_byte in pairs) / (left.width * left.height * 3)


def foreground_normalized_delta(left_path: Path | None, right_path: Path, threshold: int = 92) -> float:
    if left_path is None:
        return 0.0
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB").resize(left.size, Image.Resampling.BICUBIC)
    left_mask = foreground_by_background_distance(left, threshold)
    right_mask = foreground_by_background_distance(right, threshold)
    union = ImageChops.lighter(left_mask, right_mask)
    bbox = union.getbbox()
    if bbox is None:
        return mean_delta(left_path, right_path)
    left_x, top_y, right_x, bottom_y = bbox
    pad = max(4, round(min(left.width, left.height) * 0.025))
    crop_box = (
        max(0, left_x - pad),
        max(0, top_y - pad),
        min(left.width, right_x + pad),
        min(left.height, bottom_y + pad),
    )
    left_crop = left.crop(crop_box)
    right_crop = right.crop(crop_box)
    pairs = zip(left_crop.tobytes(), right_crop.tobytes())
    return sum(abs(left_byte - right_byte) for left_byte, right_byte in pairs) / (
        left_crop.width * left_crop.height * 3
    )


def _frame_motion_delta(frame: FrameQuality, motion_metric: str) -> float:
    if motion_metric == "global":
        return frame.motion_delta_prev
    if motion_metric == "foreground":
        return frame.foreground_motion_delta_prev
    if motion_metric == "max":
        return max(frame.motion_delta_prev, frame.foreground_motion_delta_prev)
    raise ValueError(f"Unknown motion metric: {motion_metric}")


def _main_component_mask(mask: Image.Image) -> Image.Image:
    components = connected_components(mask, min_pixels=48)
    out = Image.new("L", mask.size, 0)
    if not components:
        return out
    pixels = out.load()
    for x, y in components[0]["points"]:  # type: ignore[index]
        pixels[x, y] = 255
    return out


def _core_subject_mask(image: Image.Image) -> Image.Image:
    out = Image.new("L", image.size, 0)
    pixels = image.load()
    mask = out.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            channel_range = max(red, green, blue) - min(red, green, blue)
            if red + green + blue < 520 or channel_range > 80:
                mask[x, y] = 255
    return out


def _light_subject_mask(image: Image.Image) -> Image.Image:
    out = Image.new("L", image.size, 0)
    bg = estimate_background(image)
    pixels = image.load()
    mask = out.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            distance = abs(red - bg[0]) + abs(green - bg[1]) + abs(blue - bg[2])
            warm_light_subject = red + green + blue >= 540 and red >= green and red >= blue + 12
            if distance >= 34 and warm_light_subject:
                mask[x, y] = 255
    return out


def _background_contamination_ratio(image: Image.Image, protected_mask: Image.Image) -> float:
    fg = grow_mask(protected_mask, 12)
    bg = estimate_background(image)
    pixels = image.load()
    mask = fg.load()
    contaminated = 0
    background_pixels = 0
    for y in range(image.height):
        for x in range(image.width):
            if mask[x, y] > 0:
                continue
            background_pixels += 1
            red, green, blue = pixels[x, y]
            distance = abs(red - bg[0]) + abs(green - bg[1]) + abs(blue - bg[2])
            if distance > 45:
                contaminated += 1
    return contaminated / max(1, background_pixels)


def _dark_ratio(image: Image.Image) -> float:
    pixels = image.load()
    dark = 0
    total = image.width * image.height
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            if red + green + blue < 150:
                dark += 1
    return dark / total


def _upper_body_center_shift(previous_path: Path | None, current_mask: Image.Image) -> float:
    if previous_path is None:
        return 0.0
    previous = Image.open(previous_path).convert("RGB")
    previous_mask = foreground_by_background_distance(previous, 92)
    previous_center = _upper_body_center(previous_mask)
    current_center = _upper_body_center(current_mask)
    if previous_center is None or current_center is None:
        return 1.0
    dx = current_center[0] - previous_center[0]
    dy = current_center[1] - previous_center[1]
    return (dx * dx + dy * dy) ** 0.5


def _upper_body_center(mask: Image.Image) -> tuple[float, float] | None:
    bbox = mask.getbbox()
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    upper_bottom = round(top + (bottom - top) * 0.55)
    cropped = mask.crop((left, top, right, upper_bottom))
    if cropped.getbbox() is None:
        return None
    pixels = cropped.load()
    xs = []
    ys = []
    for y in range(cropped.height):
        for x in range(cropped.width):
            if pixels[x, y] > 0:
                xs.append(left + x)
                ys.append(top + y)
    if not xs:
        return None
    return sum(xs) / len(xs) / mask.width, sum(ys) / len(ys) / mask.height


def _is_foot_like(component: dict[str, object], lower_top: int, foot_zone_top: int) -> bool:
    x0, y0, x1, y1 = component["bbox"]  # type: ignore[misc]
    if y1 < lower_top:
        return False
    if y1 < foot_zone_top:
        return False
    return (x1 - x0) >= 8 and (y1 - y0) >= 8


def _continuity_penalty(deltas: list[float]) -> float:
    if len(deltas) < 2:
        return 0.0
    mean = sum(deltas) / len(deltas)
    variance = sum((value - mean) ** 2 for value in deltas) / len(deltas)
    return min(0.18, (variance**0.5) / 85.0)


def _selection_penalty(
    mean_motion_delta: float,
    mean_foreground_mask_delta: float,
    *,
    min_mean_motion_delta: float,
    max_mean_foreground_mask_delta: float | None,
) -> tuple[float, list[str]]:
    penalty = 0.0
    codes: list[str] = []
    if min_mean_motion_delta > 0 and mean_motion_delta < min_mean_motion_delta:
        shortfall = (min_mean_motion_delta - mean_motion_delta) / min_mean_motion_delta
        penalty += min(0.35, shortfall * 0.35)
        codes.append("mean_motion_delta_too_low")
    if max_mean_foreground_mask_delta and max_mean_foreground_mask_delta > 0:
        if mean_foreground_mask_delta > max_mean_foreground_mask_delta:
            excess = (mean_foreground_mask_delta - max_mean_foreground_mask_delta) / max_mean_foreground_mask_delta
            penalty += min(0.25, excess * 0.25)
            codes.append("foreground_mask_temporal_delta_high")
    return penalty, codes


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
