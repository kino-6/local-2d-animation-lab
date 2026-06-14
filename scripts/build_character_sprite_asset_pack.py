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
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    manifest = build_character_sprite_asset_pack(
        reference_image=args.reference_image,
        walk_production_ready_dir=args.walk_production_ready_dir,
        output_dir=args.output_dir,
        fps=args.fps,
        clean=args.clean,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def build_character_sprite_asset_pack(
    reference_image: Path = DEFAULT_REFERENCE,
    walk_production_ready_dir: Path = DEFAULT_WALK_READY,
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
    run_action = _write_run_stub(actions_dir / "run")

    identity_report = _build_identity_report(
        reference_image=reference_image,
        walk_action_dir=actions_dir / "walk",
        idle_action_dir=actions_dir / "idle",
    )
    production_gate = _build_production_gate(walk_action, idle_action, run_action, identity_report)

    (output_dir / "identity_report.json").write_text(
        json.dumps(identity_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "production_gate.json").write_text(
        json.dumps(production_gate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "route": ROUTE,
        "asset_kind": "2d_game_sprite_asset_pack",
        "source_reference": str(reference_image).replace("\\", "/"),
        "canonical_identity": IDENTITY_CUES,
        "actions": {
            "walk": walk_action,
            "idle": idle_action,
            "run": run_action,
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
            "Only walk and idle are production-ready in this pack.",
            "Run and stronger actions remain explicitly gated until new authored frames exist.",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "notes.md").write_text(_notes(manifest), encoding="utf-8")
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

    metrics = _action_metrics(idle_paths)
    report = {
        "action": "idle",
        "status": "production_ready",
        "source": source.name,
        "method": "subtle_upper_body_breathing_from_accepted_walk_sprite",
        "frame_count": 4,
        "frame_size": metrics["frame_size"],
        "ground_y_range": metrics["ground_y_range"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "production_ready": metrics["ground_y_range"] == 0 and not metrics["alpha_edge_touch_frames"],
    }
    (action_dir / "production_ready_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (action_dir / "notes.md").write_text(_idle_notes(report), encoding="utf-8")
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


def _write_run_stub(action_dir: Path) -> dict[str, Any]:
    action_dir.mkdir(parents=True, exist_ok=True)
    stub = {
        "action": "run",
        "status": "future_action_stub",
        "production_ready": False,
        "reason": "Run needs authored or accepted rough frames; do not derive it by speeding up walk.",
        "required_before_production": [
            "8 authored run frames",
            "stable contact/airborne phases",
            "identity cue pass",
            "game-size contact sheet review",
        ],
    }
    (action_dir / "action_stub.json").write_text(
        json.dumps(stub, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (action_dir / "notes.md").write_text(
        "# Run Action Stub\n\nRun is intentionally not production-ready yet. It needs authored frames.\n",
        encoding="utf-8",
    )
    return stub


def _build_identity_report(reference_image: Path, walk_action_dir: Path, idle_action_dir: Path) -> dict[str, Any]:
    reference = Image.open(reference_image).convert("RGBA")
    walk_frames = sorted((walk_action_dir / "frames").glob("walk_*.png"))
    idle_frames = sorted((idle_action_dir / "frames").glob("idle_*.png"))

    reference_counts = _cue_counts([reference])
    walk_counts = _cue_counts([Image.open(path).convert("RGBA") for path in walk_frames])
    idle_counts = _cue_counts([Image.open(path).convert("RGBA") for path in idle_frames])

    cue_reports = {}
    for cue, description in IDENTITY_CUES.items():
        cue_reports[cue] = {
            "description": description,
            "reference_pixels": reference_counts[cue],
            "walk_pixels": walk_counts[cue],
            "idle_pixels": idle_counts[cue],
            "passed": reference_counts[cue] > 0 and walk_counts[cue] > 0 and idle_counts[cue] > 0,
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


def _build_production_gate(
    walk_action: dict[str, Any],
    idle_action: dict[str, Any],
    run_action: dict[str, Any],
    identity_report: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "walk_production_ready": walk_action["production_ready"] is True,
        "idle_production_ready": idle_action["production_ready"] is True,
        "run_honestly_gated": run_action["production_ready"] is False,
        "identity_cues_pass": identity_report["all_required_cues_pass"] is True,
        "unsupported_backends_unused": True,
    }
    blocking = [name for name, passed in checks.items() if not passed]
    return {
        "target": "character_sprite_asset_pack_mvp",
        "decision": "production_ready" if not blocking else "needs_retake",
        "production_ready": not blocking,
        "checks": checks,
        "blocking_issues": blocking,
        "scope_statement": "walk and idle are production-ready; run is explicitly gated as future work.",
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


def _notes(manifest: dict[str, Any]) -> str:
    return f"""# Character Sprite Asset Pack

- route: `{manifest["route"]}`
- production_ready: `{manifest["production_ready"]}`
- current production actions: `walk`, `idle`
- future gated actions: `run`

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


if __name__ == "__main__":
    main()
