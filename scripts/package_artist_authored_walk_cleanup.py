from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

try:
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


ROUTE = "artist_authored_8frame_walk_cleanup"
ROUTE_STATUS = "requires_artist_authored_rough"
DEFAULT_OUTPUT = Path("outputs/adoptable/artist_authored_8frame_walk_cleanup")
PHASE_NAMES = [
    "contact",
    "down",
    "passing",
    "up",
    "opposite_contact",
    "opposite_down",
    "opposite_passing",
    "opposite_up",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package and lightly clean one artist-authored 8-frame side-view walk rough."
    )
    parser.add_argument("--rough-frames-dir", required=True, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--reference-image", default=None, type=Path)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--frame-width", default=None, type=int)
    parser.add_argument("--frame-height", default=None, type=int)
    parser.add_argument("--remove-background", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--background-threshold", default=88, type=int)
    parser.add_argument("--background-min-channel", default=205, type=int)
    parser.add_argument("--source-kind", default="artist_authored_rough")
    parser.add_argument("--source-note", default="")
    parser.add_argument("--game-preview-heights", default="128,192,256")
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    manifest = package_artist_authored_walk_cleanup(
        rough_frames_dir=args.rough_frames_dir,
        output_dir=args.output_dir,
        reference_image=args.reference_image,
        fps=args.fps,
        frame_width=args.frame_width,
        frame_height=args.frame_height,
        remove_background=args.remove_background,
        background_threshold=args.background_threshold,
        background_min_channel=args.background_min_channel,
        source_kind=args.source_kind,
        source_note=args.source_note,
        game_preview_heights=_parse_preview_heights(args.game_preview_heights),
        clean=args.clean,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def package_artist_authored_walk_cleanup(
    rough_frames_dir: Path,
    output_dir: Path = DEFAULT_OUTPUT,
    reference_image: Path | None = None,
    fps: int = 8,
    frame_width: int | None = None,
    frame_height: int | None = None,
    remove_background: bool = True,
    background_threshold: int = 88,
    background_min_channel: int = 205,
    source_kind: str = "artist_authored_rough",
    source_note: str = "",
    game_preview_heights: list[int] | None = None,
    clean: bool = True,
) -> dict[str, Any]:
    source_paths = sorted(rough_frames_dir.glob("*.png"), key=_frame_index)
    if len(source_paths) != 8:
        raise ValueError(f"Route {ROUTE} requires exactly 8 PNG rough frames, found {len(source_paths)}.")

    if reference_image is not None and not reference_image.exists():
        raise FileNotFoundError(f"Reference image not found: {reference_image}")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    first = Image.open(source_paths[0]).convert("RGBA")
    out_width = frame_width or first.width
    out_height = frame_height or first.height

    frame_entries: list[dict[str, Any]] = []
    cleanup_reports: list[dict[str, Any]] = []
    output_paths: list[Path] = []
    for index, source in enumerate(source_paths):
        cleaned, report = _clean_rough_frame(
            source,
            out_width,
            out_height,
            remove_background=remove_background,
            background_threshold=background_threshold,
            background_min_channel=background_min_channel,
        )
        output = frames_dir / f"walk_{index:03d}.png"
        cleaned.save(output)
        output_paths.append(output)
        cleanup_reports.append({"index": index, "source": str(source), **report})
        frame_entries.append(
            {
                "index": index,
                "phase": PHASE_NAMES[index],
                "file": str(output.relative_to(output_dir)).replace("\\", "/"),
                "duration_ms": round(1000 / fps),
                "bbox": report["alpha_bbox"],
            }
        )

    game_preview_heights = game_preview_heights if game_preview_heights is not None else [128, 192, 256]
    spritesheet = make_sprite_sheet(output_paths, output_dir / "spritesheet.png", columns=8)
    preview_gif = make_preview_gif(output_paths, output_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    contact_sheet = make_contact_sheet(output_paths, output_dir / "contact_sheet.png", columns=4)
    game_previews = _write_game_previews(output_paths, output_dir, game_preview_heights, fps)
    cleanup_report = {
        "route": ROUTE,
        "frame_count": len(output_paths),
        "reports": cleanup_reports,
        "warnings": _cleanup_warnings(cleanup_reports),
    }
    cleanup_report_path = output_dir / "cleanup_report.json"
    cleanup_report_path.write_text(json.dumps(cleanup_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    game_readiness = _game_readiness_metrics(frame_entries, out_width, out_height, game_previews)
    production_gate = _production_gate(game_readiness, source_kind)
    production_review_path = output_dir / "production_review.json"
    production_review_path.write_text(json.dumps(production_gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    production_review_md = output_dir / "production_review.md"
    production_review_md.write_text(_production_review_notes(production_gate), encoding="utf-8")

    manifest = {
        "route": ROUTE,
        "route_status": ROUTE_STATUS,
        "asset_kind": "2d_game_sprite",
        "source_kind": source_kind,
        "output_status": "cleanup_packaged_for_review",
        "frame_count": 8,
        "fps": fps,
        "phase_names": PHASE_NAMES,
        "frame_size": {"width": out_width, "height": out_height},
        "background": "transparent",
        "loop": True,
        "manual_art_required": True,
        "ai_scope": "cleanup_only_no_pose_or_silhouette_generation",
        "backend_usage": {
            "uses_comfyui": False,
            "uses_wan_video": False,
            "uses_controlnet": False,
            "uses_new_model_backend": False,
            "uses_120_frame_generation": False,
        },
        "outputs": {
            "frames": [str(path.relative_to(output_dir)).replace("\\", "/") for path in output_paths],
            "spritesheet": str(spritesheet.relative_to(output_dir)).replace("\\", "/"),
            "preview_gif": str(preview_gif.relative_to(output_dir)).replace("\\", "/"),
            "contact_sheet": str(contact_sheet.relative_to(output_dir)).replace("\\", "/"),
            "cleanup_report": str(cleanup_report_path.relative_to(output_dir)).replace("\\", "/"),
            "production_review": str(production_review_path.relative_to(output_dir)).replace("\\", "/"),
            "production_review_md": str(production_review_md.relative_to(output_dir)).replace("\\", "/"),
            "game_previews": game_previews,
        },
        "game_readiness": game_readiness,
        "production_gate": production_gate,
        "source": {
            "rough_frames_dir": str(rough_frames_dir),
            "reference_image": str(reference_image) if reference_image else None,
            "note": source_note,
        },
        "frames": frame_entries,
        "review": {
            "human_pose_control": True,
            "human_silhouette_control": True,
            "aseprite_friendly": True,
            "godot_friendly": True,
            "production_ready": False,
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "notes.md").write_text(_notes(manifest, cleanup_report), encoding="utf-8")
    return manifest


def _clean_rough_frame(
    source: Path,
    width: int,
    height: int,
    remove_background: bool,
    background_threshold: int,
    background_min_channel: int,
) -> tuple[Image.Image, dict[str, Any]]:
    image = Image.open(source).convert("RGBA")
    original_size = image.size
    if remove_background and _needs_background_removal(image):
        image, bg_report = _remove_connected_background(image, background_threshold, background_min_channel)
    else:
        bg_report = {"background_removed": False}
    image = _normalize_alpha(image)
    output = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    paste_x = (width - image.width) // 2
    paste_y = height - image.height
    output.alpha_composite(image, (paste_x, paste_y))
    bbox = output.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError(f"No visible foreground after cleanup: {source}")
    return output, {
        "original_size": {"width": original_size[0], "height": original_size[1]},
        "output_size": {"width": width, "height": height},
        "alpha_bbox": list(bbox),
        **bg_report,
    }


def _needs_background_removal(image: Image.Image) -> bool:
    alpha = image.getchannel("A")
    return alpha.getextrema() == (255, 255)


def _remove_connected_background(
    image: Image.Image,
    threshold: int,
    min_channel: int,
) -> tuple[Image.Image, dict[str, Any]]:
    rgb = _flatten(image).convert("RGB")
    background = _estimate_background(rgb)
    green_key = background[1] >= max(background[0], background[2]) + 80
    mask = _connected_background_mask(rgb, background, threshold, min_channel)
    rgba = rgb.convert("RGBA")
    pixels = rgba.load()
    mask_pixels = mask.load()
    removed = 0
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, _ = pixels[x, y]
            if mask_pixels[x, y]:
                pixels[x, y] = (red, green, blue, 0)
                removed += 1
            else:
                pixels[x, y] = (red, green, blue, 255)
    despilled = _despill_green_edges(rgba) if green_key else 0
    return rgba, {
        "background_removed": True,
        "estimated_background": list(background),
        "removed_pixel_count": removed,
        "despilled_pixel_count": despilled,
    }


def _normalize_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    rgba.putalpha(alpha)
    return rgba


def _cleanup_warnings(reports: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    boxes = [report["alpha_bbox"] for report in reports]
    if len({tuple(box) for box in boxes}) <= 2:
        warnings.append("Few unique alpha boxes; confirm the rough has visible walk motion.")
    for report in reports:
        left, top, right, bottom = report["alpha_bbox"]
        if right <= left or bottom <= top:
            warnings.append(f"Frame {report['index']} has invalid alpha bounds.")
    return warnings


def _write_game_previews(frame_paths: list[Path], output_dir: Path, heights: list[int], fps: int) -> dict[str, Any]:
    previews: dict[str, Any] = {}
    for height in heights:
        if height <= 0:
            raise ValueError(f"Preview height must be positive: {height}")
        preview_dir = output_dir / "game_previews" / f"height_{height}"
        frames_dir = preview_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        resized_paths: list[Path] = []
        for index, frame_path in enumerate(frame_paths):
            frame = Image.open(frame_path).convert("RGBA")
            width = round(frame.width * height / frame.height)
            resized = frame.resize((width, height), Image.Resampling.LANCZOS)
            resized_path = frames_dir / f"walk_{index:03d}.png"
            resized.save(resized_path)
            resized_paths.append(resized_path)
        spritesheet = make_sprite_sheet(resized_paths, preview_dir / "spritesheet.png", columns=8)
        preview_gif = make_preview_gif(
            resized_paths,
            preview_dir / "preview.gif",
            duration_ms=round(1000 / fps),
            loop=True,
        )
        contact_sheet = make_contact_sheet(resized_paths, preview_dir / "contact_sheet.png", columns=4)
        previews[f"height_{height}"] = {
            "frame_size": {"width": Image.open(resized_paths[0]).width, "height": height},
            "frames": [str(path.relative_to(output_dir)).replace("\\", "/") for path in resized_paths],
            "spritesheet": str(spritesheet.relative_to(output_dir)).replace("\\", "/"),
            "preview_gif": str(preview_gif.relative_to(output_dir)).replace("\\", "/"),
            "contact_sheet": str(contact_sheet.relative_to(output_dir)).replace("\\", "/"),
        }
    return previews


def _game_readiness_metrics(
    frame_entries: list[dict[str, Any]],
    frame_width: int,
    frame_height: int,
    game_previews: dict[str, Any],
) -> dict[str, Any]:
    boxes = [entry["bbox"] for entry in frame_entries]
    centers = [round((left + right) / 2, 2) for left, _top, right, _bottom in boxes]
    tops = [top for _left, top, _right, _bottom in boxes]
    bottoms = [bottom for _left, _top, _right, bottom in boxes]
    widths = [right - left for left, _top, right, _bottom in boxes]
    heights = [bottom - top for _left, top, _right, bottom in boxes]
    edge_touch = [
        index
        for index, (left, top, right, bottom) in enumerate(boxes)
        if left <= 0 or top <= 0 or right >= frame_width or bottom >= frame_height
    ]
    return {
        "fixed_best_rough": True,
        "generated_new_motion": False,
        "preview_heights": list(game_previews.keys()),
        "alpha_edge_touch_frames": edge_touch,
        "estimated_head_y_range": max(tops) - min(tops),
        "estimated_ground_y_range": max(bottoms) - min(bottoms),
        "estimated_center_x_range": round(max(centers) - min(centers), 2),
        "estimated_bbox_width_range": max(widths) - min(widths),
        "estimated_bbox_height_range": max(heights) - min(heights),
        "game_preview_review_required": True,
        "decision": "reviewable_rough_candidate_not_production",
    }


def _production_gate(game_readiness: dict[str, Any], source_kind: str) -> dict[str, Any]:
    checks = {
        "no_alpha_edge_touch": len(game_readiness["alpha_edge_touch_frames"]) == 0,
        "stable_ground_line": game_readiness["estimated_ground_y_range"] <= 10,
        "stable_head_height": game_readiness["estimated_head_y_range"] <= 16,
        "stable_body_height": game_readiness["estimated_bbox_height_range"] <= 12,
        "root_motion_not_excessive": game_readiness["estimated_center_x_range"] <= 36,
        "game_previews_exist": set(game_readiness["preview_heights"]) >= {"height_128", "height_192", "height_256"},
    }
    blocking = [name for name, passed in checks.items() if not passed]
    manual_polish_required = source_kind != "artist_authored_rough"
    manual_polish_queue = [
        "Open the 128px and 192px previews in Aseprite or Godot and confirm the loop in motion.",
        "Clean remaining per-frame line jitter around hair tips, sleeves, skirt hem, socks, and shoes.",
        "Check shoe contact and foot shape in contact/down frames.",
        "Normalize tiny color/value differences across frames after manual edits.",
    ]
    if manual_polish_required:
        manual_polish_queue.insert(
            0,
            "Human art review is required because this package uses an AI-generated rough candidate.",
        )
    decision = "candidate_ready_for_manual_polish" if not blocking else "needs_retake_before_manual_polish"
    return {
        "target": "production_walk_8frame_sideview",
        "decision": decision,
        "production_ready": False,
        "checks": checks,
        "blocking_issues": blocking,
        "manual_polish_required": manual_polish_required,
        "manual_polish_queue": manual_polish_queue,
        "do_not_claim_production_until": [
            "a human accepts the loop at game size",
            "frame-level polish is completed",
            "a final production review marks production_ready true",
        ],
    }


def _flatten(image: Image.Image) -> Image.Image:
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    return background


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    pixels = image.load()
    width, height = image.size
    samples = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
        pixels[width // 2, 0],
        pixels[width // 2, height - 1],
    ]
    return tuple(round(sum(sample[channel] for sample in samples) / len(samples)) for channel in range(3))


def _connected_background_mask(
    image: Image.Image,
    background: tuple[int, int, int],
    threshold: int,
    min_channel: int,
) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    candidate = Image.new("L", image.size, 0)
    candidate_pixels = candidate.load()
    green_key = background[1] >= max(background[0], background[2]) + 80
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            matches_distance = distance <= threshold and min(red, green, blue) >= min_channel
            matches_green_key = green_key and green >= 120 and green >= max(red, blue) + 55
            if matches_distance or matches_green_key:
                candidate_pixels[x, y] = 255

    out = Image.new("L", image.size, 0)
    out_pixels = out.load()
    stack: list[tuple[int, int]] = []
    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height:
            continue
        if out_pixels[x, y] > 0 or candidate_pixels[x, y] == 0:
            continue
        out_pixels[x, y] = 255
        stack.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    return out


def _despill_green_edges(image: Image.Image) -> int:
    pixels = image.load()
    changed = 0
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            limit = max(red, blue)
            if green >= 120 and green >= limit + 35:
                pixels[x, y] = (red, limit, blue, alpha)
                changed += 1
    return changed


def _notes(manifest: dict[str, Any], cleanup_report: dict[str, Any]) -> str:
    warnings = cleanup_report["warnings"] or ["none"]
    warning_text = "\n".join(f"- {warning}" for warning in warnings)
    if manifest["source_kind"] == "artist_authored_rough":
        source_summary = "a human-authored rough walk cycle packaged for review"
        pose_control_summary = "Keeps human-authored pose and silhouette control."
    else:
        source_summary = f"a rough walk cycle packaged for review from `{manifest['source_kind']}`"
        pose_control_summary = "Preserves the provided rough poses and silhouette without generating new frames."
    return f"""# Artist-Authored 8-Frame Walk Cleanup

This package is Route A: {source_summary}.

- route: `{manifest["route"]}`
- route_status: `{manifest["route_status"]}`
- source_kind: `{manifest["source_kind"]}`
- frame_count: `{manifest["frame_count"]}`
- background: `{manifest["background"]}`
- AI/model scope: `{manifest["ai_scope"]}`
- game_readiness: `{manifest["game_readiness"]["decision"]}`
- production_gate: `{manifest["production_gate"]["decision"]}`
- production_ready: `{manifest["review"]["production_ready"]}`

## What This Route Does

- {pose_control_summary}
- Produces transparent frames, spritesheet, preview GIF, contact sheet, manifest, and cleanup report.
- Produces 128, 192, and 256 px-height game-size preview packages by default.
- Produces production review JSON/Markdown for the manual polish gate.
- Uses deterministic cleanup only.

## What This Route Does Not Do

- Does not generate poses.
- Does not redesign the character.
- Does not run ComfyUI, Wan, ControlNet, video generation, or new model backends.
- Does not create 120-frame outputs.

## Cleanup Warnings

{warning_text}
"""


def _production_review_notes(production_gate: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- [{'x' if passed else ' '}] {name}" for name, passed in production_gate["checks"].items()
    )
    blocking = production_gate["blocking_issues"] or ["none"]
    blocking_text = "\n".join(f"- {issue}" for issue in blocking)
    polish_text = "\n".join(f"- {item}" for item in production_gate["manual_polish_queue"])
    return f"""# Production Review

- target: `{production_gate["target"]}`
- decision: `{production_gate["decision"]}`
- production_ready: `{production_gate["production_ready"]}`

## Checks

{checks}

## Blocking Issues

{blocking_text}

## Manual Polish Queue

{polish_text}

## Production Rule

Do not mark this asset production-ready until a human accepts the loop at game size, frame-level
polish is completed, and a final production review explicitly flips `production_ready` to true.
"""


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _parse_preview_heights(value: str) -> list[int]:
    if not value.strip():
        return []
    return [int(part.strip()) for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    main()
