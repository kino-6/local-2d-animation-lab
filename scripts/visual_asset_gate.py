from __future__ import annotations

import argparse
import colorsys
import json
import shutil
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a visual quality gate for adopted 2D sprite packs.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--auto-fix-output", type=Path)
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()

    result = evaluate_pack(args.manifest)
    if args.report:
        _write_json(args.report, result)
    if args.auto_fix_output:
        fixed = auto_fix_pack(args.manifest, args.auto_fix_output)
        result["auto_fix_output"] = str(fixed).replace("\\", "/")
        if args.report:
            _write_json(args.report, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.fail_on_review and result["decision"] != "production_ready":
        raise SystemExit(1)


def evaluate_pack(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("route") != "character_sprite_asset_pack":
        raise ValueError(f"unsupported manifest route: {manifest.get('route')}")

    actions: dict[str, Any] = manifest.get("actions", {})
    action_reports = {}
    for action, info in actions.items():
        frame_paths = [_resolve_asset_path(manifest_path, path) for path in info.get("frames", [])]
        action_reports[action] = evaluate_action(action, frame_paths, bool(info.get("runtime", {}).get("loop", True)))

    blocking_actions = [
        action
        for action, report in action_reports.items()
        if report["decision"] == "needs_retake_or_manual_review"
    ]
    decision = "production_ready" if not blocking_actions else "needs_retake_or_manual_review"
    return {
        "route": "visual_asset_gate",
        "manifest": _display_path(manifest_path),
        "decision": decision,
        "production_ready": decision == "production_ready",
        "blocking_actions": blocking_actions,
        "actions": action_reports,
        "notes": [
            "This gate detects deterministic visual risks before human review.",
            "Human review still overrides the gate for anatomy, pose intent, and art direction.",
        ],
    }


def evaluate_action(action: str, frame_paths: list[Path], loop: bool) -> dict[str, Any]:
    images = [Image.open(path).convert("RGBA") for path in frame_paths]
    boxes = [_alpha_bbox(image) for image in images]
    metrics = _action_metrics(images, boxes, loop)
    findings = _findings_for_action(action, metrics)
    decision = "production_ready" if not findings else "needs_retake_or_manual_review"
    return {
        "decision": decision,
        "frame_count": len(frame_paths),
        "frame_size": {"width": images[0].width, "height": images[0].height} if images else {},
        "metrics": metrics,
        "findings": findings,
    }


def auto_fix_pack(manifest_path: Path, output_dir: Path) -> Path:
    manifest_path = manifest_path.resolve()
    source_dir = manifest_path.parent
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(source_dir, output_dir)

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    for action, info in manifest.get("actions", {}).items():
        frame_paths = [output_dir / path for path in info.get("frames", [])]
        fixed_frames = _auto_fix_frames(action, frame_paths)
        for path, image in zip(frame_paths, fixed_frames):
            image.save(path)
        _regenerate_action_artifacts(output_dir, action, info, frame_paths)
    _regenerate_pack_review(output_dir, manifest)
    fixed_report = evaluate_pack(output_dir / "manifest.json")
    _write_json(output_dir / "visual_gate_report.json", fixed_report)
    return output_dir


def _auto_fix_frames(action: str, frame_paths: list[Path]) -> list[Image.Image]:
    frames = [_remove_stray_components(Image.open(path).convert("RGBA")) for path in frame_paths]
    frames = _normalize_value_and_saturation(frames)
    if action not in {"jump", "run"}:
        frames = _stabilize_bottom_center(frames)
    return frames


def _regenerate_action_artifacts(output_dir: Path, action: str, info: dict[str, Any], frame_paths: list[Path]) -> None:
    action_dir = output_dir / "actions" / action
    runtime = info.get("runtime", {})
    fps = float(runtime.get("fps", 8.0))
    loop = bool(runtime.get("loop", True))
    make_sprite_sheet(frame_paths, action_dir / "spritesheet.png", columns=len(frame_paths))
    make_preview_gif(frame_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=loop)
    make_contact_sheet(frame_paths, action_dir / "contact_sheet.png", columns=min(6, len(frame_paths)))


def _regenerate_pack_review(output_dir: Path, manifest: dict[str, Any]) -> None:
    review_dir = output_dir / "pack_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    thumbs = []
    labels = []
    for action, info in manifest.get("actions", {}).items():
        for index, frame in enumerate(info.get("frames", [])):
            image = Image.open(output_dir / frame).convert("RGBA")
            bbox = _alpha_bbox(image)
            crop = image.crop(bbox)
            crop.thumbnail((128, 200), Image.Resampling.LANCZOS)
            thumb = Image.new("RGBA", (150, 212), (245, 245, 245, 255))
            thumb.alpha_composite(crop, ((150 - crop.width) // 2, 4))
            thumbs.append(thumb)
            labels.append(f"{action} {index:02d}")
    columns = 12
    rows = (len(thumbs) + columns - 1) // columns
    canvas = Image.new("RGBA", (columns * 150, rows * 236), (245, 245, 245, 255))
    draw = ImageDraw.Draw(canvas)
    for index, thumb in enumerate(thumbs):
        x = (index % columns) * 150
        y = (index // columns) * 236
        canvas.alpha_composite(thumb, (x, y))
        draw.text((x + 4, y + 212), labels[index], fill=(30, 30, 30, 255))
    canvas.save(review_dir / "all_actions_contact_sheet.png")


def _action_metrics(images: list[Image.Image], boxes: list[tuple[int, int, int, int]], loop: bool) -> dict[str, Any]:
    widths = [box[2] - box[0] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    center_xs = [(box[0] + box[2]) * 0.5 for box in boxes]
    center_ys = [(box[1] + box[3]) * 0.5 for box in boxes]
    bottoms = [box[3] for box in boxes]
    colors = [_foreground_color_stats(image) for image in images]
    component_reports = [_component_report(image) for image in images]
    hand_cues = [_hand_cue_report(image, box) for image, box in zip(images, boxes)]
    step_deltas = [_mean_delta(images[index], images[index + 1]) for index in range(len(images) - 1)]
    loop_delta = _mean_delta(images[-1], images[0]) if loop and len(images) > 1 else None
    hand_areas = [cue["area"] for cue in hand_cues]
    hand_area_median = median(hand_areas) if hand_areas else 0.0
    hand_low_threshold = max(18.0, hand_area_median * 0.55)
    return {
        "bbox_width_range": round(max(widths) - min(widths), 3),
        "bbox_height_range": round(max(heights) - min(heights), 3),
        "center_x_range": round(max(center_xs) - min(center_xs), 3),
        "center_y_range": round(max(center_ys) - min(center_ys), 3),
        "ground_y_range": round(max(bottoms) - min(bottoms), 3),
        "edge_touch_frames": _edge_touch_frames(images, boxes, margin=2),
        "extra_component_frames": [
            index for index, report in enumerate(component_reports) if report["large_component_count"] > 1
        ],
        "main_component_ratio_min": min(report["main_component_ratio"] for report in component_reports),
        "brightness_range": round(max(item["brightness"] for item in colors) - min(item["brightness"] for item in colors), 4),
        "saturation_range": round(max(item["saturation"] for item in colors) - min(item["saturation"] for item in colors), 4),
        "upper_body_hand_cue_area_min": round(min(hand_areas), 3) if hand_areas else 0,
        "upper_body_hand_cue_area_median": round(hand_area_median, 3),
        "upper_body_hand_cue_low_frames": [
            index
            for index, cue in enumerate(hand_cues)
            if cue["area"] < hand_low_threshold and hand_area_median >= 32
        ],
        "mean_step_delta": round(sum(step_deltas) / max(1, len(step_deltas)), 4),
        "loop_delta": None if loop_delta is None else round(loop_delta, 4),
    }


def _findings_for_action(action: str, metrics: dict[str, Any]) -> list[str]:
    findings = []
    width_limit = 120 if action in {"run", "jump", "attack_sword_light"} else 80
    height_limit = 96 if action == "jump" else 52
    center_limit = 96 if action in {"run", "jump", "attack_sword_light"} else 52
    if metrics["edge_touch_frames"]:
        findings.append("possible_cropping_or_canvas_edge_touch")
    if metrics["extra_component_frames"]:
        findings.append("extra_foreground_component_or_sprite_fragment")
    if metrics["bbox_width_range"] > width_limit:
        findings.append("large_width_or_scale_jitter")
    if metrics["bbox_height_range"] > height_limit:
        findings.append("large_height_or_scale_jitter")
    if metrics["center_x_range"] > center_limit:
        findings.append("large_horizontal_center_jitter")
    if action not in {"jump", "run"} and metrics["ground_y_range"] > 22:
        findings.append("ground_or_foot_contact_jitter")
    if metrics["brightness_range"] > 0.22:
        findings.append("frame_to_frame_brightness_drift")
    if metrics["saturation_range"] > 0.28:
        findings.append("frame_to_frame_saturation_drift")
    if action in {"walk", "run", "jump", "hurt", "attack_sword_light", "parry_sword"}:
        if metrics["upper_body_hand_cue_low_frames"]:
            findings.append("upper_body_hand_cue_dropout")
    if metrics["loop_delta"] is not None and metrics["mean_step_delta"] > 0:
        if metrics["loop_delta"] > metrics["mean_step_delta"] * 2.8:
            findings.append("loop_closure_jump")
    return findings


def _remove_stray_components(image: Image.Image) -> Image.Image:
    components = _alpha_components(image.getchannel("A"))
    if not components:
        return image
    main = max(components, key=lambda component: component["area"])
    keep = [main]
    main_box = main["bbox"]
    for component in components:
        if component is main:
            continue
        area_ratio = component["area"] / max(1, main["area"])
        box = component["bbox"]
        center_x = (box[0] + box[2]) * 0.5
        center_y = (box[1] + box[3]) * 0.5
        close_to_main = (
            main_box[0] - 24 <= center_x <= main_box[2] + 24
            and main_box[1] - 24 <= center_y <= main_box[3] + 24
        )
        if area_ratio >= 0.18 and close_to_main:
            keep.append(component)
    mask = Image.new("L", image.size, 0)
    mask_pixels = mask.load()
    for component in keep:
        for x, y in component["pixels"]:
            mask_pixels[x, y] = 255
    out = image.copy()
    out.putalpha(mask)
    return out


def _normalize_value_and_saturation(frames: list[Image.Image]) -> list[Image.Image]:
    stats = [_foreground_color_stats(frame) for frame in frames]
    target_brightness = median(item["brightness"] for item in stats)
    target_saturation = median(item["saturation"] for item in stats)
    normalized = []
    for frame, stat in zip(frames, stats):
        alpha = frame.getchannel("A")
        rgb = frame.convert("RGB")
        brightness_factor = _clamp(target_brightness / max(0.01, stat["brightness"]), 0.84, 1.18)
        saturation_factor = _clamp(target_saturation / max(0.01, stat["saturation"]), 0.80, 1.22)
        rgb = ImageEnhance.Brightness(rgb).enhance(brightness_factor)
        rgb = ImageEnhance.Color(rgb).enhance(saturation_factor)
        out = rgb.convert("RGBA")
        out.putalpha(alpha)
        normalized.append(out)
    return normalized


def _stabilize_bottom_center(frames: list[Image.Image]) -> list[Image.Image]:
    boxes = [_alpha_bbox(frame) for frame in frames]
    target_center = median((box[0] + box[2]) * 0.5 for box in boxes)
    target_bottom = median(box[3] for box in boxes)
    fixed = []
    for frame, box in zip(frames, boxes):
        center = (box[0] + box[2]) * 0.5
        bottom = box[3]
        dx = round(target_center - center)
        dy = round(target_bottom - bottom)
        canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        canvas.alpha_composite(frame, (dx, dy))
        fixed.append(canvas)
    return fixed


def _foreground_color_stats(image: Image.Image) -> dict[str, float]:
    pixels = image.convert("RGBA").load()
    brightness_sum = 0.0
    saturation_sum = 0.0
    count = 0
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 16:
                continue
            hue, saturation, value = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
            _ = hue
            brightness_sum += value
            saturation_sum += saturation
            count += 1
    return {
        "brightness": round(brightness_sum / max(1, count), 5),
        "saturation": round(saturation_sum / max(1, count), 5),
    }


def _hand_cue_report(image: Image.Image, alpha_box: tuple[int, int, int, int]) -> dict[str, Any]:
    left, top, right, bottom = alpha_box
    width = right - left
    height = bottom - top
    skin_components = _skin_components(image)
    candidates = []
    for component in skin_components:
        box = component["bbox"]
        center_x = (box[0] + box[2]) * 0.5
        center_y = (box[1] + box[3]) * 0.5
        in_torso_band = top + height * 0.28 <= center_y <= top + height * 0.52
        # Avoid counting face highlights at the upper/right side of the head as hands.
        not_face_band = not (center_y <= top + height * 0.31 and center_x >= left + width * 0.42)
        near_body = left - width * 0.08 <= center_x <= right + width * 0.08
        if in_torso_band and not_face_band and near_body and 8 <= component["area"] <= 220:
            candidates.append(component)
    return {
        "area": sum(component["area"] for component in candidates),
        "count": len(candidates),
        "boxes": [component["bbox"] for component in candidates],
    }


def _skin_components(image: Image.Image) -> list[dict[str, Any]]:
    rgba = image.convert("RGBA")
    source = rgba.load()
    mask = Image.new("L", rgba.size, 0)
    mask_pixels = mask.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = source[x, y]
            if alpha < 24:
                continue
            hue, saturation, value = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
            is_skin_hue = hue < 0.13 or hue > 0.94
            is_skin = (
                is_skin_hue
                and 0.08 <= saturation <= 0.58
                and 0.45 <= value <= 1.0
                and red >= green
                and green >= blue * 0.75
            )
            if is_skin:
                mask_pixels[x, y] = 255
    return _alpha_components(mask)


def _component_report(image: Image.Image) -> dict[str, Any]:
    components = _alpha_components(image.getchannel("A"))
    if not components:
        return {"large_component_count": 0, "main_component_ratio": 0.0}
    main_area = max(component["area"] for component in components)
    total_area = sum(component["area"] for component in components)
    large_count = sum(1 for component in components if component["area"] >= main_area * 0.08)
    return {
        "large_component_count": large_count,
        "main_component_ratio": round(main_area / max(1, total_area), 5),
    }


def _alpha_components(alpha: Image.Image) -> list[dict[str, Any]]:
    pixels = alpha.load()
    width, height = alpha.size
    seen: set[tuple[int, int]] = set()
    components = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in seen:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            points = []
            left = right = x
            top = bottom = y
            while stack:
                px, py = stack.pop()
                points.append((px, py))
                left = min(left, px)
                right = max(right, px + 1)
                top = min(top, py)
                bottom = max(bottom, py + 1)
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in seen:
                        continue
                    if pixels[nx, ny] == 0:
                        continue
                    seen.add((nx, ny))
                    stack.append((nx, ny))
            if len(points) >= 8:
                components.append({"area": len(points), "bbox": (left, top, right, bottom), "pixels": points})
    return components


def _edge_touch_frames(
    images: list[Image.Image], boxes: list[tuple[int, int, int, int]], margin: int
) -> list[int]:
    return [
        index
        for index, (image, box) in enumerate(zip(images, boxes))
        if box[0] <= margin
        or box[1] <= margin
        or box[2] >= image.width - margin
        or box[3] >= image.height - margin
    ]


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("empty transparent frame")
    return bbox


def _mean_delta(a: Image.Image, b: Image.Image) -> float:
    return ImageStat.Stat(ImageChops.difference(a, b).convert("L")).mean[0]


def _resolve_asset_path(manifest_path: Path, path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    manifest_candidate = manifest_path.parent / path
    if manifest_candidate.exists():
        return manifest_candidate
    repo_candidate = manifest_path.parents[2] / path
    if repo_candidate.exists():
        return repo_candidate
    return manifest_candidate


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
