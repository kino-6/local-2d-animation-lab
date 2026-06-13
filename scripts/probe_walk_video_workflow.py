from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe local ComfyUI video readiness using walk frames.")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument(
        "--walk-run",
        default=Path("outputs_controlnet_pdca/anima_00013/walk/walk_baseline"),
        type=Path,
    )
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--keyframes", default=12, type=int)
    parser.add_argument("--target-frames", default=120, type=int)
    args = parser.parse_args()

    run_dir = build_timestamped_run_dir(args.output_root, "video_walk_probe", "video_walk_probe")
    write_run_profile(run_dir, category="video_walk_probe", label="video_walk_probe", args=args)
    object_info = _object_info(args.comfy_url)
    readiness = _readiness(object_info)

    frames = sorted((args.walk_run / "frames").glob("*.png"), key=_frame_index)
    if not frames:
        raise FileNotFoundError(f"No walk frames found: {args.walk_run / 'frames'}")

    selected = _select_keyframes(frames, args.keyframes)
    keyframe_dir = run_dir / "keyframes"
    hold_dir = run_dir / "hold_frames"
    crossfade_dir = run_dir / "crossfade_frames"
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    hold_dir.mkdir(parents=True, exist_ok=True)
    crossfade_dir.mkdir(parents=True, exist_ok=True)

    keyframe_paths = _copy_keyframes(selected, keyframe_dir)
    hold_paths = _make_hold_frames(keyframe_paths, hold_dir, args.target_frames)
    crossfade_paths = _make_crossfade_frames(keyframe_paths, crossfade_dir, args.target_frames)

    outputs = {
        "keyframe_contact_sheet": str(make_contact_sheet(keyframe_paths, run_dir / "keyframe_contact_sheet.png")),
        "hold_preview_gif": str(make_preview_gif(hold_paths, run_dir / "hold_preview.gif", loop=True)),
        "crossfade_preview_gif": str(make_preview_gif(crossfade_paths, run_dir / "crossfade_preview.gif", loop=True)),
    }

    report = {
        "purpose": "Probe whether current local ComfyUI can run a video-consistent walk workflow.",
        "walk_run": str(args.walk_run),
        "source_frame_count": len(frames),
        "keyframe_count": len(keyframe_paths),
        "target_frame_count": args.target_frames,
        "comfy_video_readiness": readiness,
        "outputs": outputs,
        "finding": _finding(readiness),
    }
    report_path = run_dir / "walk_video_probe_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(json.dumps(report["finding"], indent=2, ensure_ascii=False))


def _object_info(server_url: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{server_url.rstrip('/')}/object_info", timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _readiness(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "svd_img2vid": {
            "node_present": "SVD_img2vid_Conditioning" in data,
            "clip_vision_models": _combo_options(data, "CLIPVisionLoader", "clip_name"),
            "ready": bool(_combo_options(data, "CLIPVisionLoader", "clip_name")),
        },
        "frame_interpolation": {
            "node_present": "FrameInterpolate" in data,
            "models": _combo_options(data, "FrameInterpolationModelLoader", "model_name"),
            "ready": bool(_combo_options(data, "FrameInterpolationModelLoader", "model_name")),
        },
        "optical_flow": {
            "node_present": "OpticalFlowLoader" in data,
            "models": _combo_options(data, "OpticalFlowLoader", "model_name"),
            "ready": bool(_combo_options(data, "OpticalFlowLoader", "model_name")),
        },
        "wan_i2v": {
            "node_present": "WanImageToVideo" in data or "WanFirstLastFrameToVideo" in data,
            "unet_candidates": _matching(_combo_options(data, "UNETLoader", "unet_name"), ("wan",)),
            "clip_candidates": _matching(_combo_options(data, "CLIPLoader", "clip_name"), ("wan", "umt5", "t5")),
            "ready": bool(_matching(_combo_options(data, "UNETLoader", "unet_name"), ("wan",))),
        },
        "ltxv_i2v": {
            "node_present": "LTXVImgToVideo" in data,
            "unet_candidates": _matching(_combo_options(data, "UNETLoader", "unet_name"), ("ltx",)),
            "clip_candidates": _matching(_combo_options(data, "CLIPLoader", "clip_name"), ("ltx", "t5")),
            "ready": bool(_matching(_combo_options(data, "UNETLoader", "unet_name"), ("ltx",))),
        },
        "hunyuan_i2v": {
            "node_present": "HunyuanImageToVideo" in data or "HunyuanVideo15ImageToVideo" in data,
            "unet_candidates": _matching(_combo_options(data, "UNETLoader", "unet_name"), ("hunyuan",)),
            "clip_candidates": _matching(_combo_options(data, "CLIPLoader", "clip_name"), ("hunyuan", "llava", "clip")),
            "ready": bool(_matching(_combo_options(data, "UNETLoader", "unet_name"), ("hunyuan",))),
        },
    }


def _combo_options(data: dict[str, Any], node: str, field: str) -> list[str]:
    values = data.get(node, {}).get("input", {}).get("required", {}).get(field, [])
    if values and isinstance(values[0], list):
        return [str(item) for item in values[0]]
    if len(values) > 1 and isinstance(values[1], dict):
        return [str(item) for item in values[1].get("options", [])]
    return []


def _matching(values: list[str], needles: tuple[str, ...]) -> list[str]:
    return [value for value in values if any(needle in value.lower() for needle in needles)]


def _finding(readiness: dict[str, Any]) -> dict[str, Any]:
    ready = [name for name, item in readiness.items() if item["ready"]]
    if ready:
        return {
            "status": "video_model_ready",
            "ready_paths": ready,
            "next_step": "Build a ComfyUI walk I2V or first-last-frame workflow for the first ready path.",
        }
    return {
        "status": "video_nodes_present_but_models_missing",
        "ready_paths": [],
        "next_step": (
            "Install one local video stack, preferably Wan or LTXV for I2V, or a frame interpolation "
            "model for keyframe-to-120-frame expansion. Current probe only writes keyframe and "
            "non-generative hold/crossfade previews."
        ),
    }


def _select_keyframes(frames: list[Path], count: int) -> list[Path]:
    if count >= len(frames):
        return frames
    return [frames[round(index * (len(frames) - 1) / (count - 1))] for index in range(count)]


def _copy_keyframes(frames: list[Path], output_dir: Path) -> list[Path]:
    paths = []
    for index, path in enumerate(frames):
        image = Image.open(path).convert("RGBA")
        out = output_dir / f"keyframe_{index:03d}.png"
        image.save(out)
        paths.append(out)
    return paths


def _make_hold_frames(keyframes: list[Path], output_dir: Path, target_count: int) -> list[Path]:
    paths = []
    for index in range(target_count):
        source = keyframes[round(index * (len(keyframes) - 1) / max(1, target_count - 1))]
        image = Image.open(source).convert("RGBA")
        out = output_dir / f"frame_{index:03d}.png"
        image.save(out)
        paths.append(out)
    return paths


def _make_crossfade_frames(keyframes: list[Path], output_dir: Path, target_count: int) -> list[Path]:
    images = [Image.open(path).convert("RGBA") for path in keyframes]
    paths = []
    segments = len(images)
    for index in range(target_count):
        position = index * segments / target_count
        left_index = int(position) % segments
        right_index = (left_index + 1) % segments
        alpha = position - int(position)
        image = Image.blend(images[left_index], images[right_index], alpha)
        out = output_dir / f"frame_{index:03d}.png"
        image.save(out)
        paths.append(out)
    return paths


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


if __name__ == "__main__":
    main()
