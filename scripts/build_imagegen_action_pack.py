from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


ACTION_SPECS = {
    "idle": {"frame_count": 4, "loop": True, "fps": 6},
    "walk": {"frame_count": 8, "loop": True, "fps": 8},
    "run": {"frame_count": 8, "loop": True, "fps": 10},
    "jump": {"frame_count": 12, "loop": False, "fps": 10},
    "hurt": {"frame_count": 8, "loop": False, "fps": 8},
    "attack_sword_light": {"frame_count": 11, "loop": False, "fps": 10},
}

PHASES = {
    "idle": ["neutral", "breathe_up", "breathe_peak", "breathe_down"],
    "walk": ["right_contact", "right_down", "right_passing", "right_up", "left_contact", "left_down", "left_passing", "left_up"],
    "run": ["right_contact", "right_down", "flight_forward", "left_reach", "left_contact", "left_down", "flight_backward", "right_reach"],
    "jump": [
        "crouch",
        "deep_crouch",
        "takeoff",
        "early_rise",
        "rise",
        "apex_approach",
        "apex",
        "fall",
        "landing_contact",
        "landing_settle",
        "recover_half",
        "recover",
    ],
    "hurt": ["brace", "impact_recoil", "strong_recoil", "peak_recoil", "stagger", "settle", "recover_half", "recover"],
    "attack_sword_light": ["ready", "anticipation", "draw_back", "windup", "slash_start", "active_slash", "follow_through", "recoil", "settle_1", "recover", "ready_return"],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Godot-loadable character sprite pack from image-generated action sheets.")
    parser.add_argument("--sheets-dir", required=True, type=Path)
    parser.add_argument("--design-source", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack"), type=Path)
    parser.add_argument("--asset-name", default="comfyui2025_74298_nun_skirt_boots")
    parser.add_argument("--frame-width", default=256, type=int)
    parser.add_argument("--frame-height", default=384, type=int)
    parser.add_argument("--target-height", default=336, type=int)
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    manifest = build_pack(
        sheets_dir=args.sheets_dir,
        design_source=args.design_source,
        output_dir=args.output_dir,
        asset_name=args.asset_name,
        frame_size=(args.frame_width, args.frame_height),
        target_height=args.target_height,
        clean=args.clean,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def build_pack(
    sheets_dir: Path,
    design_source: Path,
    output_dir: Path,
    asset_name: str,
    frame_size: tuple[int, int],
    target_height: int,
    clean: bool = True,
) -> dict[str, Any]:
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    actions_dir = output_dir / "actions"
    actions_dir.mkdir(parents=True, exist_ok=True)

    source_sheet_paths = {
        "walk": sheets_dir / "walk_sheet.png",
        "run": sheets_dir / "run_sheet.png",
        "jump": sheets_dir / "jump_sheet.png",
        "hurt": sheets_dir / "hurt_sheet.png",
        "attack_sword_light": sheets_dir / "attack_sword_light_sheet.png",
    }
    for action, path in source_sheet_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing {action} sheet: {path}")

    actions: dict[str, Any] = {}
    walk_frames = _process_action_sheet(
        source_sheet_paths["walk"],
        "walk",
        ACTION_SPECS["walk"]["frame_count"],
        actions_dir / "walk",
        frame_size,
        target_height,
        preserve_vertical_arc=False,
    )
    actions["walk"] = _write_action_artifacts("walk", walk_frames, actions_dir / "walk")
    idle_frames = _make_idle_frames(walk_frames[0])
    actions["idle"] = _write_action_artifacts("idle", idle_frames, actions_dir / "idle")
    for action in ["run", "jump", "hurt", "attack_sword_light"]:
        frames = _process_action_sheet(
            source_sheet_paths[action],
            action,
            ACTION_SPECS[action]["frame_count"],
            actions_dir / action,
            frame_size,
            target_height,
            preserve_vertical_arc=False,
        )
        actions[action] = _write_action_artifacts(action, frames, actions_dir / action)

    review = _write_pack_review(output_dir, actions)
    gate = _production_gate(actions, review)
    manifest = {
        "route": "character_sprite_asset_pack",
        "asset_kind": "2d_game_sprite_asset_pack",
        "asset_name": asset_name,
        "source_design": str(design_source).replace("\\", "/"),
        "source_action_sheets": {key: str(path).replace("\\", "/") for key, path in source_sheet_paths.items()},
        "actions": actions,
        "pack_review": {
            "all_actions_contact_sheet": "pack_review/all_actions_contact_sheet.png",
            "quality_report": "pack_review/quality_report.json",
            "godot_import_manifest": "pack_review/godot_import_manifest.json",
        },
        "production_gate": gate,
        "production_ready": gate["production_ready"],
        "backend_usage": {
            "uses_builtin_image_generation": True,
            "uses_comfyui": False,
            "uses_wan_video": False,
            "uses_controlnet": False,
            "uses_120_frame_generation": False,
        },
        "known_limits": [
            "This pack is generated from a design sheet and action sprite sheets; it is not frame-by-frame hand-authored art.",
            "Weapon/effect layers are not yet separated for attack_sword_light.",
        ],
    }
    _write_text(output_dir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write_text(output_dir / "runtime_manifest.json", json.dumps(_runtime_manifest(actions), indent=2, ensure_ascii=False) + "\n")
    _write_text(output_dir / "production_gate.json", json.dumps(gate, indent=2, ensure_ascii=False) + "\n")
    _write_text(output_dir / "notes.md", _notes(manifest))
    return manifest


def _process_action_sheet(
    sheet_path: Path,
    action: str,
    frame_count: int,
    action_dir: Path,
    frame_size: tuple[int, int],
    target_height: int,
    preserve_vertical_arc: bool,
) -> list[Path]:
    sheet = Image.open(sheet_path).convert("RGBA")
    cells = _split_horizontal_cells(sheet, frame_count)
    cleaned = [_keep_largest_alpha_component(_threshold_alpha(_clean_green_background(cell), 24)) for cell in cells]
    normalized = _normalize_cells(cleaned, frame_size, target_height, preserve_vertical_arc=preserve_vertical_arc)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, frame in enumerate(normalized):
        path = frames_dir / f"{action}_{index:03d}.png"
        frame.save(path)
        paths.append(path)
    return paths


def _split_horizontal_cells(sheet: Image.Image, frame_count: int) -> list[Image.Image]:
    cleaned = _clean_green_background(sheet)
    width, height = sheet.size
    component_cells = _split_connected_components(cleaned, frame_count)
    if component_cells:
        return component_cells
    centers = _detect_frame_centers(cleaned.getchannel("A"), frame_count)
    if len(centers) == frame_count:
        boundaries = [0]
        for index in range(frame_count - 1):
            boundaries.append(round((centers[index] + centers[index + 1]) * 0.5))
        boundaries.append(width)
        cells = []
        for index in range(frame_count):
            left = max(0, boundaries[index])
            right = min(width, boundaries[index + 1])
            cells.append(sheet.crop((left, 0, right, height)))
        return cells

    cells = []
    for index in range(frame_count):
        left = round(index * width / frame_count)
        right = round((index + 1) * width / frame_count)
        cells.append(sheet.crop((left, 0, right, height)))
    return cells


def _split_connected_components(cleaned_sheet: Image.Image, frame_count: int) -> list[Image.Image]:
    alpha = _threshold_alpha(cleaned_sheet, 24).getchannel("A")
    components = _alpha_components(alpha)
    min_area = max(1000, cleaned_sheet.width * cleaned_sheet.height // 2000)
    big_components = [component for component in components if component["area"] >= min_area]
    if len(big_components) != frame_count:
        return []
    big_components.sort(key=lambda component: component["bbox"][0])
    cells = []
    for component in big_components:
        left, top, right, bottom = component["bbox"]
        pad_x = max(12, round((right - left) * 0.08))
        pad_y = max(12, round((bottom - top) * 0.08))
        crop_box = (
            max(0, left - pad_x),
            max(0, top - pad_y),
            min(cleaned_sheet.width, right + pad_x),
            min(cleaned_sheet.height, bottom + pad_y),
        )
        cells.append(cleaned_sheet.crop(crop_box))
    return cells


def _detect_frame_centers(alpha: Image.Image, frame_count: int) -> list[float]:
    pixels = alpha.load()
    width, height = alpha.size
    columns = []
    for x in range(width):
        columns.append(sum(1 for y in range(height) if pixels[x, y] > 0))
    radius = max(3, width // (frame_count * 18))
    smooth = []
    for x in range(width):
        left = max(0, x - radius)
        right = min(width, x + radius + 1)
        smooth.append(sum(columns[left:right]) / (right - left))
    threshold = max(8.0, max(smooth) * 0.08)
    runs = []
    in_run = False
    start = 0
    for x, value in enumerate(smooth):
        if value > threshold and not in_run:
            start = x
            in_run = True
        elif (value <= threshold or x == width - 1) and in_run:
            end = x if value <= threshold else x + 1
            if end - start >= 10:
                total = sum(smooth[start:end])
                center = sum(index * smooth[index] for index in range(start, end)) / max(1.0, total)
                runs.append({"start": start, "end": end, "center": center, "score": total, "width": end - start})
            in_run = False
    if len(runs) == frame_count:
        return [run["center"] for run in runs]
    # Fallback: choose prominent local maxima with a minimum spacing.
    min_distance = width / max(1, frame_count) * 0.62
    peaks = []
    for x in range(1, width - 1):
        if smooth[x] >= smooth[x - 1] and smooth[x] >= smooth[x + 1] and smooth[x] > threshold:
            peaks.append((smooth[x], x))
    peaks.sort(reverse=True)
    selected: list[int] = []
    for _, x in peaks:
        if all(abs(x - other) >= min_distance for other in selected):
            selected.append(x)
            if len(selected) == frame_count:
                break
    selected.sort()
    return [float(x) for x in selected]


def _clean_green_background(image: Image.Image) -> Image.Image:
    source = image.convert("RGBA")
    out = Image.new("RGBA", source.size, (0, 0, 0, 0))
    src = source.load()
    dst = out.load()
    for y in range(source.height):
        for x in range(source.width):
            red, green, blue, alpha = src[x, y]
            is_green = green > 95 and green > red * 1.15 and green > blue * 1.15
            if alpha >= 8 and not is_green:
                dst[x, y] = (red, green, blue, alpha)
    return out


def _threshold_alpha(image: Image.Image, minimum_alpha: int) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A").point(lambda value: 255 if value >= minimum_alpha else 0)
    rgba.putalpha(alpha)
    return rgba


def _keep_largest_alpha_component(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    if alpha.getbbox() is None:
        return image
    components = _alpha_components(alpha)
    if not components:
        return image
    main = max(components, key=lambda item: item["area"])
    mask = Image.new("L", image.size, 0)
    mask_pixels = mask.load()
    for x, y in main["pixels"]:
        mask_pixels[x, y] = 255
    out = image.copy()
    out.putalpha(mask)
    return out


def _alpha_components(alpha: Image.Image) -> list[dict[str, Any]]:
    pixels = alpha.load()
    width, height = alpha.size
    seen: set[tuple[int, int]] = set()
    components: list[dict[str, Any]] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pixels[x, y] == 0:
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
            if len(points) >= 12:
                components.append({"area": len(points), "bbox": (left, top, right, bottom), "pixels": points})
    return components


def _normalize_cells(
    frames: list[Image.Image],
    frame_size: tuple[int, int],
    target_height: int,
    preserve_vertical_arc: bool,
) -> list[Image.Image]:
    boxes = [_alpha_bbox(frame) for frame in frames]
    max_height = max(box[3] - box[1] for box in boxes)
    max_width = max(box[2] - box[0] for box in boxes)
    scale = min(target_height / max_height, frame_size[0] * 0.88 / max_width)
    source_ground = max(box[3] for box in boxes)
    source_center = sorted((box[0] + box[2]) * 0.5 for box in boxes)[len(boxes) // 2]
    target_ground = frame_size[1] - 10
    target_center = frame_size[0] // 2

    normalized = []
    for frame, box in zip(frames, boxes):
        crop = frame.crop(box)
        resized = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))), Image.Resampling.LANCZOS)
        resized = resized.filter(ImageFilter.UnsharpMask(radius=1.0, percent=115, threshold=4))
        canvas = Image.new("RGBA", frame_size, (0, 0, 0, 0))
        frame_center = (box[0] + box[2]) * 0.5
        x = round(target_center + (frame_center - source_center) * scale - resized.width * 0.5)
        if preserve_vertical_arc:
            y = round(target_ground - (source_ground - box[1]) * scale)
        else:
            y = target_ground - resized.height
        canvas.alpha_composite(resized, (x, y))
        normalized.append(_keep_inside_canvas(canvas, 2))
    return normalized


def _make_idle_frames(source_path: Path) -> list[Path]:
    source = Image.open(source_path).convert("RGBA")
    tmp_dir = source_path.parent.parent / "_idle_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, offset in enumerate([0, -1, -2, -1]):
        frame = _offset_upper_body(source, offset)
        path = tmp_dir / f"idle_{index:03d}.png"
        frame.save(path)
        paths.append(path)
    return paths


def _offset_upper_body(source: Image.Image, offset_y: int) -> Image.Image:
    bbox = _alpha_bbox(source)
    split = bbox[1] + round((bbox[3] - bbox[1]) * 0.58)
    output = Image.new("RGBA", source.size, (0, 0, 0, 0))
    output.alpha_composite(source.crop((0, split, source.width, source.height)), (0, split))
    output.alpha_composite(source.crop((0, 0, source.width, split + 10)), (0, offset_y))
    return output


def _write_action_artifacts(action: str, frame_paths: list[Path], action_dir: Path) -> dict[str, Any]:
    spec = ACTION_SPECS[action]
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    final_paths = []
    for index, source in enumerate(frame_paths):
        dest = frames_dir / f"{action}_{index:03d}.png"
        if source.resolve() != dest.resolve():
            Image.open(source).convert("RGBA").save(dest)
        final_paths.append(dest)
    if frame_paths and frame_paths[0].parent.name == "_idle_tmp":
        shutil.rmtree(frame_paths[0].parent, ignore_errors=True)
    make_sprite_sheet(final_paths, action_dir / "spritesheet.png", columns=len(final_paths))
    make_preview_gif(final_paths, action_dir / "preview.gif", duration_ms=round(1000 / spec["fps"]), loop=spec["loop"])
    make_contact_sheet(final_paths, action_dir / "contact_sheet.png", columns=min(6, len(final_paths)))
    metrics = _action_metrics(final_paths, loop=spec["loop"])
    report = {
        "action": action,
        "status": "production_ready" if metrics["production_ready"] else "needs_manual_review",
        "frame_count": len(final_paths),
        "frame_size": {"width": Image.open(final_paths[0]).width, "height": Image.open(final_paths[0]).height},
        "phase_names": PHASES[action],
        "metrics": metrics,
        "production_ready": metrics["production_ready"],
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return {
        "action": action,
        "frame_count": len(final_paths),
        "frame_size": report["frame_size"],
        "production_ready": metrics["production_ready"],
        "status": report["status"],
        "phase_names": PHASES[action],
        "frames": [f"actions/{action}/frames/{action}_{index:03d}.png" for index in range(len(final_paths))],
        "spritesheet": f"actions/{action}/spritesheet.png",
        "preview_gif": f"actions/{action}/preview.gif",
        "contact_sheet": f"actions/{action}/contact_sheet.png",
        "production_ready_report": f"actions/{action}/production_ready_report.json",
        "runtime": _action_runtime(action, final_paths),
    }


def _action_runtime(action: str, paths: list[Path]) -> dict[str, Any]:
    spec = ACTION_SPECS[action]
    visible = _union_bbox(paths)
    return {
        "fps": spec["fps"],
        "loop": spec["loop"],
        "source_frame_count": len(paths),
        "playback_frame_count": len(paths),
        "playback_frame_indices": list(range(len(paths))),
        "origin": {"x": Image.open(paths[0]).width // 2, "y": Image.open(paths[0]).height - 10},
        "visible_bbox": {"x": visible[0], "y": visible[1], "width": visible[2] - visible[0], "height": visible[3] - visible[1]},
        "collision_box": {"x": 94, "y": 80, "width": 72, "height": 294},
        "hit_frames": [5, 6] if action == "attack_sword_light" else [],
    }


def _action_metrics(paths: list[Path], loop: bool) -> dict[str, Any]:
    images = [Image.open(path).convert("RGBA") for path in paths]
    boxes = [_alpha_bbox(image) for image in images]
    sizes = sorted({image.size for image in images})
    edge_touch = []
    for index, (image, box) in enumerate(zip(images, boxes)):
        if box[0] <= 1 or box[1] <= 1 or box[2] >= image.width - 1 or box[3] >= image.height - 1:
            edge_touch.append(index)
    deltas = [_mean_delta(images[index], images[index + 1]) for index in range(len(images) - 1)]
    loop_delta = _mean_delta(images[-1], images[0]) if loop and len(images) > 1 else None
    production_ready = len(sizes) == 1 and not edge_touch and all(box is not None for box in boxes)
    return {
        "same_size": len(sizes) == 1,
        "alpha_edge_touch_frames": edge_touch,
        "mean_step_delta": round(sum(deltas) / max(1, len(deltas)), 3),
        "loop_delta": loop_delta,
        "ground_y_range": max(box[3] for box in boxes) - min(box[3] for box in boxes),
        "production_ready": production_ready,
    }


def _mean_delta(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a, b).convert("L")
    return ImageStat.Stat(diff).mean[0]


def _write_pack_review(output_dir: Path, actions: dict[str, Any]) -> dict[str, Any]:
    review_dir = output_dir / "pack_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for action in actions:
        paths = [output_dir / frame for frame in actions[action]["frames"]]
        rows.append((action, paths))
    contact = _make_all_actions_contact(rows, review_dir / "all_actions_contact_sheet.png")
    report = {"actions": {action: actions[action]["status"] for action in actions}}
    _write_text(review_dir / "quality_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    godot_manifest = {"route": "character_sprite_asset_pack", "actions": {k: {"frame_count": v["frame_count"], "loop": v["runtime"]["loop"]} for k, v in actions.items()}}
    _write_text(review_dir / "godot_import_manifest.json", json.dumps(godot_manifest, indent=2, ensure_ascii=False) + "\n")
    return {"contact_sheet": str(contact), "quality_report": report}


def _make_all_actions_contact(rows: list[tuple[str, list[Path]]], output: Path) -> Path:
    thumbs = []
    labels = []
    for action, paths in rows:
        for index, path in enumerate(paths):
            image = Image.open(path).convert("RGBA")
            bbox = _alpha_bbox(image)
            crop = image.crop(bbox)
            thumb = Image.new("RGBA", (150, 210), (245, 245, 245, 255))
            crop.thumbnail((120, 170), Image.Resampling.LANCZOS)
            thumb.alpha_composite(crop, ((150 - crop.width) // 2, 18))
            thumbs.append(thumb)
            labels.append(f"{action} {index:02d}")
    columns = 12
    rows_count = (len(thumbs) + columns - 1) // columns
    canvas = Image.new("RGBA", (columns * 150, rows_count * 236), (245, 245, 245, 255))
    draw = ImageDraw.Draw(canvas)
    for index, thumb in enumerate(thumbs):
        x = (index % columns) * 150
        y = (index // columns) * 236
        canvas.alpha_composite(thumb, (x, y))
        draw.text((x + 4, y + 212), labels[index], fill=(30, 30, 30, 255))
    canvas.save(output)
    return output


def _production_gate(actions: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    checks = {f"{action}_production_ready": bool(info["production_ready"]) for action, info in actions.items()}
    checks["godot_pack_manifest_ready"] = True
    ready = all(checks.values())
    return {
        "target": "nun_skirt_boots_character_sprite_asset_pack",
        "decision": "production_ready" if ready else "needs_manual_review",
        "production_ready": ready,
        "checks": checks,
        "manual_review_required": [
            "Open preview GIFs and Godot viewer to confirm real motion feel.",
            "Confirm attack sword/effect separation is sufficient for the target game.",
        ],
        "review_contact_sheet": "pack_review/all_actions_contact_sheet.png",
    }


def _runtime_manifest(actions: dict[str, Any]) -> dict[str, Any]:
    return {"actions": {action: info["runtime"] for action, info in actions.items()}}


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("empty alpha frame")
    return bbox


def _union_bbox(paths: list[Path]) -> tuple[int, int, int, int]:
    boxes = [_alpha_bbox(Image.open(path).convert("RGBA")) for path in paths]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


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
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out.alpha_composite(image, (dx, dy))
    return out


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _notes(manifest: dict[str, Any]) -> str:
    return f"""# {manifest['asset_name']}

Generated Nun + skirt/boots 2D game sprite pack.

- route: `{manifest['route']}`
- production_ready: `{manifest['production_ready']}`
- actions: `{', '.join(manifest['actions'].keys())}`
- review: `pack_review/all_actions_contact_sheet.png`

This pack is intended for Godot `AnimatedSprite2D` review. The current attack is a composed
sprite action; separate sword/effect layers are a follow-up if the composed action is accepted.
"""


if __name__ == "__main__":
    main()
