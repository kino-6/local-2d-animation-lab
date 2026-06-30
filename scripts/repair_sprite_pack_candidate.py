from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif, make_preview_webp
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


GEOMETRY_ACTIONS = {"walk", "run", "hurt", "attack_sword_light"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair a high-resolution sprite-pack candidate.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--stabilize-geometry", action="store_true")
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    report = repair_pack(args.manifest, args.output_dir, stabilize_geometry=args.stabilize_geometry, clean=args.clean)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def repair_pack(
    manifest_path: Path,
    output_dir: Path,
    stabilize_geometry: bool = False,
    clean: bool = True,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    source_dir = manifest_path.parent
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(source_dir, output_dir)

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    actions = manifest.get("actions", {})
    idle_frames = _load_action_frames(output_dir, actions["idle"]) if "idle" in actions else []

    repair_report: dict[str, Any] = {"source_manifest": _display_path(manifest_path), "actions": {}}
    for action, info in actions.items():
        frames = _load_action_frames(output_dir, info)
        before = _local_metrics(frames, loop=bool(info.get("runtime", {}).get("loop", True)))
        frames = _replace_blended_inbetweens_with_holds(frames, info.get("phase_names", []))
        frames = [_reduce_tonal_clipping_fast(frame) for frame in frames]
        if action == "hurt":
            frames = [_keep_largest_alpha_component(frame) for frame in frames]
        if stabilize_geometry and action in GEOMETRY_ACTIONS:
            frames = _stabilize_geometry(frames, action)
            frames = [_threshold_alpha_floor(frame, minimum=8) for frame in frames]
            frames = [_reduce_tonal_clipping_fast(frame) for frame in frames]
        if action == "jump" and idle_frames:
            frames = _repair_recovery_tail(frames, idle_frames)
        if action == "hurt":
            frames = [_keep_largest_alpha_component(frame) for frame in frames]
        frames = [_keep_inside_canvas(_threshold_alpha_floor(frame, minimum=8), margin=4) for frame in frames]
        _save_action_frames(output_dir, info, frames)
        _regenerate_action_artifacts(output_dir, action, info)
        after = _local_metrics(frames, loop=bool(info.get("runtime", {}).get("loop", True)))
        repair_report["actions"][action] = {"before": before, "after": after}

    _regenerate_pack_review(output_dir, manifest)
    manifest["production_ready"] = False
    manifest["repair_pipeline"] = {
        "source_manifest": _display_path(manifest_path),
            "operations": [
                "fast foreground tone clipping reduction",
                "largest-component cleanup for hurt",
                "optional bbox geometry stabilization for walk/run/hurt/attack_sword_light",
                "jump recovery tail replacement from idle",
            ],
            "stabilize_geometry": stabilize_geometry,
        }
    production_gate = manifest.get("production_gate")
    if isinstance(production_gate, dict):
        production_gate["decision"] = "needs_visual_gate"
        production_gate["production_ready"] = False
    _write_json(output_dir / "manifest.json", manifest)
    _write_json(output_dir / "runtime_manifest.json", {"actions": {k: v["runtime"] for k, v in actions.items()}})
    if isinstance(production_gate, dict):
        _write_json(output_dir / "production_gate.json", production_gate)
    _write_json(output_dir / "pack_review" / "repair_report.json", repair_report)
    return repair_report


def _load_action_frames(output_dir: Path, info: dict[str, Any]) -> list[Image.Image]:
    return [Image.open(output_dir / frame).convert("RGBA") for frame in info.get("frames", [])]


def _save_action_frames(output_dir: Path, info: dict[str, Any], frames: list[Image.Image]) -> None:
    for rel, frame in zip(info.get("frames", []), frames):
        frame.save(output_dir / rel)


def _stabilize_geometry(frames: list[Image.Image], action: str) -> list[Image.Image]:
    boxes = [_alpha_bbox(frame) for frame in frames]
    widths = [box[2] - box[0] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    centers = [(box[0] + box[2]) * 0.5 for box in boxes]
    bottoms = [box[3] for box in boxes]
    target_width = round(median(widths))
    target_height = round(median(heights))
    if action == "attack_sword_light":
        target_width = min(round(median(widths) * 1.08), min(widths) + 112)
        target_height = min(round(median(heights) * 1.04), min(heights) + 48)
    if action == "run":
        target_width = min(round(median(widths)), min(widths) + 112)
        target_height = min(round(median(heights)), min(heights) + 48)
    target_center = median(centers)
    target_bottom = median(bottoms)
    fixed = []
    for frame, box in zip(frames, boxes):
        crop = frame.crop(box)
        crop = crop.resize((max(1, target_width), max(1, target_height)), Image.Resampling.LANCZOS)
        crop = crop.filter(ImageFilter.UnsharpMask(radius=0.8, percent=105, threshold=4))
        canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        x = round(target_center - crop.width * 0.5)
        y = round(target_bottom - crop.height)
        canvas.alpha_composite(crop, (x, y))
        fixed.append(canvas)
    return fixed


def _repair_recovery_tail(frames: list[Image.Image], idle_frames: list[Image.Image]) -> list[Image.Image]:
    if len(frames) < 4:
        return frames
    idle = idle_frames[0]
    fixed = list(frames)
    fixed[-2] = idle.copy()
    fixed[-1] = idle.copy()
    return fixed


def _replace_blended_inbetweens_with_holds(frames: list[Image.Image], phase_names: list[Any]) -> list[Image.Image]:
    if len(phase_names) != len(frames):
        return frames
    fixed = list(frames)
    previous_key: Image.Image | None = None
    for index, (frame, phase_name) in enumerate(zip(frames, phase_names)):
        name = str(phase_name)
        if "_to_" not in name:
            previous_key = frame
            continue
        if previous_key is not None:
            fixed[index] = previous_key.copy()
        elif index + 1 < len(frames):
            fixed[index] = frames[index + 1].copy()
    return fixed


def _reduce_tonal_clipping_fast(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rgb = rgba.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(0.985)
    lut = []
    for value in range(256):
        if value >= 236:
            lut.append(round(236 + (value - 236) * 0.28))
        elif value <= 18:
            lut.append(round(7 + value * 0.72))
        else:
            lut.append(value)
    out = rgb.point(lut * 3).convert("RGBA")
    out.putalpha(alpha)
    return out


def _threshold_alpha_floor(image: Image.Image, minimum: int) -> Image.Image:
    out = image.convert("RGBA")
    alpha = out.getchannel("A").point(lambda value: 0 if value < minimum else value)
    out.putalpha(alpha)
    return out


def _keep_largest_alpha_component(image: Image.Image) -> Image.Image:
    components = _alpha_components(image.getchannel("A"))
    if not components:
        return image
    main = max(components, key=lambda component: component["area"])
    mask = Image.new("L", image.size, 0)
    mask_pixels = mask.load()
    for x, y in main["pixels"]:
        mask_pixels[x, y] = 255
    out = image.copy()
    out.putalpha(mask)
    return out


def _regenerate_action_artifacts(output_dir: Path, action: str, info: dict[str, Any]) -> None:
    frame_paths = [output_dir / frame for frame in info.get("frames", [])]
    action_dir = output_dir / "actions" / action
    runtime = info.get("runtime", {})
    fps = float(runtime.get("fps", 8.0))
    loop = bool(runtime.get("loop", True))
    make_sprite_sheet(frame_paths, action_dir / "spritesheet.png", columns=len(frame_paths))
    make_preview_gif(frame_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=loop)
    make_preview_webp(frame_paths, action_dir / "preview.webp", duration_ms=round(1000 / fps), loop=loop)
    make_contact_sheet(frame_paths, action_dir / "contact_sheet.png", columns=min(6, len(frame_paths)))


def _regenerate_pack_review(output_dir: Path, manifest: dict[str, Any]) -> None:
    review_dir = output_dir / "pack_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    cells: list[tuple[str, Path]] = []
    for action, info in manifest.get("actions", {}).items():
        frame_paths = [output_dir / frame for frame in info.get("frames", [])]
        make_contact_sheet(frame_paths, review_dir / f"{action}_fullres_contact_sheet.png", columns=min(4, len(frame_paths)))
        for index, frame_path in enumerate(frame_paths):
            cells.append((f"{action} {index:02d}", frame_path))
    if not cells:
        return
    first = Image.open(cells[0][1]).convert("RGBA")
    label_height = max(28, round(first.height * 0.05))
    columns = 4
    rows = (len(cells) + columns - 1) // columns
    canvas = Image.new("RGBA", (columns * first.width, rows * (first.height + label_height)), (245, 245, 245, 255))
    draw = ImageDraw.Draw(canvas)
    for index, (label, frame_path) in enumerate(cells):
        frame = Image.open(frame_path).convert("RGBA")
        x = (index % columns) * first.width
        y = (index // columns) * (first.height + label_height)
        canvas.alpha_composite(frame, (x, y))
        draw.text((x + 8, y + first.height + 6), label, fill=(30, 30, 30, 255))
    canvas.save(review_dir / "all_actions_contact_sheet_fullres.png")


def _local_metrics(frames: list[Image.Image], loop: bool) -> dict[str, Any]:
    boxes = [_alpha_bbox(frame) for frame in frames]
    widths = [box[2] - box[0] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    centers = [(box[0] + box[2]) * 0.5 for box in boxes]
    deltas = [_mean_delta(frames[index], frames[index + 1]) for index in range(len(frames) - 1)]
    loop_delta = _mean_delta(frames[-1], frames[0]) if loop and len(frames) > 1 else None
    return {
        "bbox_width_range": round(max(widths) - min(widths), 3),
        "bbox_height_range": round(max(heights) - min(heights), 3),
        "center_x_range": round(max(centers) - min(centers), 3),
        "mean_step_delta": round(sum(deltas) / max(1, len(deltas)), 4),
        "loop_delta": None if loop_delta is None else round(loop_delta, 4),
    }


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("empty alpha frame")
    return bbox


def _alpha_components(alpha: Image.Image) -> list[dict[str, Any]]:
    pixels = alpha.load()
    width, height = alpha.size
    seen: set[tuple[int, int]] = set()
    components: list[dict[str, Any]] = []
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


def _mean_delta(a: Image.Image, b: Image.Image) -> float:
    return ImageStat.Stat(ImageChops.difference(a, b).convert("L")).mean[0]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


if __name__ == "__main__":
    main()
