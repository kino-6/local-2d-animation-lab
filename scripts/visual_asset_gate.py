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
    _apply_pack_style_findings(manifest_path, actions, action_reports)
    _apply_idle_reference_findings(manifest_path, actions, action_reports)

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
    return _evaluate_action_images(action, images, loop)


def _evaluate_action_images(action: str, images: list[Image.Image], loop: bool) -> dict[str, Any]:
    boxes = [_alpha_bbox(image) for image in images]
    metrics = _action_metrics(images, boxes, loop)
    findings = _findings_for_action(action, metrics)
    decision = "production_ready" if not findings else "needs_retake_or_manual_review"
    return {
        "decision": decision,
        "frame_count": len(images),
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
    adopted_frames: dict[str, list[Image.Image]] = {}
    original_reports: dict[str, dict[str, Any]] = {}
    for action, info in manifest.get("actions", {}).items():
        frame_paths = [output_dir / path for path in info.get("frames", [])]
        original_frames = [Image.open(path).convert("RGBA") for path in frame_paths]
        original_report = _evaluate_action_images(action, original_frames, bool(info.get("runtime", {}).get("loop", True)))
        fixed_frames = _auto_fix_images(action, original_frames)
        fixed_report = _evaluate_action_images(action, fixed_frames, bool(info.get("runtime", {}).get("loop", True)))
        original_reports[action] = original_report
        adopted_frames[action] = fixed_frames if _safe_to_adopt_auto_fix(original_report, fixed_report) else original_frames
        for path, image in zip(frame_paths, adopted_frames[action]):
            image.save(path)
    _normalize_pack_style(output_dir, manifest)
    for action, info in manifest.get("actions", {}).items():
        frame_paths = [output_dir / path for path in info.get("frames", [])]
        normalized_report = evaluate_action(action, frame_paths, bool(info.get("runtime", {}).get("loop", True)))
        if not _safe_to_adopt_auto_fix(original_reports[action], normalized_report):
            for path, image in zip(frame_paths, adopted_frames[action]):
                image.save(path)
    for action, info in manifest.get("actions", {}).items():
        frame_paths = [output_dir / path for path in info.get("frames", [])]
        _regenerate_action_artifacts(output_dir, action, info, frame_paths)
    _regenerate_pack_review(output_dir, manifest)
    fixed_report = evaluate_pack(output_dir / "manifest.json")
    manifest["visual_gate"] = {
        "report": "pack_review/visual_gate_report.json",
        "decision": fixed_report["decision"],
        "production_ready": fixed_report["production_ready"],
        "blocking_actions": fixed_report["blocking_actions"],
    }
    manifest["production_ready"] = fixed_report["production_ready"]
    production_gate = manifest.get("production_gate")
    if isinstance(production_gate, dict):
        production_gate["decision"] = (
            "production_ready" if fixed_report["production_ready"] else "needs_visual_retake_or_manual_review"
        )
        production_gate["production_ready"] = fixed_report["production_ready"]
        production_gate["visual_gate_report"] = "pack_review/visual_gate_report.json"
        production_gate["visual_gate_decision"] = fixed_report["decision"]
        production_gate["blocking_actions"] = fixed_report["blocking_actions"]
    _write_json(output_dir / "manifest.json", manifest)
    if isinstance(production_gate, dict):
        _write_json(output_dir / "production_gate.json", production_gate)
    _write_json(output_dir / "pack_review" / "visual_gate_report.json", fixed_report)
    _write_json(output_dir / "visual_gate_report.json", fixed_report)
    return output_dir


def _auto_fix_frames(action: str, frame_paths: list[Path]) -> list[Image.Image]:
    return _auto_fix_images(action, [Image.open(path).convert("RGBA") for path in frame_paths])


def _auto_fix_images(action: str, images: list[Image.Image]) -> list[Image.Image]:
    frames = [_remove_stray_components(image) for image in images]
    frames = _normalize_value_and_saturation(frames)
    frames = [_reduce_border_chroma_fringe(frame) for frame in frames]
    if action == "hurt":
        frames = _trim_hurt_side_panel_artifacts(frames)
        frames = [_remove_stray_components(frame) for frame in frames]
    if action not in {"jump", "run"}:
        frames = _stabilize_bottom_center(frames)
    return [_keep_inside_canvas(frame, margin=3) for frame in frames]


def _safe_to_adopt_auto_fix(before: dict[str, Any], after: dict[str, Any]) -> bool:
    before_findings = set(before.get("findings", []))
    after_findings = set(after.get("findings", []))
    if after_findings - before_findings:
        return False
    if len(after_findings) > len(before_findings):
        return False
    before_metrics = before.get("metrics", {})
    after_metrics = after.get("metrics", {})
    if after_metrics.get("hard_vertical_alpha_cut_run_max", 0) > before_metrics.get("hard_vertical_alpha_cut_run_max", 0) + 24:
        return False
    if after_metrics.get("main_component_ratio_min", 1.0) + 0.02 < before_metrics.get("main_component_ratio_min", 1.0):
        return False
    return True


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
    entries = []
    labels = []
    for action, info in manifest.get("actions", {}).items():
        for index, frame in enumerate(info.get("frames", [])):
            image = Image.open(output_dir / frame).convert("RGBA")
            bbox = _alpha_bbox(image)
            entries.append((image, bbox))
            labels.append(f"{action} {index:02d}")
    max_crop_width = max(box[2] - box[0] for _image, box in entries)
    max_crop_height = max(box[3] - box[1] for _image, box in entries)
    fixed_scale = min(128 / max(1, max_crop_width), 200 / max(1, max_crop_height))
    thumbs = []
    for image, bbox in entries:
            crop = image.crop(bbox)
            scaled_size = (
                max(1, round(crop.width * fixed_scale)),
                max(1, round(crop.height * fixed_scale)),
            )
            crop = crop.resize(scaled_size, Image.Resampling.LANCZOS)
            thumb = Image.new("RGBA", (150, 212), (245, 245, 245, 255))
            thumb.alpha_composite(crop, ((150 - crop.width) // 2, 200 - crop.height))
            thumbs.append(thumb)
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
    densities = [_silhouette_density(image, box) for image, box in zip(images, boxes)]
    center_xs = [(box[0] + box[2]) * 0.5 for box in boxes]
    center_ys = [(box[1] + box[3]) * 0.5 for box in boxes]
    bottoms = [box[3] for box in boxes]
    colors = [_foreground_color_stats(image) for image in images]
    component_reports = [_component_report(image) for image in images]
    hand_cues = [_hand_cue_report(image, box) for image, box in zip(images, boxes)]
    border_fringe_reports = [_border_chroma_fringe_report(image) for image in images]
    weapon_cue_reports = [_weapon_cue_report(image, box) for image, box in zip(images, boxes)]
    vertical_cut_reports = [_hard_vertical_alpha_cut_report(image, box) for image, box in zip(images, boxes)]
    step_deltas = [_mean_delta(images[index], images[index + 1]) for index in range(len(images) - 1)]
    loop_delta = _mean_delta(images[-1], images[0]) if loop and len(images) > 1 else None
    step_delta_median = median(step_deltas) if step_deltas else 0.0
    step_delta_outlier_threshold = max(18.0, step_delta_median * 2.4)
    isolated_delta_outliers = _isolated_frame_delta_outlier_frames(images, step_deltas)
    step_delta_outlier_frames = sorted(
        {
            index + 1
            for index, value in enumerate(step_deltas)
            if value > step_delta_outlier_threshold
        }
        | set(isolated_delta_outliers)
    )
    hand_areas = [cue["area"] for cue in hand_cues]
    hand_area_median = median(hand_areas) if hand_areas else 0.0
    hand_low_threshold = max(18.0, hand_area_median * 0.55)
    return {
        "bbox_width_range": round(max(widths) - min(widths), 3),
        "bbox_width_median": round(median(widths), 3),
        "bbox_height_range": round(max(heights) - min(heights), 3),
        "center_x_range": round(max(center_xs) - min(center_xs), 3),
        "center_y_range": round(max(center_ys) - min(center_ys), 3),
        "ground_y_range": round(max(bottoms) - min(bottoms), 3),
        "edge_touch_frames": _edge_touch_frames(images, boxes, margin=2),
        "extra_component_frames": [
            index for index, report in enumerate(component_reports) if report["large_component_count"] > 1
        ],
        "main_component_ratio_min": min(report["main_component_ratio"] for report in component_reports),
        "minor_component_ratio_max": round(max(1.0 - report["main_component_ratio"] for report in component_reports), 5),
        "minor_component_fragment_frames": [
            index for index, report in enumerate(component_reports) if 1.0 - report["main_component_ratio"] > 0.003
        ],
        "hard_vertical_alpha_cut_frames": [
            index for index, report in enumerate(vertical_cut_reports) if report["max_strong_edge_run"] >= 70
        ],
        "hard_vertical_alpha_cut_run_max": max(report["max_strong_edge_run"] for report in vertical_cut_reports),
        "silhouette_density_min": round(min(densities), 4),
        "silhouette_width_outlier_frames": [
            index
            for index, (width, density) in enumerate(zip(widths, densities))
            if width > median(widths) * 1.24 and density < 0.49
        ],
        "right_edge_silhouette_outlier_frames": [
            index
            for index, (box, density) in enumerate(zip(boxes, densities))
            if box[2] > median(box[2] for box in boxes) + 8 and density < 0.49
        ],
        "brightness_range": round(max(item["brightness"] for item in colors) - min(item["brightness"] for item in colors), 4),
        "saturation_range": round(max(item["saturation"] for item in colors) - min(item["saturation"] for item in colors), 4),
        "upper_body_hand_cue_area_min": round(min(hand_areas), 3) if hand_areas else 0,
        "upper_body_hand_cue_area_median": round(hand_area_median, 3),
        "upper_body_hand_cue_low_frames": [
            index
            for index, cue in enumerate(hand_cues)
            if cue["area"] < hand_low_threshold and hand_area_median >= 32
        ],
        "border_green_cyan_fringe_ratio_max": round(max(item["ratio"] for item in border_fringe_reports), 4),
        "border_green_cyan_fringe_frames": [
            index for index, item in enumerate(border_fringe_reports) if item["ratio"] > 0.39
        ],
        "weapon_cue_pixels_min": min(item["pixels"] for item in weapon_cue_reports),
        "weapon_cue_pixels_max": max(item["pixels"] for item in weapon_cue_reports),
        "step_delta_values": [round(value, 4) for value in step_deltas],
        "step_delta_max": round(max(step_deltas), 4) if step_deltas else 0,
        "step_delta_outlier_frames": step_delta_outlier_frames,
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
    if action == "hurt" and (
        metrics["silhouette_width_outlier_frames"] or metrics["right_edge_silhouette_outlier_frames"]
    ):
        findings.append("side_panel_or_silhouette_width_outlier")
    if action == "hurt" and metrics["minor_component_fragment_frames"]:
        findings.append("minor_detached_side_fragment")
    if action == "hurt" and metrics["hard_vertical_alpha_cut_frames"]:
        findings.append("hard_vertical_alpha_cut")
    if metrics["bbox_width_range"] > width_limit:
        findings.append("large_width_or_scale_jitter")
    if action not in {"jump", "hurt"} and metrics["bbox_height_range"] > height_limit:
        findings.append("large_height_or_scale_jitter")
    if metrics["center_x_range"] > center_limit:
        findings.append("large_horizontal_center_jitter")
    if action not in {"jump", "run"} and metrics["ground_y_range"] > 22:
        findings.append("ground_or_foot_contact_jitter")
    if metrics["brightness_range"] > 0.22:
        findings.append("frame_to_frame_brightness_drift")
    if metrics["saturation_range"] > 0.28:
        findings.append("frame_to_frame_saturation_drift")
    if metrics["border_green_cyan_fringe_frames"]:
        findings.append("green_cyan_alpha_edge_fringe")
    if metrics["step_delta_outlier_frames"]:
        findings.append("abrupt_frame_delta_outlier")
    if action.startswith("attack_sword") and metrics["weapon_cue_pixels_min"] < 650:
        findings.append("weak_weapon_readability")
    if action in {"walk", "parry_sword"}:
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


def _normalize_pack_style(output_dir: Path, manifest: dict[str, Any]) -> None:
    action_stats = _action_style_stats_from_manifest(output_dir, manifest)
    reference_stats = [
        stats
        for action, stats in action_stats.items()
        if action in {"walk", "idle"}
    ] or list(action_stats.values())
    target_brightness = median(item["brightness"] for item in reference_stats)
    target_saturation = median(item["saturation"] for item in reference_stats)
    for action, info in manifest.get("actions", {}).items():
        stats = action_stats.get(action)
        if not stats:
            continue
        brightness_factor = _clamp(target_brightness / max(0.01, stats["brightness"]), 0.88, 1.18)
        saturation_factor = _clamp(target_saturation / max(0.01, stats["saturation"]), 0.82, 1.14)
        for frame in info.get("frames", []):
            path = output_dir / frame
            image = Image.open(path).convert("RGBA")
            alpha = image.getchannel("A")
            rgb = image.convert("RGB")
            rgb = ImageEnhance.Brightness(rgb).enhance(brightness_factor)
            rgb = ImageEnhance.Color(rgb).enhance(saturation_factor)
            out = rgb.convert("RGBA")
            out.putalpha(alpha)
            _reduce_border_chroma_fringe(out).save(path)


def _trim_hurt_side_panel_artifacts(frames: list[Image.Image]) -> list[Image.Image]:
    boxes = [_alpha_bbox(frame) for frame in frames]
    widths = [box[2] - box[0] for box in boxes]
    densities = [_silhouette_density(frame, box) for frame, box in zip(frames, boxes)]
    target_width = median(widths) * 1.20
    target_left = round(median(box[0] for box in boxes) - 2)
    target_right = round(median(box[2] for box in boxes) - 8)
    fixed = []
    for frame, box, width, density in zip(frames, boxes, widths, densities):
        has_side_panel = (
            width > median(widths) * 1.20
            and density < 0.49
            and box[2] > median(item[2] for item in boxes) + 4
        )
        if width <= target_width and not has_side_panel:
            fixed.append(frame)
            continue
        left, _top, right, _bottom = box
        center = (left + right) * 0.5
        keep_left = round(center - target_width * 0.5)
        keep_right = round(center + target_width * 0.5)
        if has_side_panel:
            keep_left = max(keep_left, target_left)
            keep_right = min(keep_right, target_right)
        out = _feather_alpha_outside_x_range(frame, keep_left, keep_right, feather=18)
        fixed.append(out)
    return fixed


def _feather_alpha_outside_x_range(image: Image.Image, keep_left: int, keep_right: int, feather: int) -> Image.Image:
    out = image.copy()
    alpha = out.getchannel("A")
    alpha_pixels = alpha.load()
    for y in range(out.height):
        for x in range(out.width):
            value = alpha_pixels[x, y]
            if value == 0:
                continue
            if x < keep_left:
                distance = keep_left - x
                factor = _clamp(1.0 - distance / max(1, feather), 0.0, 1.0)
                alpha_pixels[x, y] = round(value * factor)
            elif x > keep_right:
                distance = x - keep_right
                factor = _clamp(1.0 - distance / max(1, feather), 0.0, 1.0)
                alpha_pixels[x, y] = round(value * factor)
    out.putalpha(alpha)
    return out


def _apply_pack_style_findings(
    manifest_path: Path,
    actions: dict[str, Any],
    action_reports: dict[str, Any],
) -> None:
    action_stats = _action_style_stats_from_manifest(manifest_path.parent, actions)
    reference_stats = [
        stats
        for action, stats in action_stats.items()
        if action in {"walk", "idle"}
    ] or list(action_stats.values())
    if not reference_stats:
        return
    target_brightness = median(item["brightness"] for item in reference_stats)
    target_saturation = median(item["saturation"] for item in reference_stats)
    for action, stats in action_stats.items():
        report = action_reports.get(action)
        if not report:
            continue
        brightness_delta = round(stats["brightness"] - target_brightness, 4)
        saturation_delta = round(stats["saturation"] - target_saturation, 4)
        report["metrics"]["pack_style_brightness_delta"] = brightness_delta
        report["metrics"]["pack_style_saturation_delta"] = saturation_delta
        if abs(brightness_delta) > 0.055:
            report["findings"].append("action_brightness_style_drift")
        if abs(saturation_delta) > 0.045:
            report["findings"].append("action_saturation_style_drift")
        report["decision"] = "production_ready" if not report["findings"] else "needs_retake_or_manual_review"


def _apply_idle_reference_findings(
    manifest_path: Path,
    actions: dict[str, Any],
    action_reports: dict[str, Any],
) -> None:
    idle_info = actions.get("idle")
    if not idle_info:
        return
    idle_frames = [
        Image.open(_resolve_asset_path(manifest_path, path)).convert("RGBA")
        for path in idle_info.get("frames", [])
    ]
    if not idle_frames:
        return
    idle_boxes = [_alpha_bbox(frame) for frame in idle_frames]
    recovery_actions = {"jump", "hurt", "attack_sword_light", "dodge_backstep", "parry_sword"}
    for action, info in actions.items():
        if action == "idle":
            continue
        report = action_reports.get(action)
        if not report:
            continue
        frames = [
            Image.open(_resolve_asset_path(manifest_path, path)).convert("RGBA")
            for path in info.get("frames", [])
        ]
        if not frames:
            continue
        idle_deltas = [
            min(_mean_delta(frame, idle_frame) for idle_frame in idle_frames)
            for frame in frames
        ]
        frame_boxes = [_alpha_bbox(frame) for frame in frames]
        idle_bbox_deltas = [
            min(_bbox_pose_delta(frame_box, idle_box) for idle_box in idle_boxes)
            for frame_box in frame_boxes
        ]
        report["metrics"]["idle_pose_delta_values"] = [round(value, 4) for value in idle_deltas]
        report["metrics"]["idle_pose_delta_min"] = round(min(idle_deltas), 4)
        report["metrics"]["idle_pose_delta_first"] = round(idle_deltas[0], 4)
        report["metrics"]["idle_pose_delta_last"] = round(idle_deltas[-1], 4)
        report["metrics"]["idle_bbox_pose_delta_values"] = [round(value, 4) for value in idle_bbox_deltas]
        report["metrics"]["idle_bbox_pose_delta_first"] = round(idle_bbox_deltas[0], 4)
        report["metrics"]["idle_bbox_pose_delta_last"] = round(idle_bbox_deltas[-1], 4)
        poor_recovery = idle_deltas[-1] > 30.0
        if not action.startswith("attack_sword"):
            poor_recovery = poor_recovery or idle_bbox_deltas[-1] > 58.0
        if action in recovery_actions and poor_recovery:
            report["findings"].append("poor_recovery_to_idle_pose")
        report["decision"] = "production_ready" if not report["findings"] else "needs_retake_or_manual_review"


def _action_style_stats_from_manifest(base_dir: Path, manifest_or_actions: dict[str, Any]) -> dict[str, dict[str, float]]:
    actions = manifest_or_actions.get("actions", manifest_or_actions)
    stats = {}
    for action, info in actions.items():
        colors = []
        for frame in info.get("frames", []):
            path = base_dir / frame
            if path.exists():
                colors.append(_foreground_color_stats(Image.open(path).convert("RGBA")))
        if colors:
            stats[action] = {
                "brightness": median(item["brightness"] for item in colors),
                "saturation": median(item["saturation"] for item in colors),
            }
    return stats


def _reduce_border_chroma_fringe(image: Image.Image) -> Image.Image:
    source = image.convert("RGBA")
    pixels = source.load()
    alpha = source.getchannel("A").load()
    out = source.copy()
    out_pixels = out.load()
    for y in range(source.height):
        for x in range(source.width):
            if alpha[x, y] < 24 or not _touches_transparency(alpha, source.width, source.height, x, y):
                continue
            red, green, blue, opacity = pixels[x, y]
            hue, saturation, value = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
            if 0.25 <= hue <= 0.55 and saturation >= 0.35 and value >= 0.18:
                new_red, new_green, new_blue = colorsys.hsv_to_rgb(hue, saturation * 0.18, value * 0.92)
                out_pixels[x, y] = (
                    round(new_red * 255),
                    round(new_green * 255),
                    round(new_blue * 255),
                    opacity,
                )
    return out


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


def _keep_inside_canvas(image: Image.Image, margin: int) -> Image.Image:
    box = image.getchannel("A").getbbox()
    if box is None:
        return image
    dx = 0
    dy = 0
    if box[0] < margin:
        dx = margin - box[0]
    elif box[2] > image.width - margin:
        dx = image.width - margin - box[2]
    if box[1] < margin:
        dy = margin - box[1]
    elif box[3] > image.height - margin:
        dy = image.height - margin - box[3]
    if dx == 0 and dy == 0:
        return image
    canvas = Image.new("RGBA", image.size, (0, 0, 0, 0))
    canvas.alpha_composite(image, (dx, dy))
    return canvas


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


def _silhouette_density(image: Image.Image, alpha_box: tuple[int, int, int, int]) -> float:
    left, top, right, bottom = alpha_box
    alpha = image.getchannel("A").load()
    area = 0
    for y in range(top, bottom):
        for x in range(left, right):
            if alpha[x, y] >= 24:
                area += 1
    return area / max(1, (right - left) * (bottom - top))


def _border_chroma_fringe_report(image: Image.Image) -> dict[str, Any]:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    alpha = rgba.getchannel("A").load()
    border_pixels = 0
    fringe_pixels = 0
    for y in range(rgba.height):
        for x in range(rgba.width):
            if alpha[x, y] < 24 or not _touches_transparency(alpha, rgba.width, rgba.height, x, y):
                continue
            red, green, blue, _opacity = pixels[x, y]
            hue, saturation, value = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
            border_pixels += 1
            if 0.25 <= hue <= 0.55 and saturation >= 0.35 and value >= 0.18:
                fringe_pixels += 1
    return {
        "pixels": fringe_pixels,
        "border_pixels": border_pixels,
        "ratio": fringe_pixels / max(1, border_pixels),
    }


def _weapon_cue_report(image: Image.Image, alpha_box: tuple[int, int, int, int]) -> dict[str, Any]:
    left, top, right, bottom = alpha_box
    height = bottom - top
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    cue_pixels = 0
    for y in range(top + round(height * 0.22), bottom):
        for x in range(left, right):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 64:
                continue
            hue, saturation, value = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
            _ = hue
            if saturation <= 0.24 and value >= 0.54:
                cue_pixels += 1
    return {"pixels": cue_pixels}


def _hard_vertical_alpha_cut_report(image: Image.Image, alpha_box: tuple[int, int, int, int]) -> dict[str, Any]:
    left, top, right, bottom = alpha_box
    alpha = image.getchannel("A").load()
    max_run = 0
    for x in (left, right - 1):
        current_run = 0
        for y in range(top, bottom):
            if alpha[x, y] >= 160:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
    return {"max_strong_edge_run": max_run}


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


def _touches_transparency(alpha: Any, width: int, height: int, x: int, y: int) -> bool:
    for ny in range(max(0, y - 1), min(height, y + 2)):
        for nx in range(max(0, x - 1), min(width, x + 2)):
            if nx == x and ny == y:
                continue
            if alpha[nx, ny] < 24:
                return True
    return False


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


def _bbox_pose_delta(left_box: tuple[int, int, int, int], right_box: tuple[int, int, int, int]) -> float:
    left_center_x = (left_box[0] + left_box[2]) * 0.5
    left_center_y = (left_box[1] + left_box[3]) * 0.5
    right_center_x = (right_box[0] + right_box[2]) * 0.5
    right_center_y = (right_box[1] + right_box[3]) * 0.5
    return abs(left_center_x - right_center_x) + abs(left_center_y - right_center_y)


def _isolated_frame_delta_outlier_frames(images: list[Image.Image], step_deltas: list[float]) -> list[int]:
    outliers = []
    for index in range(1, len(images) - 1):
        incoming = step_deltas[index - 1]
        outgoing = step_deltas[index]
        bypass = _mean_delta(images[index - 1], images[index + 1])
        if incoming > 12.0 and outgoing > 12.0 and bypass < 8.0:
            outliers.append(index)
    return outliers


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
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
