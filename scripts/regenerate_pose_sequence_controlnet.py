from __future__ import annotations

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFilter

sys.path.append(str(Path(__file__).resolve().parent))

from generate_fullbody_reference_candidates import _download_first_saveimage
from generate_fullbody_reference_candidates import _queue_prompt
from generate_fullbody_reference_candidates import _safe_label
from generate_fullbody_reference_candidates import _upload_image
from generate_fullbody_reference_candidates import _wait_for_history
from natural_sprite_lab.comfy_queue import add_queue_wait_arguments
from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.progress import progress_iter
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


POSITIVE_PROMPT = (
    "masterpiece, best quality, polished anime 2d game sprite animation frame, one full-body young woman character, "
    "same character design and outfit as the reference image, right-facing side view, clean cel shading, crisp line art, "
    "stable face, stable pink hair, stable sailor uniform, navy skirt, black socks, brown shoes, clean plain white background, "
    "readable walk cycle pose, complete hands and feet"
)

NEGATIVE_PROMPT = (
    "low quality, blurry, motion blur, ghost trail, afterimage, transparent limb, duplicate body, duplicate legs, extra limbs, "
    "missing limbs, broken feet, broken hands, multiple characters, front view, back view, cropped feet, dark background, "
    "grey background, brown background, scenery, cast shadow, text, watermark, changing outfit, identity drift"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate a short pose-controlled sprite sequence from a single reference image."
    )
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--source-image", required=True, type=Path)
    parser.add_argument("--pose-dir", default=Path("pose_templates/walk/controlnet"), type=Path)
    parser.add_argument("--pose-indices", default="0,15,30,45,60,75,90,105")
    parser.add_argument("--sidecar-dir", default=None, type=Path)
    parser.add_argument("--sidecar-indices", default=None)
    parser.add_argument("--sidecar-controlnet", default="SDXL\\t2i-adapter-openpose-sdxl-1.0.safetensors")
    parser.add_argument("--sidecar-strength", default=0.0, type=float)
    parser.add_argument("--sidecar-start", default=0.0, type=float)
    parser.add_argument("--sidecar-end", default=0.55, type=float)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--checkpoint", default="novaOrangeXL_v120.safetensors")
    parser.add_argument("--controlnet", default="SDXL\\OpenPoseXL2.safetensors")
    parser.add_argument("--ipadapter-model", default=None)
    parser.add_argument("--ipadapter-mode", choices=("simple", "advanced"), default="simple")
    parser.add_argument("--ipadapter-preset", default="PLUS (high strength)")
    parser.add_argument("--ipadapter-weight", default=0.0, type=float)
    parser.add_argument("--ipadapter-weight-type", default="style transfer")
    parser.add_argument("--ipadapter-combine-embeds", default="concat")
    parser.add_argument("--ipadapter-embeds-scaling", default="V only")
    parser.add_argument("--ipadapter-start", default=0.0, type=float)
    parser.add_argument("--ipadapter-end", default=0.78, type=float)
    parser.add_argument(
        "--ipadapter-attn-mask",
        choices=("none", "upper_body", "whole_character", "head_hair"),
        default="none",
    )
    parser.add_argument("--width", default=768, type=int)
    parser.add_argument("--height", default=768, type=int)
    parser.add_argument("--steps", default=18, type=int)
    parser.add_argument("--cfg", default=5.0, type=float)
    parser.add_argument("--denoise", default=0.55, type=float)
    parser.add_argument("--controlnet-strength", default=0.78, type=float)
    parser.add_argument("--controlnet-end", default=0.82, type=float)
    parser.add_argument("--sampler", default="dpmpp_2m")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--seed", default=919191, type=int)
    parser.add_argument("--seed-step", default=0, type=int)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--positive", default=POSITIVE_PROMPT)
    parser.add_argument("--negative", default=NEGATIVE_PROMPT)
    add_queue_wait_arguments(parser)
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    args = parser.parse_args()

    pose_indices = _parse_indices(args.pose_indices)
    pose_paths = [args.pose_dir / f"frame_{index:03d}.png" for index in pose_indices]
    missing = [path for path in pose_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing pose frames: {missing}")
    sidecar_indices = _parse_indices(args.sidecar_indices) if args.sidecar_indices else pose_indices
    if args.sidecar_dir and len(sidecar_indices) != len(pose_indices):
        raise ValueError("--sidecar-indices must have the same count as --pose-indices")
    sidecar_paths: list[Path] = []
    if args.sidecar_dir:
        sidecar_paths = [args.sidecar_dir / f"frame_{index:03d}.png" for index in sidecar_indices]
        missing_sidecars = [path for path in sidecar_paths if not path.exists()]
        if missing_sidecars:
            raise FileNotFoundError(f"Missing sidecar frames: {missing_sidecars}")

    label = _safe_label(args.run_label or f"{args.source_image.stem}_pose_regen")
    run_dir = build_timestamped_run_dir(args.output_root, "reference_pose_regen", label)
    write_run_profile(
        run_dir,
        category="reference_pose_regen",
        label=label,
        args=args,
        memo=(
            "Mechanism probe: source reference image + SDXL OpenPose ControlNet per-frame regeneration, "
            "optionally with IPAdapter identity/reference lock."
        ),
    )
    frames_dir = run_dir / "frames"
    source_dir = run_dir / "source_reference"
    pose_out_dir = run_dir / "control_pose"
    sidecar_out_dir = run_dir / "lower_body_sidecar" if args.sidecar_dir else None
    workflow_dir = run_dir / "workflow"
    for path in (frames_dir, source_dir, pose_out_dir, workflow_dir):
        path.mkdir(parents=True, exist_ok=True)
    if sidecar_out_dir:
        sidecar_out_dir.mkdir(parents=True, exist_ok=True)

    prepared_source = _prepare_source(args.source_image, source_dir / "source_image.png", args.width, args.height)
    server = args.comfy_url.rstrip("/")
    source_name = _upload_image(server, prepared_source)
    attn_mask_name = None
    attn_mask_path = None
    if args.ipadapter_weight > 0 and args.ipadapter_attn_mask != "none":
        attn_mask_path = _make_ipadapter_attn_mask(
            args.ipadapter_attn_mask,
            source_dir / f"ipadapter_attn_mask_{args.ipadapter_attn_mask}.png",
            args.width,
            args.height,
        )
        attn_mask_name = _upload_image(server, attn_mask_path)

    report: dict[str, Any] = {
        "status": "started",
        "purpose": "Probe reference-conditioned still-frame regeneration from reusable walk pose controls.",
        "source_image": str(args.source_image),
        "prepared_source": str(prepared_source),
        "settings": {
            "checkpoint": args.checkpoint,
            "controlnet": args.controlnet,
            "ipadapter_model": args.ipadapter_model,
            "ipadapter_mode": args.ipadapter_mode,
            "ipadapter_preset": args.ipadapter_preset,
            "ipadapter_weight": args.ipadapter_weight,
            "ipadapter_weight_type": args.ipadapter_weight_type,
            "ipadapter_combine_embeds": args.ipadapter_combine_embeds,
            "ipadapter_embeds_scaling": args.ipadapter_embeds_scaling,
            "ipadapter_start": args.ipadapter_start,
            "ipadapter_end": args.ipadapter_end,
            "ipadapter_attn_mask": args.ipadapter_attn_mask,
            "ipadapter_attn_mask_path": str(attn_mask_path) if attn_mask_path else None,
            "width": args.width,
            "height": args.height,
            "steps": args.steps,
            "cfg": args.cfg,
            "denoise": args.denoise,
            "controlnet_strength": args.controlnet_strength,
            "controlnet_end": args.controlnet_end,
            "sidecar_dir": str(args.sidecar_dir) if args.sidecar_dir else None,
            "sidecar_indices": sidecar_indices if args.sidecar_dir else None,
            "sidecar_controlnet": args.sidecar_controlnet if args.sidecar_dir else None,
            "sidecar_strength": args.sidecar_strength if args.sidecar_dir else None,
            "sidecar_start": args.sidecar_start if args.sidecar_dir else None,
            "sidecar_end": args.sidecar_end if args.sidecar_dir else None,
            "sampler": args.sampler,
            "scheduler": args.scheduler,
            "seed": args.seed,
            "seed_step": args.seed_step,
            "pose_indices": pose_indices,
            "positive": args.positive,
            "negative": args.negative,
        },
        "frames": [],
    }
    report_path = run_dir / "reference_pose_regen_report.json"

    output_paths: list[Path] = []
    copied_pose_paths: list[Path] = []
    copied_sidecar_paths: list[Path] = []
    try:
        for out_index, pose_path in progress_iter(
            list(enumerate(pose_paths)),
            total=len(pose_paths),
            desc="reference pose regeneration",
            unit="frame",
        ):
            copied_pose = pose_out_dir / f"pose_{out_index:03d}_src_{pose_indices[out_index]:03d}.png"
            _prepare_pose(pose_path, copied_pose, args.width, args.height)
            copied_pose_paths.append(copied_pose)
            pose_name = _upload_image(server, copied_pose)
            sidecar_name = None
            copied_sidecar = None
            if sidecar_paths and sidecar_out_dir:
                copied_sidecar = sidecar_out_dir / f"sidecar_{out_index:03d}_src_{sidecar_indices[out_index]:03d}.png"
                _prepare_pose(sidecar_paths[out_index], copied_sidecar, args.width, args.height)
                copied_sidecar_paths.append(copied_sidecar)
                sidecar_name = _upload_image(server, copied_sidecar)
            workflow = _workflow(
                args,
                source_name,
                pose_name,
                out_index,
                attn_mask_name=attn_mask_name,
                sidecar_image_name=sidecar_name,
            )
            workflow_path = workflow_dir / f"frame_{out_index:03d}.json"
            workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            prompt_id = _queue_prompt(server, workflow, args=args)
            history = _wait_for_history(server, prompt_id, args.timeout_seconds)
            image_bytes = _download_first_saveimage(server, history, "12")
            output_path = frames_dir / f"frame_{out_index:03d}.png"
            Image.open(BytesIO(image_bytes)).convert("RGB").save(output_path)
            output_paths.append(output_path)
            report["frames"].append(
                {
                    "index": out_index,
                    "pose_index": pose_indices[out_index],
                    "pose": str(copied_pose),
                    "sidecar_index": sidecar_indices[out_index] if copied_sidecar else None,
                    "sidecar": str(copied_sidecar) if copied_sidecar else None,
                    "workflow": str(workflow_path),
                    "prompt_id": prompt_id,
                    "output": str(output_path),
                    "source_delta": _mean_delta(prepared_source, output_path),
                }
            )
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
        contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=min(8, len(output_paths)))
        pose_sheet = make_contact_sheet(copied_pose_paths, run_dir / "pose_contact_sheet.png", columns=min(8, len(copied_pose_paths)))
        sidecar_sheet = None
        if copied_sidecar_paths:
            sidecar_sheet = make_contact_sheet(
                copied_sidecar_paths,
                run_dir / "sidecar_contact_sheet.png",
                columns=min(8, len(copied_sidecar_paths)),
            )
        comparison = _make_comparison_sheet(prepared_source, copied_pose_paths, output_paths, run_dir / "comparison_sheet.png")
        report.update(
            {
                "status": "completed",
                "frame_count": len(output_paths),
                "frames_dir": str(frames_dir),
                "preview_gif": str(preview),
                "contact_sheet": str(contact_sheet),
                "pose_contact_sheet": str(pose_sheet),
                "sidecar_contact_sheet": str(sidecar_sheet) if sidecar_sheet else None,
                "comparison_sheet": str(comparison),
                "motion_metrics": _motion_metrics(output_paths),
                "mean_source_delta": round(
                    sum(float(item["source_delta"]) for item in report["frames"]) / max(1, len(report["frames"])),
                    5,
                ),
            }
        )
    except Exception as exc:
        report.update({"status": "failed", "error": repr(exc)})
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(report_path)
        raise

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(
        json.dumps(
            {
                "status": report["status"],
                "frame_count": report["frame_count"],
                "frames_dir": report["frames_dir"],
                "preview_gif": report["preview_gif"],
                "contact_sheet": report["contact_sheet"],
                "comparison_sheet": report["comparison_sheet"],
                "sidecar_contact_sheet": report.get("sidecar_contact_sheet"),
                "motion_metrics": report["motion_metrics"],
                "mean_source_delta": report["mean_source_delta"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _workflow(
    args: argparse.Namespace,
    source_image_name: str,
    pose_image_name: str,
    index: int,
    *,
    attn_mask_name: str | None = None,
    sidecar_image_name: str | None = None,
) -> dict[str, Any]:
    seed = args.seed + index * args.seed_step
    model_ref: list[Any] = ["1", 0]
    ipadapter_nodes: dict[str, Any] = {}
    if args.ipadapter_weight > 0:
        apply_node_id = "14"
        model_ref = [apply_node_id, 0]
        mask_nodes = _ipadapter_mask_nodes(attn_mask_name)
        apply_inputs: dict[str, Any] = {
            "model": ["13", 0],
            "ipadapter": ["13", 1],
            "image": ["5", 0],
            "weight": args.ipadapter_weight,
            "start_at": args.ipadapter_start,
            "end_at": args.ipadapter_end,
            "weight_type": args.ipadapter_weight_type,
        }
        if mask_nodes:
            apply_inputs["attn_mask"] = ["16", 0]
        class_type = "IPAdapter"
        if args.ipadapter_mode == "advanced":
            class_type = "IPAdapterAdvanced"
            apply_inputs.update(
                {
                    "combine_embeds": args.ipadapter_combine_embeds,
                    "embeds_scaling": args.ipadapter_embeds_scaling,
                }
            )
        ipadapter_nodes = {
            "13": {
                "class_type": "IPAdapterUnifiedLoader",
                "inputs": {
                    "model": ["1", 0],
                    "preset": args.ipadapter_preset,
                },
            },
            "14": {
                "class_type": class_type,
                "inputs": apply_inputs,
            },
            **mask_nodes,
        }
    conditioning_ref: tuple[list[Any], list[Any]] = (["9", 0], ["9", 1])
    sidecar_nodes: dict[str, Any] = {}
    if sidecar_image_name and args.sidecar_strength > 0:
        conditioning_ref = (["19", 0], ["19", 1])
        sidecar_nodes = {
            "17": {"class_type": "LoadImage", "inputs": {"image": sidecar_image_name}},
            "18": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": args.sidecar_controlnet}},
            "19": {
                "class_type": "ControlNetApplyAdvanced",
                "inputs": {
                    "positive": ["9", 0],
                    "negative": ["9", 1],
                    "control_net": ["18", 0],
                    "image": ["17", 0],
                    "strength": args.sidecar_strength,
                    "start_percent": args.sidecar_start,
                    "end_percent": args.sidecar_end,
                },
            },
        }
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": args.positive}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": args.negative}},
        "4": {"class_type": "LoadImage", "inputs": {"image": source_image_name}},
        "5": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["4", 0],
                "upscale_method": "lanczos",
                "width": args.width,
                "height": args.height,
                "crop": "disabled",
            },
        },
        "6": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "LoadImage", "inputs": {"image": pose_image_name}},
        "8": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": args.controlnet}},
        "9": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["2", 0],
                "negative": ["3", 0],
                "control_net": ["8", 0],
                "image": ["7", 0],
                "strength": args.controlnet_strength,
                "start_percent": 0.0,
                "end_percent": args.controlnet_end,
            },
        },
        "10": {
            "class_type": "KSampler",
            "inputs": {
                "model": model_ref,
                "positive": conditioning_ref[0],
                "negative": conditioning_ref[1],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": args.steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": args.denoise,
            },
        },
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
        "12": {
            "class_type": "SaveImage",
            "inputs": {"images": ["11", 0], "filename_prefix": f"reference_pose_regen_{index:03d}"},
        },
        **ipadapter_nodes,
        **sidecar_nodes,
    }


def _ipadapter_mask_nodes(attn_mask_name: str | None) -> dict[str, Any]:
    if not attn_mask_name:
        return {}
    return {
        "15": {"class_type": "LoadImage", "inputs": {"image": attn_mask_name}},
        "16": {"class_type": "ImageToMask", "inputs": {"image": ["15", 0], "channel": "red"}},
    }


def _prepare_source(source: Path, output: Path, width: int, height: int) -> Path:
    image = Image.open(source).convert("RGBA")
    canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
    canvas.alpha_composite(image)
    flattened = canvas.convert("RGB")
    scale = min(width / flattened.width, height / flattened.height)
    resized = flattened.resize(
        (max(1, round(flattened.width * scale)), max(1, round(flattened.height * scale))),
        Image.Resampling.LANCZOS,
    )
    out = Image.new("RGB", (width, height), (255, 255, 255))
    out.paste(resized, ((width - resized.width) // 2, (height - resized.height) // 2))
    output.parent.mkdir(parents=True, exist_ok=True)
    out.save(output)
    return output


def _prepare_pose(source: Path, output: Path, width: int, height: int) -> Path:
    image = Image.open(source).convert("RGB").resize((width, height), Image.Resampling.BICUBIC)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def _make_ipadapter_attn_mask(kind: str, output: Path, width: int, height: int) -> Path:
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    if kind == "upper_body":
        box = _scale_box(width, height, (0.30, 0.05, 0.70, 0.64))
    elif kind == "whole_character":
        box = _scale_box(width, height, (0.24, 0.04, 0.76, 0.94))
    elif kind == "head_hair":
        box = _scale_box(width, height, (0.34, 0.03, 0.66, 0.36))
    else:
        raise ValueError(f"Unknown IPAdapter attention mask kind: {kind}")
    draw.rounded_rectangle(box, radius=max(8, round(width * 0.04)), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(2, round(width * 0.018))))
    output.parent.mkdir(parents=True, exist_ok=True)
    mask.convert("RGB").save(output)
    return output


def _scale_box(width: int, height: int, box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    return (
        round(width * left),
        round(height * top),
        round(width * right),
        round(height * bottom),
    )


def _make_comparison_sheet(source: Path, poses: list[Path], outputs: list[Path], output: Path) -> Path:
    tile_width = 256
    tile_height = 256
    columns = len(outputs)
    sheet = Image.new("RGB", (columns * tile_width, tile_height * 3), (245, 245, 245))
    source_image = _thumb(source, tile_width, tile_height)
    for column, (pose, frame) in enumerate(zip(poses, outputs)):
        sheet.paste(source_image, (column * tile_width, 0))
        sheet.paste(_thumb(pose, tile_width, tile_height), (column * tile_width, tile_height))
        sheet.paste(_thumb(frame, tile_width, tile_height), (column * tile_width, tile_height * 2))
    sheet.save(output)
    return output


def _thumb(path: Path, width: int, height: int) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    out = Image.new("RGB", (width, height), (255, 255, 255))
    out.paste(image, ((width - image.width) // 2, (height - image.height) // 2))
    return out


def _motion_metrics(paths: list[Path]) -> dict[str, float]:
    if len(paths) < 2:
        return {"mean_frame_delta": 0.0, "max_frame_delta": 0.0, "min_frame_delta": 0.0}
    deltas = [_mean_delta(left, right) for left, right in zip(paths, paths[1:])]
    return {
        "mean_frame_delta": round(sum(deltas) / len(deltas), 3),
        "max_frame_delta": round(max(deltas), 3),
        "min_frame_delta": round(min(deltas), 3),
    }


def _mean_delta(left_path: Path, right_path: Path) -> float:
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB").resize(left.size, Image.Resampling.BICUBIC)
    pairs = zip(left.tobytes(), right.tobytes())
    return sum(abs(left_byte - right_byte) for left_byte, right_byte in pairs) / (left.width * left.height * 3)


def _parse_indices(value: str) -> list[int]:
    indices = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not indices:
        raise ValueError("--pose-indices must include at least one integer")
    return indices


if __name__ == "__main__":
    main()
