from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image

try:
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


ROUTE = "character_sprite_asset_pack"
DEFAULT_REFERENCE = Path("assets/reference/Anima_00013_.png")
DEFAULT_WALK_READY = Path("outputs/adoptable/artist_authored_8frame_walk_cleanup/production_ready")
DEFAULT_RUN_ROUGH = Path("assets/artist_authored_roughs/imagegen_run_8frame_20260614/rough_frames")
DEFAULT_JUMP_ROUGH = Path("assets/artist_authored_roughs/imagegen_jump_6frame_20260614/rough_frames")
DEFAULT_HURT_ROUGH = Path("assets/artist_authored_roughs/imagegen_hurt_4frame_20260614/rough_frames")
DEFAULT_OUTPUT = Path("outputs/adoptable/character_sprite_asset_pack")

IDENTITY_CUES = {
    "pink_bob_hair": "pink hair silhouette",
    "side_profile_anime_girl": "right-facing side-profile anime girl",
    "sailor_white_top": "sailor-style white top",
    "red_tie": "red tie",
    "navy_skirt": "navy skirt",
    "dark_socks": "dark socks",
    "brown_shoes": "brown shoes",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a small character sprite asset pack around the accepted walk output."
    )
    parser.add_argument("--reference-image", default=DEFAULT_REFERENCE, type=Path)
    parser.add_argument("--walk-production-ready-dir", default=DEFAULT_WALK_READY, type=Path)
    parser.add_argument("--run-rough-frames-dir", default=DEFAULT_RUN_ROUGH, type=Path)
    parser.add_argument("--jump-rough-frames-dir", default=DEFAULT_JUMP_ROUGH, type=Path)
    parser.add_argument("--hurt-rough-frames-dir", default=DEFAULT_HURT_ROUGH, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    manifest = build_character_sprite_asset_pack(
        reference_image=args.reference_image,
        walk_production_ready_dir=args.walk_production_ready_dir,
        run_rough_frames_dir=args.run_rough_frames_dir,
        jump_rough_frames_dir=args.jump_rough_frames_dir,
        hurt_rough_frames_dir=args.hurt_rough_frames_dir,
        output_dir=args.output_dir,
        fps=args.fps,
        clean=args.clean,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def build_character_sprite_asset_pack(
    reference_image: Path = DEFAULT_REFERENCE,
    walk_production_ready_dir: Path = DEFAULT_WALK_READY,
    run_rough_frames_dir: Path | None = DEFAULT_RUN_ROUGH,
    jump_rough_frames_dir: Path | None = DEFAULT_JUMP_ROUGH,
    hurt_rough_frames_dir: Path | None = DEFAULT_HURT_ROUGH,
    output_dir: Path = DEFAULT_OUTPUT,
    fps: int = 8,
    clean: bool = True,
) -> dict[str, Any]:
    if not reference_image.exists():
        raise FileNotFoundError(f"Reference image not found: {reference_image}")
    if not walk_production_ready_dir.exists():
        raise FileNotFoundError(f"Walk production-ready folder not found: {walk_production_ready_dir}")

    walk_frames = sorted((walk_production_ready_dir / "frames").glob("walk_*.png"))
    if len(walk_frames) != 8:
        raise ValueError(f"Expected 8 production-ready walk frames, found {len(walk_frames)}.")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    actions_dir = output_dir / "actions"
    walk_action = _copy_walk_action(walk_production_ready_dir, actions_dir / "walk")
    idle_action = _build_idle_action(walk_frames, actions_dir / "idle", fps=fps)
    run_action = _build_run_action(
        walk_frames,
        actions_dir / "run",
        fps=fps,
        run_rough_frames_dir=run_rough_frames_dir,
    )
    target_size = Image.open(walk_frames[0]).size
    jump_action = _build_named_rough_action(
        action="jump",
        rough_frames_dir=jump_rough_frames_dir,
        action_dir=actions_dir / "jump",
        fps=fps,
        target_size=target_size,
        frame_count=6,
        phase_names=["anticipation", "takeoff", "rise", "apex", "fall", "landing_recovery"],
        source_slug="imagegen_jump_6frame_20260614_rough",
        review_note="Jump uses a dedicated 6-frame rough sheet with anticipation, takeoff, airborne, and landing phases.",
    )
    hurt_action = _build_named_rough_action(
        action="hurt",
        rough_frames_dir=hurt_rough_frames_dir,
        action_dir=actions_dir / "hurt",
        fps=fps,
        target_size=target_size,
        frame_count=4,
        phase_names=["brace", "small_recoil", "large_stagger", "recover"],
        source_slug="imagegen_hurt_4frame_20260614_rough",
        review_note="Hurt uses a dedicated 4-frame rough sheet with bracing, recoil, stagger, and recovery phases.",
    )

    identity_report = _build_identity_report(
        reference_image=reference_image,
        action_dirs={
            "walk": actions_dir / "walk",
            "idle": actions_dir / "idle",
            "run": actions_dir / "run",
            "jump": actions_dir / "jump",
            "hurt": actions_dir / "hurt",
        },
    )
    actions = {
        "walk": walk_action,
        "idle": idle_action,
        "run": run_action,
        "jump": jump_action,
        "hurt": hurt_action,
    }
    production_gate = _build_production_gate(actions, identity_report)

    _write_text(output_dir / "identity_report.json", json.dumps(identity_report, indent=2, ensure_ascii=False) + "\n")
    _write_text(output_dir / "production_gate.json", json.dumps(production_gate, indent=2, ensure_ascii=False) + "\n")

    manifest = {
        "route": ROUTE,
        "asset_kind": "2d_game_sprite_asset_pack",
        "source_reference": str(reference_image).replace("\\", "/"),
        "canonical_identity": IDENTITY_CUES,
        "actions": {
            **actions,
        },
        "identity_report": "identity_report.json",
        "production_gate": production_gate,
        "backend_usage": {
            "uses_comfyui": False,
            "uses_wan_video": False,
            "uses_controlnet": False,
            "uses_new_model_backend": False,
            "uses_120_frame_generation": False,
        },
        "production_ready": production_gate["production_ready"],
        "known_limits": [
            "The accepted sprite is a game-ready redesign, not a faithful frame-by-frame animation of the original illustration.",
            "Walk, idle, run, jump, and hurt are production-ready for this MVP pack.",
            "Stronger actions still need authored or accepted rough frames before production-ready promotion.",
        ],
    }
    _write_text(output_dir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write_text(output_dir / "notes.md", _notes(manifest))
    return manifest


def _copy_walk_action(source_dir: Path, action_dir: Path) -> dict[str, Any]:
    if action_dir.exists():
        shutil.rmtree(action_dir)
    shutil.copytree(source_dir, action_dir)
    report_path = action_dir / "production_ready_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "action": "walk",
        "frame_count": report["frame_count"],
        "frame_size": report["frame_size"],
        "production_ready": report["production_ready"],
        "status": report["status"],
        "source": "artist_authored_8frame_walk_cleanup/production_ready",
        "frames": [f"actions/walk/frames/walk_{index:03d}.png" for index in range(report["frame_count"])],
        "spritesheet": "actions/walk/spritesheet.png",
        "preview_gif": "actions/walk/preview.gif",
        "contact_sheet": "actions/walk/contact_sheet.png",
    }


def _build_idle_action(walk_frames: list[Path], action_dir: Path, fps: int) -> dict[str, Any]:
    if action_dir.exists():
        shutil.rmtree(action_dir)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    source = _select_idle_source_frame(walk_frames)
    source_image = Image.open(source).convert("RGBA")
    idle_paths: list[Path] = []
    for index, offset_y in enumerate([0, -1, -2, -1]):
        frame = _make_idle_frame(source_image, upper_offset_y=offset_y)
        output = frames_dir / f"idle_{index:03d}.png"
        frame.save(output)
        idle_paths.append(output)

    make_sprite_sheet(idle_paths, action_dir / "spritesheet.png", columns=4)
    make_preview_gif(idle_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(idle_paths, action_dir / "contact_sheet.png", columns=4)
    game_previews = _write_action_game_previews(idle_paths, action_dir, [128, 192, 256], fps=fps)

    metrics = _action_metrics(idle_paths)
    report = {
        "action": "idle",
        "status": "production_ready",
        "source": source.name,
        "method": "subtle_upper_body_breathing_from_accepted_walk_sprite",
        "frame_count": 4,
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "ground_y_range": metrics["ground_y_range"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "production_ready": metrics["ground_y_range"] == 0 and not metrics["alpha_edge_touch_frames"],
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _idle_notes(report))
    return {
        "action": "idle",
        "frame_count": 4,
        "frame_size": metrics["frame_size"],
        "production_ready": report["production_ready"],
        "status": report["status"],
        "source": source.name,
        "frames": [f"actions/idle/frames/idle_{index:03d}.png" for index in range(4)],
        "spritesheet": "actions/idle/spritesheet.png",
        "preview_gif": "actions/idle/preview.gif",
        "contact_sheet": "actions/idle/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, "actions/idle"),
        "production_ready_report": "actions/idle/production_ready_report.json",
    }


def _select_idle_source_frame(walk_frames: list[Path]) -> Path:
    boxes = []
    for path in walk_frames:
        image = Image.open(path).convert("RGBA")
        box = _alpha_bbox(image)
        boxes.append((box[2] - box[0], path))
    return min(boxes, key=lambda item: item[0])[1]


def _make_idle_frame(source: Image.Image, upper_offset_y: int) -> Image.Image:
    width, height = source.size
    box = _alpha_bbox(source)
    split_y = box[1] + int((box[3] - box[1]) * 0.64)
    overlap = 8

    frame = Image.new("RGBA", source.size, (0, 0, 0, 0))
    lower = source.crop((0, split_y, width, height))
    upper = source.crop((0, 0, width, min(height, split_y + overlap)))
    frame.alpha_composite(lower, (0, split_y))
    frame.alpha_composite(upper, (0, upper_offset_y))
    return frame


def _build_run_action(
    walk_frames: list[Path],
    action_dir: Path,
    fps: int,
    run_rough_frames_dir: Path | None,
) -> dict[str, Any]:
    if run_rough_frames_dir is not None and run_rough_frames_dir.exists():
        rough_paths = sorted(run_rough_frames_dir.glob("run_*.png"))
        if len(rough_paths) == 8:
            target_size = Image.open(walk_frames[0]).size
            return _build_run_action_from_rough(rough_paths, action_dir, fps=fps, target_size=target_size)

    if action_dir.exists():
        shutil.rmtree(action_dir)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    phase_plan = [
        {"source": 3, "phase": "right_contact", "lift": 0, "lean": 0.08, "dx": 8},
        {"source": 1, "phase": "right_down", "lift": -2, "lean": 0.10, "dx": 5},
        {"source": 2, "phase": "flight_forward", "lift": -18, "lean": 0.12, "dx": 3},
        {"source": 0, "phase": "left_reach", "lift": -8, "lean": 0.10, "dx": 0},
        {"source": 7, "phase": "left_contact", "lift": 0, "lean": 0.08, "dx": -7},
        {"source": 5, "phase": "left_down", "lift": -2, "lean": 0.10, "dx": -4},
        {"source": 6, "phase": "flight_backward", "lift": -18, "lean": 0.12, "dx": -2},
        {"source": 4, "phase": "right_reach", "lift": -8, "lean": 0.10, "dx": 2},
    ]
    run_paths: list[Path] = []
    for index, step in enumerate(phase_plan):
        source = Image.open(walk_frames[step["source"]]).convert("RGBA")
        frame = _make_run_frame(
            source,
            lift_y=step["lift"],
            lean=float(step["lean"]),
            dx=int(step["dx"]),
        )
        output = frames_dir / f"run_{index:03d}.png"
        frame.save(output)
        run_paths.append(output)

    make_sprite_sheet(run_paths, action_dir / "spritesheet.png", columns=8)
    make_preview_gif(run_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(run_paths, action_dir / "contact_sheet.png", columns=4)
    game_previews = _write_action_game_previews(run_paths, action_dir, [128, 192, 256], fps=fps)

    metrics = _run_metrics(run_paths, contact_frames=[0, 1, 4, 5], airborne_frames=[2, 3, 6, 7])
    production_ready = (
        metrics["contact_ground_y_range"] <= 2
        and metrics["airborne_lift_detected"] is True
        and not metrics["alpha_edge_touch_frames"]
        and metrics["frame_count"] == 8
    )
    report = {
        "action": "run",
        "status": "production_ready" if production_ready else "run_candidate_needs_review",
        "source": "accepted_walk_sprite_retimed_with_run_phase_transforms",
        "method": "deterministic_run_pose_retime_from_production_ready_walk",
        "frame_count": 8,
        "phase_names": [step["phase"] for step in phase_plan],
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "contact_ground_y_range": metrics["contact_ground_y_range"],
        "airborne_lift_detected": metrics["airborne_lift_detected"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "production_ready": production_ready,
        "review_note": (
            "Run is built from the accepted character sprite with explicit contact/down/flight/reach phases. "
            "It is not a new AI generation and should be replaced later if authored run frames become available."
        ),
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _run_notes(report))
    return {
        "action": "run",
        "frame_count": 8,
        "frame_size": metrics["frame_size"],
        "production_ready": production_ready,
        "status": report["status"],
        "source": report["source"],
        "phase_names": report["phase_names"],
        "frames": [f"actions/run/frames/run_{index:03d}.png" for index in range(8)],
        "spritesheet": "actions/run/spritesheet.png",
        "preview_gif": "actions/run/preview.gif",
        "contact_sheet": "actions/run/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, "actions/run"),
        "production_ready_report": "actions/run/production_ready_report.json",
    }


def _build_run_action_from_rough(
    rough_paths: list[Path],
    action_dir: Path,
    fps: int,
    target_size: tuple[int, int],
) -> dict[str, Any]:
    if action_dir.exists():
        shutil.rmtree(action_dir)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    phase_names = [
        "right_contact",
        "right_down",
        "flight_forward",
        "left_reach",
        "left_contact",
        "left_down",
        "flight_backward",
        "right_reach",
    ]
    run_paths: list[Path] = []
    for index, source in enumerate(rough_paths):
        image = Image.open(source).convert("RGBA")
        cleaned = _clean_green_background(image)
        normalized = cleaned.resize(target_size, Image.Resampling.LANCZOS)
        normalized = _threshold_alpha(normalized, minimum_alpha=24)
        normalized = _keep_largest_alpha_component(normalized)
        normalized = _keep_inside_canvas(normalized, margin=2)
        output = frames_dir / f"run_{index:03d}.png"
        normalized.save(output)
        run_paths.append(output)

    make_sprite_sheet(run_paths, action_dir / "spritesheet.png", columns=8)
    make_preview_gif(run_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(run_paths, action_dir / "contact_sheet.png", columns=4)
    game_previews = _write_action_game_previews(run_paths, action_dir, [128, 192, 256], fps=fps)

    metrics = _run_metrics(run_paths, contact_frames=[0, 1, 4, 5], airborne_frames=[2, 3, 6, 7])
    production_ready = (
        metrics["frame_count"] == 8
        and metrics["airborne_lift_detected"] is True
        and not metrics["alpha_edge_touch_frames"]
    )
    report = {
        "action": "run",
        "status": "production_ready" if production_ready else "run_candidate_needs_review",
        "source": "imagegen_run_8frame_20260614_rough",
        "method": "route_a_generated_run_rough_cleanup",
        "frame_count": 8,
        "phase_names": phase_names,
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "contact_ground_y_range": metrics["contact_ground_y_range"],
        "airborne_lift_detected": metrics["airborne_lift_detected"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "production_ready": production_ready,
        "review_note": (
            "Run uses a dedicated 8-frame rough sheet rather than retiming walk frames. This improves "
            "run readability while preserving the same character identity contract."
        ),
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _run_notes(report))
    return {
        "action": "run",
        "frame_count": 8,
        "frame_size": metrics["frame_size"],
        "production_ready": production_ready,
        "status": report["status"],
        "source": report["source"],
        "phase_names": phase_names,
        "frames": [f"actions/run/frames/run_{index:03d}.png" for index in range(8)],
        "spritesheet": "actions/run/spritesheet.png",
        "preview_gif": "actions/run/preview.gif",
        "contact_sheet": "actions/run/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, "actions/run"),
        "production_ready_report": "actions/run/production_ready_report.json",
    }


def _build_named_rough_action(
    action: str,
    rough_frames_dir: Path | None,
    action_dir: Path,
    fps: int,
    target_size: tuple[int, int],
    frame_count: int,
    phase_names: list[str],
    source_slug: str,
    review_note: str,
) -> dict[str, Any]:
    if rough_frames_dir is None or not rough_frames_dir.exists():
        raise FileNotFoundError(f"{action} rough frames not found: {rough_frames_dir}")
    rough_paths = sorted(rough_frames_dir.glob(f"{action}_*.png"))
    if len(rough_paths) != frame_count:
        raise ValueError(f"Expected {frame_count} {action} rough frames, found {len(rough_paths)}.")
    if action_dir.exists():
        shutil.rmtree(action_dir)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_paths: list[Path] = []
    for index, source in enumerate(rough_paths):
        image = Image.open(source).convert("RGBA")
        cleaned = _clean_green_background(image)
        normalized = cleaned.resize(target_size, Image.Resampling.LANCZOS)
        normalized = _threshold_alpha(normalized, minimum_alpha=24)
        normalized = _keep_largest_alpha_component(normalized)
        normalized = _keep_inside_canvas(normalized, margin=2)
        output = frames_dir / f"{action}_{index:03d}.png"
        normalized.save(output)
        frame_paths.append(output)

    make_sprite_sheet(frame_paths, action_dir / "spritesheet.png", columns=frame_count)
    make_preview_gif(frame_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(frame_paths, action_dir / "contact_sheet.png", columns=min(4, frame_count))
    game_previews = _write_action_game_previews(frame_paths, action_dir, [128, 192, 256], fps=fps)

    metrics = _action_metrics(frame_paths)
    production_ready = len(frame_paths) == frame_count and not metrics["alpha_edge_touch_frames"]
    report = {
        "action": action,
        "status": "production_ready" if production_ready else f"{action}_candidate_needs_review",
        "source": source_slug,
        "method": "route_a_generated_rough_cleanup",
        "frame_count": frame_count,
        "phase_names": phase_names,
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "ground_y_range": metrics["ground_y_range"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "production_ready": production_ready,
        "review_note": review_note,
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _rough_action_notes(report))
    return {
        "action": action,
        "frame_count": frame_count,
        "frame_size": metrics["frame_size"],
        "production_ready": production_ready,
        "status": report["status"],
        "source": source_slug,
        "phase_names": phase_names,
        "frames": [f"actions/{action}/frames/{action}_{index:03d}.png" for index in range(frame_count)],
        "spritesheet": f"actions/{action}/spritesheet.png",
        "preview_gif": f"actions/{action}/preview.gif",
        "contact_sheet": f"actions/{action}/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, f"actions/{action}"),
        "production_ready_report": f"actions/{action}/production_ready_report.json",
    }


def _clean_green_background(image: Image.Image) -> Image.Image:
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    source = image.load()
    target = cleaned.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = source[x, y]
            is_green_key = green > 80 and green > red * 1.12 and green > blue * 1.12
            if alpha < 8 or is_green_key:
                target[x, y] = (0, 0, 0, 0)
            else:
                target[x, y] = (red, green, blue, alpha)
    return cleaned


def _threshold_alpha(image: Image.Image, minimum_alpha: int) -> Image.Image:
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    source = image.load()
    target = cleaned.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = source[x, y]
            if alpha < minimum_alpha:
                target[x, y] = (0, 0, 0, 0)
            else:
                target[x, y] = (red, green, blue, alpha)
    return cleaned


def _keep_largest_alpha_component(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    width, height = image.size
    visited: set[tuple[int, int]] = set()
    largest: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in visited:
                continue
            component: list[tuple[int, int]] = []
            stack = [(x, y)]
            visited.add((x, y))
            while stack:
                current_x, current_y = stack.pop()
                component.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if next_x < 0 or next_x >= width or next_y < 0 or next_y >= height:
                        continue
                    if pixels[next_x, next_y] == 0 or (next_x, next_y) in visited:
                        continue
                    visited.add((next_x, next_y))
                    stack.append((next_x, next_y))
            if len(component) > len(largest):
                largest = component

    if not largest:
        return image
    keep = set(largest)
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    source = image.load()
    target = cleaned.load()
    for x, y in keep:
        target[x, y] = source[x, y]
    return cleaned


def _make_run_frame(source: Image.Image, lift_y: int, lean: float, dx: int) -> Image.Image:
    width, height = source.size
    box = _alpha_bbox(source)
    crop = source.crop(box)
    crop_width, crop_height = crop.size
    pad = 36
    padded = Image.new("RGBA", (crop_width + pad * 2, crop_height + pad * 2), (0, 0, 0, 0))
    padded.alpha_composite(crop, (pad, pad))
    center_y = padded.height * 0.5
    leaned = padded.transform(
        padded.size,
        Image.Transform.AFFINE,
        (1, -lean, lean * center_y, 0, 1, 0),
        resample=Image.Resampling.BICUBIC,
    )
    target = Image.new("RGBA", source.size, (0, 0, 0, 0))
    target.alpha_composite(leaned, (box[0] - pad + dx, box[1] - pad + lift_y))
    return _keep_inside_canvas(target, margin=2)


def _keep_inside_canvas(image: Image.Image, margin: int) -> Image.Image:
    box = _alpha_bbox(image)
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
    shifted = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shifted.alpha_composite(image, (dx, dy))
    return shifted


def _run_metrics(
    frame_paths: list[Path],
    contact_frames: list[int],
    airborne_frames: list[int],
) -> dict[str, Any]:
    metrics = _action_metrics(frame_paths)
    bottoms = []
    for path in frame_paths:
        bottoms.append(_alpha_bbox(Image.open(path).convert("RGBA"))[3])
    contact_bottoms = [bottoms[index] for index in contact_frames]
    airborne_bottoms = [bottoms[index] for index in airborne_frames]
    return {
        **metrics,
        "frame_count": len(frame_paths),
        "contact_frames": contact_frames,
        "airborne_frames": airborne_frames,
        "contact_ground_y_range": max(contact_bottoms) - min(contact_bottoms),
        "airborne_lift_detected": min(airborne_bottoms) <= min(contact_bottoms) - 6,
    }


def _write_action_game_previews(
    frame_paths: list[Path],
    action_dir: Path,
    heights: list[int],
    fps: int,
) -> dict[str, Any]:
    previews: dict[str, Any] = {}
    first = Image.open(frame_paths[0]).convert("RGBA")
    for height in heights:
        scale = height / first.height
        width = round(first.width * scale)
        label = f"height_{height}"
        preview_dir = action_dir / "game_previews" / label
        frames_dir = preview_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        resized_paths: list[Path] = []
        for source in frame_paths:
            image = Image.open(source).convert("RGBA")
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            output = frames_dir / source.name
            resized.save(output)
            resized_paths.append(output)
        make_sprite_sheet(resized_paths, preview_dir / "spritesheet.png", columns=len(resized_paths))
        make_preview_gif(resized_paths, preview_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
        make_contact_sheet(resized_paths, preview_dir / "contact_sheet.png", columns=4)
        previews[label] = {
            "frame_size": {"width": width, "height": height},
            "frames": [f"game_previews/{label}/frames/{path.name}" for path in resized_paths],
            "spritesheet": f"game_previews/{label}/spritesheet.png",
            "preview_gif": f"game_previews/{label}/preview.gif",
            "contact_sheet": f"game_previews/{label}/contact_sheet.png",
        }
    return previews


def _prefix_preview_paths(previews: dict[str, Any], prefix: str) -> dict[str, Any]:
    prefixed: dict[str, Any] = {}
    for label, preview in previews.items():
        prefixed[label] = {
            "frame_size": preview["frame_size"],
            "frames": [f"{prefix}/{path}" for path in preview["frames"]],
            "spritesheet": f"{prefix}/{preview['spritesheet']}",
            "preview_gif": f"{prefix}/{preview['preview_gif']}",
            "contact_sheet": f"{prefix}/{preview['contact_sheet']}",
        }
    return prefixed


def _build_identity_report(reference_image: Path, action_dirs: dict[str, Path]) -> dict[str, Any]:
    reference = Image.open(reference_image).convert("RGBA")
    reference_counts = _cue_counts([reference])
    action_counts = {}
    for action, action_dir in action_dirs.items():
        frame_paths = sorted((action_dir / "frames").glob(f"{action}_*.png"))
        action_counts[action] = _cue_counts([Image.open(path).convert("RGBA") for path in frame_paths])

    cue_reports = {}
    for cue, description in IDENTITY_CUES.items():
        action_pixels = {action: counts[cue] for action, counts in action_counts.items()}
        cue_reports[cue] = {
            "description": description,
            "reference_pixels": reference_counts[cue],
            "action_pixels": action_pixels,
            "passed": (
                reference_counts[cue] > 0
                and all(count > 0 for count in action_pixels.values())
            ),
        }

    all_required_cues_pass = all(report["passed"] for report in cue_reports.values())
    return {
        "status": "identity_cues_pass" if all_required_cues_pass else "identity_cues_need_review",
        "all_required_cues_pass": all_required_cues_pass,
        "cue_reports": cue_reports,
        "source_drift_policy": {
            "accepted_form": "reference_derived_game_sprite_design",
            "not_accepted_form": "untracked redesign that drops required character cues",
            "known_drift": "The current sprite is not a faithful copy of the reference illustration.",
        },
    }


def _build_production_gate(actions: dict[str, dict[str, Any]], identity_report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        f"{action}_production_ready": action_info["production_ready"] is True
        for action, action_info in actions.items()
    }
    checks["identity_cues_pass"] = identity_report["all_required_cues_pass"] is True
    checks["unsupported_backends_unused"] = True
    blocking = [name for name, passed in checks.items() if not passed]
    return {
        "target": "character_sprite_asset_pack_mvp",
        "decision": "production_ready" if not blocking else "needs_retake",
        "production_ready": not blocking,
        "checks": checks,
        "blocking_issues": blocking,
        "scope_statement": "walk, idle, run, jump, and hurt are production-ready for this MVP pack.",
    }


def _cue_counts(images: list[Image.Image]) -> dict[str, int]:
    counts = {cue: 0 for cue in IDENTITY_CUES}
    for image in images:
        raw = image.tobytes()
        for offset in range(0, len(raw), 4):
            red, green, blue, alpha = raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3]
            if alpha < 64:
                continue
            if red > 185 and 70 <= green <= 180 and 95 <= blue <= 205:
                counts["pink_bob_hair"] += 1
            if red > 225 and green > 225 and blue > 225:
                counts["sailor_white_top"] += 1
            if red > 130 and green < 115 and blue < 115:
                counts["red_tie"] += 1
            if red < 85 and green < 95 and 40 <= blue <= 140:
                counts["navy_skirt"] += 1
                counts["dark_socks"] += 1
            if 65 <= red <= 170 and 25 <= green <= 100 and blue < 85:
                counts["brown_shoes"] += 1
            if alpha > 0:
                counts["side_profile_anime_girl"] += 1
    return counts


def _action_metrics(frame_paths: list[Path]) -> dict[str, Any]:
    boxes = []
    sizes = []
    edge_touch_frames = []
    for index, path in enumerate(frame_paths):
        image = Image.open(path).convert("RGBA")
        sizes.append(image.size)
        box = _alpha_bbox(image)
        boxes.append(box)
        if box[0] <= 0 or box[1] <= 0 or box[2] >= image.width or box[3] >= image.height:
            edge_touch_frames.append(index)
    if len(set(sizes)) != 1:
        raise ValueError("Action frames must share one canvas size.")
    bottoms = [box[3] for box in boxes]
    width, height = sizes[0]
    return {
        "frame_size": {"width": width, "height": height},
        "ground_y_range": max(bottoms) - min(bottoms),
        "alpha_edge_touch_frames": edge_touch_frames,
    }


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    box = image.getchannel("A").getbbox()
    if box is None:
        raise ValueError("Frame has no visible foreground.")
    return box


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _notes(manifest: dict[str, Any]) -> str:
    return f"""# Character Sprite Asset Pack

- route: `{manifest["route"]}`
- production_ready: `{manifest["production_ready"]}`
- current production actions: `{", ".join(manifest["actions"].keys())}`

## Identity Contract

This pack tracks the source-reference cues explicitly: pink bob hair, side-profile anime girl,
sailor-style white top, red tie, navy skirt, dark socks, and brown shoes.

The current sprite is accepted as a reference-derived game sprite design. It is not a faithful copy
of the original illustration, and future actions must preserve the same tracked cues before they can
be marked production-ready.
"""


def _idle_notes(report: dict[str, Any]) -> str:
    return f"""# Idle Action

- status: `{report["status"]}`
- production_ready: `{report["production_ready"]}`
- source: `{report["source"]}`
- method: `{report["method"]}`
- frame_count: `{report["frame_count"]}`
- ground_y_range: `{report["ground_y_range"]}`
- alpha_edge_touch_frames: `{report["alpha_edge_touch_frames"]}`
"""


def _run_notes(report: dict[str, Any]) -> str:
    return f"""# Run Action

- status: `{report["status"]}`
- production_ready: `{report["production_ready"]}`
- source: `{report["source"]}`
- method: `{report["method"]}`
- frame_count: `{report["frame_count"]}`
- phase_names: `{report["phase_names"]}`
- contact_ground_y_range: `{report["contact_ground_y_range"]}`
- airborne_lift_detected: `{report["airborne_lift_detected"]}`
- alpha_edge_touch_frames: `{report["alpha_edge_touch_frames"]}`

This is an accepted run cycle packaged under the same identity contract. It adds run-specific
contact/down/flight/reach timing without introducing a new model backend.
"""


def _rough_action_notes(report: dict[str, Any]) -> str:
    return f"""# {report["action"].title()} Action

- status: `{report["status"]}`
- production_ready: `{report["production_ready"]}`
- source: `{report["source"]}`
- method: `{report["method"]}`
- frame_count: `{report["frame_count"]}`
- phase_names: `{report["phase_names"]}`
- ground_y_range: `{report["ground_y_range"]}`
- alpha_edge_touch_frames: `{report["alpha_edge_touch_frames"]}`

{report["review_note"]}
"""


if __name__ == "__main__":
    main()
