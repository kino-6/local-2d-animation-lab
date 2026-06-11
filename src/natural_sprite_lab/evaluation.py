from __future__ import annotations

from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from PIL import Image, ImageStat


def evaluate_animation(
    frame_paths: list[Path],
    spec: Any | None = None,
    effect_frame_paths: list[Path] | None = None,
    backend_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Local heuristic evaluation for generated animation runs."""
    frame_reports = [_evaluate_frame(path) for path in frame_paths]
    if not frame_reports:
        return {"score": 0.0, "issues": ["no frames"], "frames": []}

    areas = [report["foreground_area_ratio"] for report in frame_reports]
    heights = [report["bbox_height_ratio"] for report in frame_reports]
    centers = [report["center_x_ratio"] for report in frame_reports]
    color_distances = [
        _color_distance(frame_reports[index]["mean_rgb"], frame_reports[index - 1]["mean_rgb"])
        for index in range(1, len(frame_reports))
    ]
    pose_deltas = [
        abs(frame_reports[index]["center_x_ratio"] - frame_reports[index - 1]["center_x_ratio"])
        + abs(frame_reports[index]["bbox_height_ratio"] - frame_reports[index - 1]["bbox_height_ratio"])
        for index in range(1, len(frame_reports))
    ]

    issues: list[str] = []
    issue_codes: set[str] = set()
    if max(report["component_count"] for report in frame_reports) > 2:
        issues.append("possible multi-character or fragmented foreground")
        issue_codes.add("multiple_or_fragmented_foreground")
    if pstdev(centers) > 0.16:
        issues.append("character center drifts too much between frames")
        issue_codes.add("center_drift")
    if pstdev(heights) > 0.12:
        issues.append("character scale changes too much between frames")
        issue_codes.add("scale_drift")
    if mean(color_distances or [0.0]) > 60:
        issues.append("character colors are inconsistent between frames")
        issue_codes.add("color_drift")
    if max(areas) < 0.08:
        issues.append("foreground character is too small")
        issue_codes.add("missing_or_tiny_foreground")
    if max(pose_deltas or [0.0]) < 0.04:
        issues.append("motion variation is weak")
        issue_codes.add("weak_motion")
    if max(report["edge_foreground_ratio"] for report in frame_reports) > 0.08:
        issues.append("foreground touches canvas edges or background is contaminated")
        issue_codes.add("background_contamination")

    score = 1.0
    score -= min(0.35, pstdev(centers) * 1.2)
    score -= min(0.30, pstdev(heights) * 1.2)
    score -= min(0.25, mean(color_distances or [0.0]) / 260)
    score -= 0.08 * sum(max(0, report["component_count"] - 1) for report in frame_reports) / len(frame_reports)
    score += min(0.12, max(pose_deltas or [0.0]))
    semantic = _evaluate_semantics(frame_reports, spec, effect_frame_paths or [])
    viability = _evaluate_animation_viability(frame_paths, frame_reports, spec, backend_metadata or {})
    template_match = _evaluate_pose_template_match(spec, backend_metadata or {})
    if semantic:
        score -= max(0.0, 1.0 - float(semantic["score"])) * 0.20
        issues.extend(str(issue) for issue in semantic["issues"])
        issue_codes.update(str(code) for code in semantic.get("issue_codes", []))
    score -= max(0.0, 1.0 - float(viability["score"])) * 0.25
    issues.extend(str(issue) for issue in viability["issues"])
    issue_codes.update(str(code) for code in viability.get("issue_codes", []))
    score -= max(0.0, 1.0 - float(template_match["score"])) * 0.15
    issues.extend(str(issue) for issue in template_match["issues"])
    issue_codes.update(str(code) for code in template_match.get("issue_codes", []))
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 3),
        "issues": issues,
        "issue_codes": sorted(issue_codes),
        "summary": {
            "mean_foreground_area_ratio": round(mean(areas), 3),
            "center_x_stdev": round(pstdev(centers), 3),
            "height_stdev": round(pstdev(heights), 3),
            "mean_color_distance": round(mean(color_distances or [0.0]), 3),
            "max_pose_delta": round(max(pose_deltas or [0.0]), 3),
        },
        "semantic": semantic,
        "animation_viability": viability,
        "pose_template_match": template_match,
        "frames": frame_reports,
    }


def _evaluate_frame(path: Path) -> dict[str, Any]:
    image = Image.open(path).convert("RGBA")
    mask = _foreground_mask(image)
    bbox = mask.getbbox()
    if not bbox:
        return {
            "path": str(path),
            "foreground_area_ratio": 0.0,
            "bbox_width_ratio": 0.0,
            "bbox_height_ratio": 0.0,
            "center_x_ratio": 0.5,
            "mean_rgb": [0, 0, 0],
            "component_count": 0,
            "edge_foreground_ratio": 0.0,
        }

    left, top, right, bottom = bbox
    width, height = image.size
    foreground = image.crop(bbox)
    foreground_mask = mask.crop(bbox)
    stat = ImageStat.Stat(foreground.convert("RGB"), foreground_mask)
    area = sum(mask.histogram()[1:])
    return {
        "path": str(path),
        "foreground_area_ratio": round(area / (width * height), 4),
        "bbox_width_ratio": round((right - left) / width, 4),
        "bbox_height_ratio": round((bottom - top) / height, 4),
        "center_x_ratio": round(((left + right) / 2) / width, 4),
        "mean_rgb": [round(value) for value in stat.mean],
        "component_count": _component_count(mask, min_pixels=max(80, int(width * height * 0.002))),
        "edge_foreground_ratio": round(_edge_foreground_ratio(mask), 4),
    }


def _foreground_mask(image: Image.Image) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    samples = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
    ]
    background = tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))
    mask = Image.new("L", image.size, 0)
    mask_pixels = mask.load()
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            if alpha > 10 and distance > 58:
                mask_pixels[x, y] = 255
    return mask


def _component_count(mask: Image.Image, min_pixels: int) -> int:
    width, height = mask.size
    pixels = mask.load()
    seen: set[tuple[int, int]] = set()
    count = 0
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if pixels[x, y] == 0 or (x, y) in seen:
                continue
            size = _flood(mask, x, y, seen)
            if size >= min_pixels:
                count += 1
    return count


def _edge_foreground_ratio(mask: Image.Image) -> float:
    width, height = mask.size
    pixels = mask.load()
    border = max(2, min(width, height) // 32)
    total = 0
    edge = 0
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0:
                continue
            total += 1
            if x < border or y < border or x >= width - border or y >= height - border:
                edge += 1
    return edge / total if total else 0.0


def _flood(mask: Image.Image, start_x: int, start_y: int, seen: set[tuple[int, int]]) -> int:
    width, height = mask.size
    pixels = mask.load()
    stack = [(start_x, start_y)]
    size = 0
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height or (x, y) in seen or pixels[x, y] == 0:
            continue
        seen.add((x, y))
        size += 4
        stack.extend([(x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2)])
    return size


def _color_distance(left: list[int], right: list[int]) -> float:
    return sum(abs(left[index] - right[index]) for index in range(3)) / 3


def _evaluate_semantics(
    frame_reports: list[dict[str, Any]],
    spec: Any | None,
    effect_frame_paths: list[Path],
) -> dict[str, Any]:
    if spec is None:
        return {}
    action = getattr(getattr(spec, "action", ""), "value", getattr(spec, "action", ""))
    frame_plan = list(getattr(spec, "frame_plan", []) or [])
    if action not in {"attack", "hit"} or not frame_plan:
        return {}

    active_frames = [
        index
        for index, frame in enumerate(frame_plan)
        if "active_frame" in frame.get("semantic_tags", []) or "reaction_frame" in frame.get("semantic_tags", [])
    ]
    effect_non_empty = _effect_non_empty(effect_frame_paths)
    issues: list[str] = []
    issue_codes: set[str] = set()
    if not active_frames:
        issues.append("semantic metadata has no active action frames")
        issue_codes.add("pose_action_mismatch")
    if effect_frame_paths and not any(effect_non_empty):
        issues.append("semantic action cue layers are empty")
        issue_codes.add("weapon_or_hit_cue_missing")
    if effect_frame_paths and active_frames:
        missing = [index for index in active_frames if index < len(effect_non_empty) and not effect_non_empty[index]]
        if missing:
            issues.append(f"semantic action cue missing on active frames: {missing}")
            issue_codes.add("weapon_or_hit_cue_missing")

    pose_delta = _max_report_delta(frame_reports)
    if action == "hit" and pose_delta < 0.045:
        issues.append("hit semantic motion is too weak")
        issue_codes.add("weak_hit_recoil")
    if action == "attack" and pose_delta < 0.035:
        issues.append("attack semantic motion is too weak")
        issue_codes.add("weak_attack_motion")

    variant = frame_plan[0].get("action_variant", action)
    if action == "attack" and variant in {"sword", "axe"} and not active_frames:
        issues.append(f"{variant} attack has no active weapon phase")
        issue_codes.add("weapon_phase_missing")
    if action == "attack" and variant == "bow":
        if not active_frames:
            issues.append("bow attack has no draw or release phase")
            issue_codes.add("bow_phase_missing")
        if pose_delta < 0.045:
            issues.append("bow draw or release motion is weak")
            issue_codes.add("bow_string_arrow_breakage_likely")

    score = 1.0
    score -= 0.22 * len(issues)
    if effect_frame_paths and active_frames:
        active_with_effect = sum(1 for index in active_frames if index < len(effect_non_empty) and effect_non_empty[index])
        score += min(0.1, active_with_effect / max(1, len(active_frames)) * 0.1)
    score = max(0.0, min(1.0, score))
    return {
        "score": round(score, 3),
        "issues": issues,
        "issue_codes": sorted(issue_codes),
        "action": action,
        "variant": variant,
        "active_frames": active_frames,
        "effect_non_empty": effect_non_empty,
    }


def _effect_non_empty(effect_frame_paths: list[Path]) -> list[bool]:
    values: list[bool] = []
    for path in effect_frame_paths:
        if not path.exists():
            values.append(False)
            continue
        image = Image.open(path).convert("RGBA")
        alpha = image.getchannel("A")
        values.append(bool(alpha.getbbox()))
    return values


def _max_report_delta(frame_reports: list[dict[str, Any]]) -> float:
    if len(frame_reports) < 2:
        return 0.0
    return max(
        abs(frame_reports[index]["center_x_ratio"] - frame_reports[index - 1]["center_x_ratio"])
        + abs(frame_reports[index]["bbox_height_ratio"] - frame_reports[index - 1]["bbox_height_ratio"])
        for index in range(1, len(frame_reports))
    )


def _evaluate_animation_viability(
    frame_paths: list[Path],
    frame_reports: list[dict[str, Any]],
    spec: Any | None,
    backend_metadata: dict[str, Any],
) -> dict[str, Any]:
    action = getattr(getattr(spec, "action", ""), "value", getattr(spec, "action", ""))
    backend_name = ""
    if spec is not None:
        backend_name = str(getattr(spec, "director_metadata", {}).get("backend_name", ""))
    frame_deltas = _frame_alpha_deltas(frame_paths)
    max_pose_delta = _max_report_delta(frame_reports)
    center_stdev = pstdev([report["center_x_ratio"] for report in frame_reports]) if frame_reports else 0.0
    height_stdev = pstdev([report["bbox_height_ratio"] for report in frame_reports]) if frame_reports else 0.0
    loop_delta = _loop_delta(frame_paths) if frame_paths else 1.0
    rigged = _looks_rigged(frame_paths)
    motion_economy = _motion_economy(backend_metadata)

    issues: list[str] = []
    issue_codes: set[str] = set()
    if len(frame_paths) < 4:
        issues.append("animation has too few frames for viability review")
        issue_codes.add("too_few_frames")
    if max_pose_delta < 0.035 and action != "idle":
        issues.append("animation motion amplitude is too low")
        issue_codes.add("weak_motion")
    if center_stdev > 0.20:
        issues.append("animation root motion drifts too much")
        issue_codes.add("center_drift")
    if height_stdev > 0.14:
        issues.append("animation silhouette height is unstable")
        issue_codes.add("scale_drift")
    if action in {"walk", "idle"} and loop_delta > 0.12:
        issues.append("loop closure is weak")
        issue_codes.add("weak_loop_closure")
    if not rigged and mean(frame_deltas or [0.0]) > 0.16:
        issues.append("frame-to-frame changes look like independent redraws")
        issue_codes.add("frame_jitter")
    issues.extend(motion_economy["issues"])
    issue_codes.update(str(code) for code in motion_economy.get("issue_codes", []))

    score = 1.0
    score -= min(0.25, center_stdev)
    score -= min(0.22, height_stdev * 1.2)
    score -= min(0.25, loop_delta if action in {"walk", "idle"} else 0.0)
    if max_pose_delta < 0.035 and action != "idle":
        score -= 0.22
    if rigged:
        score += 0.08
    score += min(0.08, float(motion_economy["score"]) * 0.08)
    score -= min(0.18, max(0.0, mean(frame_deltas or [0.0]) - 0.18))
    score = max(0.0, min(1.0, score))
    return {
        "score": round(score, 3),
        "issues": issues,
        "issue_codes": sorted(issue_codes),
        "summary": {
            "mean_frame_delta": round(mean(frame_deltas or [0.0]), 4),
            "max_frame_delta": round(max(frame_deltas or [0.0]), 4),
            "loop_delta": round(loop_delta, 4),
            "max_pose_delta": round(max_pose_delta, 4),
            "center_x_stdev": round(center_stdev, 4),
            "height_stdev": round(height_stdev, 4),
            "rigged_like": rigged,
            "backend_hint": backend_name,
            "motion_economy": motion_economy,
        },
    }


def _motion_economy(backend_metadata: dict[str, Any]) -> dict[str, Any]:
    style = str(backend_metadata.get("motion_style", ""))
    source_count = int(backend_metadata.get("source_frame_count", 0) or 0)
    sampled_indices = list(backend_metadata.get("sampled_indices", []) or [])
    rig_frames = list(backend_metadata.get("rig_frames", []) or [])
    active_counts = [
        len(frame.get("active_parts", []))
        for frame in rig_frames
        if isinstance(frame, dict) and isinstance(frame.get("active_parts", []), list)
    ]
    mean_active = mean(active_counts or [0.0])

    issues: list[str] = []
    issue_codes: set[str] = set()
    if style == "sfc" and source_count < 60:
        issues.append("SFC-style motion should be planned from at least 60 source frames")
        issue_codes.add("insufficient_source_frames")
    if style == "sfc" and mean_active > 4.0:
        issues.append("too many body parts are marked active for SFC-style limited animation")
        issue_codes.add("too_many_active_parts")
    if sampled_indices and sampled_indices != sorted(sampled_indices):
        issues.append("sampled source frames are not monotonic")
        issue_codes.add("non_monotonic_sampling")

    score = 1.0
    if style != "sfc":
        score -= 0.25
    if source_count >= 120:
        score += 0.08
    elif source_count >= 60:
        score += 0.04
    score -= 0.08 * len(issues)
    score = max(0.0, min(1.0, score))
    return {
        "score": round(score, 3),
        "style": style,
        "source_frame_count": source_count,
        "sampled_indices": sampled_indices,
        "mean_active_part_count": round(mean_active, 3),
        "issues": issues,
        "issue_codes": sorted(issue_codes),
    }


def _evaluate_pose_template_match(spec: Any | None, backend_metadata: dict[str, Any]) -> dict[str, Any]:
    if spec is None:
        return {"score": 1.0, "issues": [], "issue_codes": []}

    expected = _expected_template_name(spec)
    actual = str(backend_metadata.get("pose_template_name", "") or "")
    issues: list[str] = []
    issue_codes: set[str] = set()
    if actual and expected and actual != expected:
        issues.append(f"pose template mismatch: expected {expected}, got {actual}")
        issue_codes.add("pose_action_mismatch")

    score = 0.72 if issue_codes else 1.0
    return {
        "score": score,
        "issues": issues,
        "issue_codes": sorted(issue_codes),
        "expected": expected,
        "actual": actual,
    }


def _expected_template_name(spec: Any) -> str:
    action = getattr(getattr(spec, "action", ""), "value", getattr(spec, "action", ""))
    frame_plan = list(getattr(spec, "frame_plan", []) or [])
    if action in {"walk", "idle"}:
        return action
    if frame_plan:
        variant = str(frame_plan[0].get("action_variant", action))
        if action == "attack":
            return f"attack_{variant}" if variant in {"sword", "axe", "bow"} else "attack_sword"
        if action == "hit":
            if variant in {"light", "heavy", "knockback"}:
                return f"hit_{variant}"
            return "hit_light"
    return action


def _frame_alpha_deltas(frame_paths: list[Path]) -> list[float]:
    images = [Image.open(path).convert("RGBA").resize((96, 96), Image.Resampling.BILINEAR) for path in frame_paths]
    return [_image_delta(images[index - 1], images[index]) for index in range(1, len(images))]


def _loop_delta(frame_paths: list[Path]) -> float:
    if len(frame_paths) < 2:
        return 1.0
    first = Image.open(frame_paths[0]).convert("RGBA").resize((96, 96), Image.Resampling.BILINEAR)
    last = Image.open(frame_paths[-1]).convert("RGBA").resize((96, 96), Image.Resampling.BILINEAR)
    return _image_delta(first, last)


def _image_delta(left: Image.Image, right: Image.Image) -> float:
    left_pixels = left.tobytes()
    right_pixels = right.tobytes()
    total = 0.0
    for left_pixel, right_pixel in zip(left_pixels, right_pixels, strict=True):
        total += abs(left_pixel - right_pixel) / 255
    return total / (left.width * left.height * 4)


def _looks_rigged(frame_paths: list[Path]) -> bool:
    # A procedural rig keeps a stable transparent canvas and part colors; generated redraws usually vary more.
    if len(frame_paths) < 2:
        return False
    deltas = _frame_alpha_deltas(frame_paths)
    return bool(deltas and mean(deltas) < 0.14 and max(deltas) < 0.28)
