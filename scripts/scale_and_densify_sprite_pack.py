from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif, make_preview_webp
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="Scale a character sprite pack and insert in-between frames.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--frame-width", required=True, type=int)
    parser.add_argument("--frame-height", required=True, type=int)
    parser.add_argument("--inbetweens", default=1, type=int)
    parser.add_argument("--asset-name")
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    manifest = scale_and_densify_pack(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        frame_size=(args.frame_width, args.frame_height),
        inbetweens=args.inbetweens,
        asset_name=args.asset_name,
        clean=args.clean,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def scale_and_densify_pack(
    manifest_path: Path,
    output_dir: Path,
    frame_size: tuple[int, int],
    inbetweens: int = 1,
    asset_name: str | None = None,
    clean: bool = True,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    source_dir = manifest_path.parent
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("route") != "character_sprite_asset_pack":
        raise ValueError(f"unsupported manifest route: {source_manifest.get('route')}")
    if inbetweens < 0:
        raise ValueError("--inbetweens must be >= 0")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = dict(source_manifest)
    manifest["asset_name"] = asset_name or f"{source_manifest.get('asset_name', 'sprite_pack')}_scaled_densified"
    manifest["actions"] = {}
    manifest["production_ready"] = False
    manifest["scale_and_densify"] = {
        "source_manifest": _display_path(manifest_path),
        "frame_size": {"width": frame_size[0], "height": frame_size[1]},
        "inbetweens": inbetweens,
    }

    actions_dir = output_dir / "actions"
    actions_dir.mkdir(parents=True, exist_ok=True)
    for action, info in source_manifest.get("actions", {}).items():
        manifest["actions"][action] = _write_scaled_densified_action(
            source_dir=source_dir,
            output_dir=output_dir,
            action=action,
            info=info,
            frame_size=frame_size,
            inbetweens=inbetweens,
        )

    _write_pack_review(output_dir, manifest)
    _write_json(output_dir / "manifest.json", manifest)
    _write_json(output_dir / "runtime_manifest.json", {"actions": {k: v["runtime"] for k, v in manifest["actions"].items()}})
    production_gate = manifest.get("production_gate")
    if isinstance(production_gate, dict):
        production_gate = dict(production_gate)
        production_gate["decision"] = "needs_visual_retake_or_manual_review"
        production_gate["production_ready"] = False
        _write_json(output_dir / "production_gate.json", production_gate)
    return manifest


def _write_scaled_densified_action(
    source_dir: Path,
    output_dir: Path,
    action: str,
    info: dict[str, Any],
    frame_size: tuple[int, int],
    inbetweens: int,
) -> dict[str, Any]:
    action_dir = output_dir / "actions" / action
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    source_frames = [Image.open(source_dir / rel).convert("RGBA") for rel in info.get("frames", [])]
    if not source_frames:
        raise ValueError(f"action has no frames: {action}")
    scaled_frames = [_scale_frame(frame, frame_size) for frame in source_frames]
    loop = bool(info.get("runtime", {}).get("loop", True))
    densified_frames = _densify_frames(scaled_frames, inbetweens, loop=loop)

    frame_paths: list[Path] = []
    for index, frame in enumerate(densified_frames):
        path = frames_dir / f"{action}_{index:03d}.png"
        frame.save(path)
        frame_paths.append(path)

    old_fps = float(info.get("runtime", {}).get("fps", 8.0))
    new_fps = _scaled_fps(old_fps, len(source_frames), len(densified_frames))
    make_sprite_sheet(frame_paths, action_dir / "spritesheet.png", columns=len(frame_paths))
    make_preview_gif(frame_paths, action_dir / "preview.gif", duration_ms=round(1000 / new_fps), loop=loop)
    make_preview_webp(frame_paths, action_dir / "preview.webp", duration_ms=round(1000 / new_fps), loop=loop)
    make_contact_sheet(frame_paths, action_dir / "contact_sheet.png", columns=min(6, len(frame_paths)))

    runtime = _runtime_from_frames(
        info.get("runtime", {}),
        frame_paths,
        frame_size,
        old_size=source_frames[0].size,
        playback_factor=inbetweens + 1,
    )
    runtime["fps"] = new_fps
    runtime["source_frame_count"] = len(source_frames)
    runtime["playback_frame_count"] = len(densified_frames)
    runtime["playback_frame_indices"] = list(range(len(densified_frames)))

    production_report = {
        "action": action,
        "status": "needs_manual_review",
        "frame_count": len(frame_paths),
        "frame_size": {"width": frame_size[0], "height": frame_size[1]},
        "metrics": _local_action_metrics(frame_paths, loop=loop),
        "production_ready": False,
    }
    _write_json(action_dir / "production_ready_report.json", production_report)

    return {
        "action": action,
        "frame_count": len(frame_paths),
        "frame_size": {"width": frame_size[0], "height": frame_size[1]},
        "production_ready": False,
        "status": "needs_manual_review",
        "phase_names": _densified_phase_names(info.get("phase_names", []), inbetweens, loop=loop),
        "frames": [f"actions/{action}/frames/{path.name}" for path in frame_paths],
        "spritesheet": f"actions/{action}/spritesheet.png",
        "preview_gif": f"actions/{action}/preview.gif",
        "preview_webp": f"actions/{action}/preview.webp",
        "contact_sheet": f"actions/{action}/contact_sheet.png",
        "production_ready_report": f"actions/{action}/production_ready_report.json",
        "runtime": runtime,
    }


def _scale_frame(frame: Image.Image, frame_size: tuple[int, int]) -> Image.Image:
    resized = frame.resize(frame_size, Image.Resampling.LANCZOS)
    return resized.filter(ImageFilter.UnsharpMask(radius=1.0, percent=105, threshold=4))


def _densify_frames(frames: list[Image.Image], inbetweens: int, loop: bool) -> list[Image.Image]:
    if inbetweens == 0:
        return frames
    output: list[Image.Image] = []
    pair_count = len(frames) if loop else len(frames) - 1
    for index in range(pair_count):
        current = frames[index]
        following = frames[(index + 1) % len(frames)]
        output.append(current)
        for step in range(1, inbetweens + 1):
            amount = step / (inbetweens + 1)
            output.append(Image.blend(current, following, amount))
    if not loop:
        output.append(frames[-1])
    return output


def _scaled_fps(old_fps: float, old_count: int, new_count: int) -> float:
    if old_count <= 0:
        return old_fps
    return round(old_fps * new_count / old_count, 3)


def _runtime_from_frames(
    source_runtime: dict[str, Any],
    frame_paths: list[Path],
    frame_size: tuple[int, int],
    old_size: tuple[int, int],
    playback_factor: int,
) -> dict[str, Any]:
    visible = _union_bbox(frame_paths)
    scale_x = frame_size[0] / old_size[0]
    scale_y = frame_size[1] / old_size[1]
    collision = source_runtime.get("collision_box", {})
    return {
        "fps": float(source_runtime.get("fps", 8.0)),
        "loop": bool(source_runtime.get("loop", True)),
        "source_frame_count": int(source_runtime.get("source_frame_count", len(frame_paths))),
        "playback_frame_count": len(frame_paths),
        "playback_frame_indices": list(range(len(frame_paths))),
        "origin": {
            "x": round(float(source_runtime.get("origin", {}).get("x", old_size[0] / 2)) * scale_x),
            "y": round(float(source_runtime.get("origin", {}).get("y", old_size[1] - 10)) * scale_y),
        },
        "visible_bbox": {"x": visible[0], "y": visible[1], "width": visible[2] - visible[0], "height": visible[3] - visible[1]},
        "collision_box": {
            "x": round(float(collision.get("x", 0)) * scale_x),
            "y": round(float(collision.get("y", 0)) * scale_y),
            "width": round(float(collision.get("width", 0)) * scale_x),
            "height": round(float(collision.get("height", 0)) * scale_y),
        },
        "hit_frames": _densified_hit_frames(source_runtime.get("hit_frames", []), len(frame_paths), playback_factor=playback_factor),
    }


def _densified_hit_frames(hit_frames: list[Any], frame_count: int, playback_factor: int) -> list[int]:
    expanded = set()
    for frame in hit_frames:
        try:
            index = int(frame)
        except (TypeError, ValueError):
            continue
        expanded.add(min(frame_count - 1, index * playback_factor))
    return sorted(expanded)


def _densified_phase_names(phase_names: list[Any], inbetweens: int, loop: bool) -> list[str]:
    names = [str(name) for name in phase_names]
    if not names or inbetweens == 0:
        return names
    output: list[str] = []
    pair_count = len(names) if loop else len(names) - 1
    for index in range(pair_count):
        current = names[index]
        following = names[(index + 1) % len(names)]
        output.append(current)
        for step in range(1, inbetweens + 1):
            output.append(f"{current}_to_{following}_{step}")
    if not loop:
        output.append(names[-1])
    return output


def _write_pack_review(output_dir: Path, manifest: dict[str, Any]) -> None:
    review_dir = output_dir / "pack_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for action, info in manifest["actions"].items():
        frame_paths = [output_dir / frame for frame in info.get("frames", [])]
        rows.append((action, frame_paths))
        make_contact_sheet(frame_paths, review_dir / f"{action}_fullres_contact_sheet.png", columns=min(4, len(frame_paths)))
    _write_all_actions_fullres(rows, review_dir / "all_actions_contact_sheet_fullres.png")
    _write_json(review_dir / "quality_report.json", {"actions": {action: "needs_manual_review" for action in manifest["actions"]}})
    _write_json(
        review_dir / "godot_import_manifest.json",
        {"route": "character_sprite_asset_pack", "actions": {k: {"frame_count": v["frame_count"], "loop": v["runtime"]["loop"]} for k, v in manifest["actions"].items()}},
    )


def _write_all_actions_fullres(rows: list[tuple[str, list[Path]]], output_path: Path) -> None:
    cells: list[tuple[str, Path]] = []
    for action, paths in rows:
        for index, path in enumerate(paths):
            cells.append((f"{action} {index:02d}", path))
    first = Image.open(cells[0][1]).convert("RGBA")
    width, height = first.size
    label_height = max(28, round(height * 0.05))
    columns = 4
    row_count = (len(cells) + columns - 1) // columns
    canvas = Image.new("RGBA", (columns * width, row_count * (height + label_height)), (245, 245, 245, 255))
    draw = ImageDraw.Draw(canvas)
    for index, (label, path) in enumerate(cells):
        image = Image.open(path).convert("RGBA")
        x = (index % columns) * width
        y = (index // columns) * (height + label_height)
        canvas.alpha_composite(image, (x, y))
        draw.text((x + 8, y + height + 6), label, fill=(30, 30, 30, 255))
    canvas.save(output_path)


def _local_action_metrics(frame_paths: list[Path], loop: bool) -> dict[str, Any]:
    images = [Image.open(path).convert("RGBA") for path in frame_paths]
    step_deltas = [_mean_delta(images[index], images[index + 1]) for index in range(len(images) - 1)]
    loop_delta = _mean_delta(images[-1], images[0]) if loop and len(images) > 1 else None
    return {
        "step_delta_values": [round(value, 4) for value in step_deltas],
        "mean_step_delta": round(sum(step_deltas) / max(1, len(step_deltas)), 4),
        "loop_delta": None if loop_delta is None else round(loop_delta, 4),
    }


def _union_bbox(frame_paths: list[Path]) -> tuple[int, int, int, int]:
    boxes = []
    for path in frame_paths:
        bbox = Image.open(path).convert("RGBA").getchannel("A").getbbox()
        if bbox:
            boxes.append(bbox)
    if not boxes:
        raise ValueError("frames are empty")
    return (min(box[0] for box in boxes), min(box[1] for box in boxes), max(box[2] for box in boxes), max(box[3] for box in boxes))


def _mean_delta(a: Image.Image, b: Image.Image) -> float:
    return ImageStat.Stat(ImageChops.difference(a, b).convert("L")).mean[0]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


if __name__ == "__main__":
    main()
