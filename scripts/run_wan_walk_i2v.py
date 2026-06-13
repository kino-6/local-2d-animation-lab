from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

from natural_sprite_lab.comfy_queue import add_queue_wait_arguments
from natural_sprite_lab.comfy_queue import wait_for_queue_capacity_from_args
from natural_sprite_lab.foot_guides import render_foot_guide, walk_foot_guide_for
from natural_sprite_lab.pose_templates import load_pose_sequence, render_pose_frame
from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.progress import ProgressTimer
from natural_sprite_lab.progress import progress_iter
from natural_sprite_lab.quality.start_frame import prepare_clean_start_frame
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile
from natural_sprite_lab.weapon_guides import render_weapon_guide, weapon_guide_for


POSITIVE_PROMPT = (
    "anime game sprite, full body young woman character, side view walking in place, "
    "smooth natural walk cycle, legs alternating clearly, arms swinging opposite to legs, "
    "stable character identity, stable camera, clean white background, single character, "
    "crisp cel shading, sharp limbs, no motion trails, readable 2d game animation"
)

NEGATIVE_PROMPT = (
    "multiple characters, duplicate body, extra limbs, missing limbs, broken legs, broken feet, "
    "weapon, sword, bow, text, watermark, heavy camera motion, zoom, blur, cropped feet, "
    "motion blur, ghost trail, afterimage, smeared limb, transparent limb, background scenery, "
    "changing outfit, face melting"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a minimal Wan Image-to-Video action test in ComfyUI.")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument(
        "--start-image",
        default=Path(
            "outputs_controlnet_pdca/anima_00013/walk/walk_baseline/frames/"
            "anima_00013_walk_r01_000.png"
        ),
        type=Path,
    )
    parser.add_argument(
        "--end-image",
        default=Path(
            "outputs_controlnet_pdca/anima_00013/walk/walk_baseline/frames/"
            "anima_00013_walk_r01_014.png"
        ),
        type=Path,
    )
    parser.add_argument(
        "--mode",
        choices=(
            "i2v",
            "first_last",
            "fun_i2v",
            "fun_first_last",
            "fun_control",
            "wan22_fun_control",
            "animate_pose",
            "vace",
        ),
        default="i2v",
    )
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--pose-root", default=Path("pose_templates"), type=Path)
    parser.add_argument("--pose-template", default="walk")
    parser.add_argument("--pose-phase", default=0, type=int)
    parser.add_argument(
        "--pose-sample-span",
        default=None,
        type=int,
        help="Optional number of template frames to sample across for this Wan clip. Defaults to the full template.",
    )
    parser.add_argument(
        "--pose-render-style",
        choices=(
            "controlnet",
            "controlnet_thin",
            "wan_line",
            "wan_lower",
            "wan_confidence_lower",
            "wan_balanced",
            "wan_walk_lower",
            "vace_depth_proxy",
            "vace_side_proxy",
            "vace_walk_silhouette",
            "vace_walk_lower_hint",
            "vace_walk_confidence_hint",
        ),
        default="controlnet",
    )
    parser.add_argument("--character-mask", default=None, type=Path)
    parser.add_argument("--auto-character-mask", action="store_true")
    parser.add_argument("--character-mask-threshold", default=42, type=int)
    parser.add_argument("--character-mask-grow", default=11, type=int)
    parser.add_argument("--character-mask-blur", default=3, type=int)
    parser.add_argument("--invert-character-mask", action="store_true")
    parser.add_argument("--weapon-guide", choices=("none", "sword", "axe", "bow"), default="none")
    parser.add_argument(
        "--foot-guide",
        choices=("none", "walk"),
        default="none",
        help="Overlay a lower-body-only foot/contact guide on control-video frames.",
    )
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--normalize-start-frame", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reject-bad-start-frame", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--require-start-profile-detail", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--require-start-lower-body-readiness", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--height", default=512, type=int)
    parser.add_argument("--length", default=9, type=int)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--steps", default=4, type=int)
    parser.add_argument("--cfg", default=5.0, type=float)
    parser.add_argument("--sampler", default="uni_pc")
    parser.add_argument("--scheduler", default="simple")
    parser.add_argument("--seed", default=424242, type=int)
    parser.add_argument("--shift", default=8.0, type=float)
    parser.add_argument("--continue-motion-max-frames", default=5, type=int)
    parser.add_argument("--vace-strength", default=1.0, type=float)
    parser.add_argument("--unet", default="wan2.1_i2v_480p_14B_fp16.safetensors")
    parser.add_argument("--weight-dtype", default="fp8_e4m3fn")
    parser.add_argument("--vae", default="wan_2.1_vae.safetensors")
    parser.add_argument("--clip", default="umt5_xxl_fp8_e4m3fn_scaled.safetensors")
    parser.add_argument("--clip-vision", default="clip_vision_h.safetensors")
    parser.add_argument("--positive", default=POSITIVE_PROMPT)
    parser.add_argument("--negative", default=NEGATIVE_PROMPT)
    parser.add_argument("--post-trim-start", default=0, type=int)
    parser.add_argument("--post-trim-end", default=None, type=int)
    parser.add_argument("--timeout-seconds", default=1800.0, type=float)
    add_queue_wait_arguments(parser)
    args = parser.parse_args()

    run_label = args.run_label or f"{args.pose_template}_{args.mode}"
    run_dir = build_timestamped_run_dir(args.output_root, "wan_walk_i2v", _safe_label(run_label))
    write_run_profile(
        run_dir,
        category="wan_walk_i2v",
        label=run_label,
        args=args,
        memo="Wan I2V/action probe output. Keep workflow, generated frames, preview, and quality notes together.",
    )
    frames_dir = run_dir / "frames"
    workflow_dir = run_dir / "workflow"
    frames_dir.mkdir(parents=True, exist_ok=True)
    workflow_dir.mkdir(parents=True, exist_ok=True)

    start_report_path = run_dir / "start_frame_report.json"
    if args.normalize_start_frame:
        start_report = prepare_clean_start_frame(
            args.start_image,
            run_dir / "start_image.png",
            width=args.width,
            height=args.height,
            require_profile_detail=args.require_start_profile_detail,
            require_lower_body_readiness=args.require_start_lower_body_readiness,
        )
        start_report_path.write_text(json.dumps(start_report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.reject_bad_start_frame and start_report.status == "rejected":
            raise RuntimeError(f"Start frame rejected before Wan: {start_report.issue_codes}")
        start_image = run_dir / "start_image.png"
    else:
        start_image = _prepare_image(args.start_image, run_dir / "start_image.png", args.width, args.height)
        start_report_path = None
    image_name = _upload_image(args.comfy_url.rstrip("/"), start_image)
    character_mask = None
    character_mask_name = None
    if args.character_mask is not None or args.auto_character_mask:
        mask_source = args.character_mask if args.character_mask is not None else start_image
        character_mask = _prepare_character_mask(
            mask_source,
            run_dir / "character_mask.png",
            args.width,
            args.height,
            threshold=args.character_mask_threshold,
            grow=args.character_mask_grow,
            blur_radius=args.character_mask_blur,
            invert=args.invert_character_mask,
        )
        character_mask_name = _upload_image(args.comfy_url.rstrip("/"), character_mask)
    end_image = None
    end_image_name = None
    if args.mode in {"first_last", "fun_first_last"}:
        end_image = _prepare_image(args.end_image, run_dir / "end_image.png", args.width, args.height)
        end_image_name = _upload_image(args.comfy_url.rstrip("/"), end_image)
    workflow = _workflow(args, image_name)
    if args.mode == "first_last":
        assert end_image_name is not None
        workflow = _first_last_workflow(args, image_name, end_image_name)
    elif args.mode == "fun_i2v":
        workflow = _fun_workflow(args, image_name, None)
    elif args.mode == "fun_first_last":
        assert end_image_name is not None
        workflow = _fun_workflow(args, image_name, end_image_name)
    elif args.mode == "fun_control":
        control_names = _make_and_upload_control_video(args, run_dir / "control_video")
        workflow = _fun_control_workflow(args, image_name, control_names, class_type="WanFunControlToVideo")
    elif args.mode == "wan22_fun_control":
        control_names = _make_and_upload_control_video(args, run_dir / "control_video")
        workflow = _fun_control_workflow(args, image_name, control_names, class_type="Wan22FunControlToVideo")
    elif args.mode == "animate_pose":
        control_names = _make_and_upload_control_video(args, run_dir / "control_video")
        workflow = _animate_pose_workflow(args, image_name, control_names, character_mask_name)
    elif args.mode == "vace":
        control_names = _make_and_upload_control_video(args, run_dir / "control_video")
        workflow = _vace_workflow(args, image_name, control_names)
    workflow_path = workflow_dir / "wan_walk_i2v_api.json"
    workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report: dict[str, Any] = {
        "status": "started",
        "purpose": "Validate local Wan Image-to-Video as a video-consistent walk generation path.",
        "run_label": run_label,
        "mode": args.mode,
        "start_image": str(start_image),
        "start_frame_report": str(start_report_path) if start_report_path else None,
        "end_image": str(end_image) if end_image else None,
        "workflow": str(workflow_path),
        "settings": {
            "width": args.width,
            "height": args.height,
            "length": args.length,
            "fps": args.fps,
            "steps": args.steps,
            "cfg": args.cfg,
            "sampler": args.sampler,
            "scheduler": args.scheduler,
            "seed": args.seed,
            "shift": args.shift,
            "continue_motion_max_frames": args.continue_motion_max_frames,
            "vace_strength": args.vace_strength,
            "unet": args.unet,
            "weight_dtype": args.weight_dtype,
            "vae": args.vae,
            "clip": args.clip,
            "clip_vision": args.clip_vision,
            "positive": args.positive,
            "negative": args.negative,
            "pose_root": str(args.pose_root),
            "pose_template": args.pose_template,
            "pose_phase": args.pose_phase,
            "pose_sample_span": args.pose_sample_span,
            "pose_render_style": args.pose_render_style,
            "weapon_guide": args.weapon_guide,
            "foot_guide": args.foot_guide,
            "character_mask": str(character_mask) if character_mask else None,
            "auto_character_mask": args.auto_character_mask,
            "character_mask_threshold": args.character_mask_threshold,
            "character_mask_grow": args.character_mask_grow,
            "character_mask_blur": args.character_mask_blur,
            "invert_character_mask": args.invert_character_mask,
            "run_label": run_label,
            "post_trim_start": args.post_trim_start,
            "post_trim_end": args.post_trim_end,
        },
    }
    report_path = run_dir / "wan_walk_i2v_report.json"

    try:
        prompt_id = _queue_prompt(args.comfy_url.rstrip("/"), workflow, args=args)
        report["prompt_id"] = prompt_id
        history = _wait_for_history(args.comfy_url.rstrip("/"), prompt_id, args.timeout_seconds)
        frame_paths = _download_frames(args.comfy_url.rstrip("/"), history, frames_dir)
        frame_paths = _post_trim_frames(frame_paths, args.post_trim_start, args.post_trim_end, run_dir / "curated_frames")
        if not frame_paths:
            raise RuntimeError("ComfyUI completed but returned no downloadable frames.")
        preview = make_preview_gif(frame_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
        contact_sheet = make_contact_sheet(frame_paths, run_dir / "contact_sheet.png", columns=min(6, len(frame_paths)))
        report.update(
            {
                "status": "completed",
                "frame_count": len(frame_paths),
                "frames_dir": str(frames_dir),
                "preview_gif": str(preview),
                "contact_sheet": str(contact_sheet),
                "motion_metrics": _motion_metrics(frame_paths),
                "history_status": history.get("status", {}),
            }
        )
    except Exception as exc:
        report.update({"status": "failed", "error": repr(exc)})
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(report_path)
        raise

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(json.dumps({key: report[key] for key in ("status", "frame_count", "preview_gif", "contact_sheet", "motion_metrics")}, indent=2, ensure_ascii=False))


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "wan_i2v"


def _workflow(args: argparse.Namespace, image_name: str) -> dict[str, Any]:
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": args.unet, "weight_dtype": args.weight_dtype}},
        "2": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": args.shift}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": args.clip, "type": "wan", "device": "default"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": args.positive}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": args.negative}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": args.vae}},
        "7": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "8": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["7", 0],
                "upscale_method": "lanczos",
                "width": args.width,
                "height": args.height,
                "crop": "center",
            },
        },
        "9": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": args.clip_vision}},
        "10": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["9", 0], "image": ["8", 0], "crop": "center"}},
        "11": {
            "class_type": "WanImageToVideo",
            "inputs": {
                "positive": ["4", 0],
                "negative": ["5", 0],
                "vae": ["6", 0],
                "width": args.width,
                "height": args.height,
                "length": args.length,
                "batch_size": 1,
                "clip_vision_output": ["10", 0],
                "start_image": ["8", 0],
            },
        },
        "12": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 0],
                "positive": ["11", 0],
                "negative": ["11", 1],
                "latent_image": ["11", 2],
                "seed": args.seed,
                "steps": args.steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": 1.0,
            },
        },
        "13": {
            "class_type": "VAEDecodeTiled",
            "inputs": {
                "samples": ["12", 0],
                "vae": ["6", 0],
                "tile_size": 256,
                "overlap": 64,
                "temporal_size": 8,
                "temporal_overlap": 4,
            },
        },
        "14": {"class_type": "SaveImage", "inputs": {"images": ["13", 0], "filename_prefix": "natural_sprite_lab_wan_walk_i2v"}},
        "15": {
            "class_type": "SaveAnimatedWEBP",
            "inputs": {
                "images": ["13", 0],
                "filename_prefix": "natural_sprite_lab_wan_walk_i2v",
                "fps": float(args.fps),
                "lossless": True,
                "quality": 90,
                "method": "default",
            },
        },
    }


def _first_last_workflow(args: argparse.Namespace, start_image_name: str, end_image_name: str) -> dict[str, Any]:
    workflow = _workflow(args, start_image_name)
    workflow["16"] = {"class_type": "LoadImage", "inputs": {"image": end_image_name}}
    workflow["17"] = {
        "class_type": "ImageScale",
        "inputs": {
            "image": ["16", 0],
            "upscale_method": "lanczos",
            "width": args.width,
            "height": args.height,
            "crop": "disabled",
        },
    }
    workflow["18"] = {
        "class_type": "CLIPVisionEncode",
        "inputs": {"clip_vision": ["9", 0], "image": ["17", 0], "crop": "center"},
    }
    workflow["11"] = {
        "class_type": "WanFirstLastFrameToVideo",
        "inputs": {
            "positive": ["4", 0],
            "negative": ["5", 0],
            "vae": ["6", 0],
            "width": args.width,
            "height": args.height,
            "length": args.length,
            "batch_size": 1,
            "clip_vision_start_image": ["10", 0],
            "clip_vision_end_image": ["18", 0],
            "start_image": ["8", 0],
            "end_image": ["17", 0],
        },
    }
    return workflow


def _fun_workflow(args: argparse.Namespace, start_image_name: str, end_image_name: str | None) -> dict[str, Any]:
    workflow = _workflow(args, start_image_name)
    if end_image_name is not None:
        workflow["16"] = {"class_type": "LoadImage", "inputs": {"image": end_image_name}}
        workflow["17"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["16", 0],
                "upscale_method": "lanczos",
                "width": args.width,
                "height": args.height,
                "crop": "disabled",
            },
        }
    inputs: dict[str, Any] = {
        "positive": ["4", 0],
        "negative": ["5", 0],
        "vae": ["6", 0],
        "width": args.width,
        "height": args.height,
        "length": args.length,
        "batch_size": 1,
        "clip_vision_output": ["10", 0],
        "start_image": ["8", 0],
    }
    if end_image_name is not None:
        inputs["end_image"] = ["17", 0]
    workflow["11"] = {"class_type": "WanFunInpaintToVideo", "inputs": inputs}
    return workflow


def _fun_control_workflow(
    args: argparse.Namespace,
    start_image_name: str,
    control_image_names: list[str],
    *,
    class_type: str,
) -> dict[str, Any]:
    workflow = _workflow(args, start_image_name)
    final_control_ref = _add_control_video_nodes(workflow, control_image_names, args.width, args.height)
    inputs: dict[str, Any] = {
            "positive": ["4", 0],
            "negative": ["5", 0],
            "vae": ["6", 0],
            "width": args.width,
            "height": args.height,
            "length": args.length,
            "batch_size": 1,
            "control_video": final_control_ref,
    }
    if class_type == "Wan22FunControlToVideo":
        inputs["ref_image"] = ["8", 0]
    else:
        inputs["clip_vision_output"] = ["10", 0]
        inputs["start_image"] = ["8", 0]
    workflow["11"] = {"class_type": class_type, "inputs": inputs}
    return workflow


def _animate_pose_workflow(
    args: argparse.Namespace,
    reference_image_name: str,
    pose_image_names: list[str],
    character_mask_name: str | None = None,
) -> dict[str, Any]:
    workflow = _workflow(args, reference_image_name)
    final_pose_ref = _add_control_video_nodes(workflow, pose_image_names, args.width, args.height)
    mask_ref = _add_mask_node(workflow, character_mask_name, args.width, args.height) if character_mask_name else None
    workflow["11"] = {
        "class_type": "WanAnimateToVideo",
        "inputs": {
            "positive": ["4", 0],
            "negative": ["5", 0],
            "vae": ["6", 0],
            "width": args.width,
            "height": args.height,
            "length": args.length,
            "batch_size": 1,
            "continue_motion_max_frames": args.continue_motion_max_frames,
            "video_frame_offset": 0,
            "clip_vision_output": ["10", 0],
            "reference_image": ["8", 0],
            "pose_video": final_pose_ref,
        },
    }
    if mask_ref is not None:
        workflow["11"]["inputs"]["character_mask"] = mask_ref
    workflow["19"] = {
        "class_type": "TrimVideoLatent",
        "inputs": {"samples": ["12", 0], "trim_amount": ["11", 3]},
    }
    workflow["13"]["inputs"]["samples"] = ["19", 0]
    return workflow


def _vace_workflow(
    args: argparse.Namespace,
    reference_image_name: str,
    control_image_names: list[str],
) -> dict[str, Any]:
    workflow = _workflow(args, reference_image_name)
    final_control_ref = _add_control_video_nodes(workflow, control_image_names, args.width, args.height)
    workflow["11"] = {
        "class_type": "WanVaceToVideo",
        "inputs": {
            "positive": ["4", 0],
            "negative": ["5", 0],
            "vae": ["6", 0],
            "width": args.width,
            "height": args.height,
            "length": args.length,
            "batch_size": 1,
            "strength": args.vace_strength,
            "reference_image": ["8", 0],
            "control_video": final_control_ref,
        },
    }
    workflow["19"] = {
        "class_type": "TrimVideoLatent",
        "inputs": {"samples": ["12", 0], "trim_amount": ["11", 3]},
    }
    workflow["13"]["inputs"]["samples"] = ["19", 0]
    return workflow


def _add_mask_node(
    workflow: dict[str, Any],
    mask_image_name: str,
    width: int,
    height: int,
) -> list[Any]:
    workflow["200"] = {"class_type": "LoadImageMask", "inputs": {"image": mask_image_name, "channel": "red"}}
    return ["200", 0]


def _add_control_video_nodes(
    workflow: dict[str, Any],
    control_image_names: list[str],
    width: int,
    height: int,
) -> list[Any]:
    if not control_image_names:
        raise ValueError("control_image_names must not be empty")
    next_id = 20
    scaled_refs: list[list[Any]] = []
    for image_name in control_image_names:
        load_id = str(next_id)
        scale_id = str(next_id + 1)
        next_id += 2
        workflow[load_id] = {"class_type": "LoadImage", "inputs": {"image": image_name}}
        workflow[scale_id] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": [load_id, 0],
                "upscale_method": "nearest-exact",
                "width": width,
                "height": height,
                "crop": "disabled",
            },
        }
        scaled_refs.append([scale_id, 0])
    current = scaled_refs[0]
    for ref in scaled_refs[1:]:
        batch_id = str(next_id)
        next_id += 1
        workflow[batch_id] = {"class_type": "ImageBatch", "inputs": {"image1": current, "image2": ref}}
        current = [batch_id, 0]
    return current


def _prepare_image(source: Path, output: Path, width: int, height: int) -> Path:
    if not source.exists():
        raise FileNotFoundError(source)
    image = Image.open(source).convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    flattened = background.convert("RGB")
    scale = min(width / flattened.width, height / flattened.height)
    resized = flattened.resize(
        (max(1, round(flattened.width * scale)), max(1, round(flattened.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    left = (width - resized.width) // 2
    top = (height - resized.height) // 2
    canvas.paste(resized, (left, top))
    canvas.save(output)
    return output


def _prepare_character_mask(
    source: Path,
    output: Path,
    width: int,
    height: int,
    *,
    threshold: int,
    grow: int,
    blur_radius: int,
    invert: bool = False,
) -> Path:
    if not source.exists():
        raise FileNotFoundError(source)
    image = Image.open(source).convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    flattened = background.convert("RGB")
    scale = min(width / flattened.width, height / flattened.height)
    resized = flattened.resize(
        (max(1, round(flattened.width * scale)), max(1, round(flattened.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    left = (width - resized.width) // 2
    top = (height - resized.height) // 2
    canvas.paste(resized, (left, top))
    bg = _estimate_background(canvas)
    mask = Image.new("L", canvas.size, 0)
    pixels = canvas.load()
    mask_pixels = mask.load()
    for y in range(canvas.height):
        for x in range(canvas.width):
            red, green, blue = pixels[x, y]
            distance = abs(red - bg[0]) + abs(green - bg[1]) + abs(blue - bg[2])
            if distance >= threshold:
                mask_pixels[x, y] = 255
    if grow > 0:
        mask = mask.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    if blur_radius > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))
    if invert:
        from PIL import ImageChops

        mask = ImageChops.invert(mask)
    mask.save(output)
    return output


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    points = [
        (0, 0),
        (image.width - 1, 0),
        (0, image.height - 1),
        (image.width - 1, image.height - 1),
        (image.width // 2, 0),
        (image.width // 2, image.height - 1),
    ]
    pixels = image.load()
    samples = [pixels[x, y] for x, y in points]
    return tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))


def _make_and_upload_control_video(args: argparse.Namespace, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pose_frames = load_pose_sequence(args.pose_root, args.pose_template)
    if not pose_frames:
        raise ValueError(f"No pose frames found: {args.pose_root / (args.pose_template + '.json')}")
    names: list[str] = []
    for source_index in _pose_source_indices(
        pose_count=len(pose_frames),
        length=args.length,
        phase=args.pose_phase,
        sample_span=args.pose_sample_span,
    ):
        image = _render_control_frame(args, pose_frames[source_index], source_index, len(pose_frames))
        path = output_dir / f"pose_{len(names):03d}.png"
        image.save(path)
        names.append(_upload_image(args.comfy_url.rstrip("/"), path))
    return names


def _render_control_frame(
    args: argparse.Namespace,
    pose_frame: dict[str, Any],
    source_index: int,
    pose_count: int,
) -> Image.Image:
    image = render_pose_frame(pose_frame, args.width, args.height, style=args.pose_render_style)
    if getattr(args, "weapon_guide", "none") != "none":
        guide = weapon_guide_for(args.weapon_guide, source_index, pose_count)
        image = _paste_nonblack(image, render_weapon_guide(guide, args.width, args.height))
    if getattr(args, "foot_guide", "none") == "walk":
        guide = walk_foot_guide_for(source_index, pose_count)
        image = _paste_nonblack(image, render_foot_guide(guide, args.width, args.height))
    return image


def _paste_nonblack(base: Image.Image, overlay: Image.Image) -> Image.Image:
    overlay = overlay.convert("RGB")
    mask = overlay.convert("L").point(lambda value: 255 if value > 10 else 0)
    image = base.copy()
    image.paste(overlay, (0, 0), mask)
    return image


def _pose_source_indices(
    *,
    pose_count: int,
    length: int,
    phase: int,
    sample_span: int | None,
) -> list[int]:
    if pose_count <= 0:
        raise ValueError("pose_count must be positive")
    if length <= 0:
        raise ValueError("length must be positive")
    span = pose_count - 1 if sample_span is None else max(0, min(sample_span, pose_count - 1))
    return [(phase + round(index * span / max(1, length - 1))) % pose_count for index in range(length)]




def _upload_image(server_url: str, path: Path) -> str:
    data = path.read_bytes()
    filename = f"wan_walk_i2v_{uuid.uuid4().hex}.png"
    body, content_type = _multipart_image("image", filename, data)
    request = urllib.request.Request(
        f"{server_url}/upload/image",
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    payload = json.loads(_open(request, timeout=30).decode("utf-8"))
    return str(payload.get("name") or filename)


def _queue_prompt(
    server_url: str,
    workflow: dict[str, Any],
    *,
    args: argparse.Namespace | None = None,
) -> str:
    if args is not None:
        wait_for_queue_capacity_from_args(server_url, args)
    body = json.dumps({"prompt": workflow, "client_id": str(uuid.uuid4())}).encode("utf-8")
    request = urllib.request.Request(
        f"{server_url}/prompt",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    payload = json.loads(_open(request, timeout=30).decode("utf-8"))
    return str(payload["prompt_id"])


def _wait_for_history(server_url: str, prompt_id: str, timeout_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + timeout_seconds
    with ProgressTimer(total_seconds=timeout_seconds, desc=f"ComfyUI {prompt_id[:8]}") as progress:
        while time.monotonic() < deadline:
            history = _get_json(server_url, f"/history/{prompt_id}", timeout=30)
            if prompt_id in history:
                item = history[prompt_id]
                status = item.get("status", {})
                if status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI prompt failed: {status}")
                node_errors = item.get("node_errors")
                if node_errors:
                    raise RuntimeError(f"ComfyUI node errors: {node_errors}")
                return item
            progress.update_elapsed(time.monotonic() - started)
            time.sleep(2.0)
    raise TimeoutError(f"Timed out waiting for ComfyUI prompt: {prompt_id}")


def _download_frames(server_url: str, history: dict[str, Any], frames_dir: Path) -> list[Path]:
    paths: list[Path] = []
    save_image_output = history.get("outputs", {}).get("14", {})
    images = list(save_image_output.get("images", []))
    for image in progress_iter(images, total=len(images), desc="download Wan frames", unit="frame"):
        image_bytes = _download_image(server_url, image)
        local = frames_dir / f"frame_{len(paths):03d}.png"
        Image.open(BytesIO(image_bytes)).convert("RGBA").save(local)
        paths.append(local)
    return paths


def _post_trim_frames(frame_paths: list[Path], start: int, end: int | None, output_dir: Path) -> list[Path]:
    if start <= 0 and end is None:
        return frame_paths
    selected = frame_paths[start:end]
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for index, path in enumerate(selected):
        image = Image.open(path).convert("RGBA")
        out = output_dir / f"frame_{index:03d}.png"
        image.save(out)
        copied.append(out)
    return copied


def _download_image(server_url: str, image: dict[str, Any]) -> bytes:
    query = urllib.parse.urlencode(
        {
            "filename": image["filename"],
            "subfolder": image.get("subfolder", ""),
            "type": image.get("type", "output"),
        }
    )
    request = urllib.request.Request(f"{server_url}/view?{query}", method="GET")
    return _open(request, timeout=60)


def _get_json(server_url: str, path: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(f"{server_url}{path}", method="GET")
    return json.loads(_open(request, timeout=timeout).decode("utf-8"))


def _motion_metrics(frame_paths: list[Path]) -> dict[str, Any]:
    if len(frame_paths) < 2:
        return {"mean_frame_delta": 0.0, "max_frame_delta": 0.0}
    deltas = []
    previous = Image.open(frame_paths[0]).convert("RGB")
    for path in frame_paths[1:]:
        current = Image.open(path).convert("RGB")
        pairs = zip(previous.tobytes(), current.tobytes())
        delta = sum(abs(left - right) for left, right in pairs) / (previous.width * previous.height * 3)
        deltas.append(delta)
        previous = current
    return {
        "mean_frame_delta": round(sum(deltas) / len(deltas), 3),
        "max_frame_delta": round(max(deltas), 3),
        "min_frame_delta": round(min(deltas), 3),
    }


def _multipart_image(field_name: str, filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = f"----natural-sprite-lab-{uuid.uuid4().hex}"
    chunks = [
        f"--{boundary}\r\n".encode("ascii"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode("ascii"),
        data,
        f"\r\n--{boundary}--\r\n".encode("ascii"),
    ]
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _open(request: urllib.request.Request, timeout: float) -> bytes:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from ComfyUI: {detail}") from exc


if __name__ == "__main__":
    main()
