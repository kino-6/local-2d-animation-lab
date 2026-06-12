from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

sys.path.append(str(Path(__file__).resolve().parent))

from generate_fullbody_reference_candidates import NEGATIVE_PROMPT
from generate_fullbody_reference_candidates import _assess_candidate
from generate_fullbody_reference_candidates import _download_first_saveimage
from generate_fullbody_reference_candidates import _queue_prompt
from generate_fullbody_reference_candidates import _safe_label
from generate_fullbody_reference_candidates import _select_candidate
from generate_fullbody_reference_candidates import _upload_image
from generate_fullbody_reference_candidates import _wait_for_history
from generate_fullbody_reference_candidates import _workflow as _txt2img_workflow
from natural_sprite_lab.comfy_queue import add_queue_wait_arguments
from natural_sprite_lab.pose_templates import render_pose_frame
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.progress import progress_iter
from natural_sprite_lab.quality import analyze_frame_quality
from natural_sprite_lab.quality.start_frame import make_start_frame_debug_sheet
from natural_sprite_lab.quality.start_frame import prepare_clean_start_frame


DEFAULT_IDENTITY_TRAITS = (
    "same character design as the provided reference image, anime game character, full body, "
    "clean cel shading, readable outfit, stable face, complete hands and shoes"
)


@dataclass(frozen=True)
class ActionKeyframeCandidate:
    name: str
    action: str
    pose_variant: str
    positive_template: str
    seed_offset: int


ACTION_CANDIDATES: dict[str, tuple[ActionKeyframeCandidate, ...]] = {
    "run": (
        ActionKeyframeCandidate(
            name="run_low_stride",
            action="run",
            pose_variant="run_low_stride",
            seed_offset=0,
            positive_template=(
                "masterpiece, best quality, polished anime game sprite keyframe, one full-body character only, "
                "side view facing right, conservative running stride, low knee lift, both feet near the ground, "
                "small forward lean, arms pumping opposite the legs, feet fully visible, centered on clean white background, "
                "crisp cel shading, no high kick, no dramatic illustration pose, {identity_traits}"
            ),
        ),
        ActionKeyframeCandidate(
            name="run_compact_forward_stride",
            action="run",
            pose_variant="run_compact_forward_stride",
            seed_offset=700,
            positive_template=(
                "masterpiece, best quality, polished anime game sprite keyframe, one full-body character only, "
                "right-facing side-view compact run stride, body leaning slightly forward, front leg reaching only a little, "
                "rear leg kicking back only a little, clear readable shoes and hands, clean white background, "
                "no high kick, no flying hair, {identity_traits}"
            ),
        ),
    ),
    "hit_light": (
        ActionKeyframeCandidate(
            name="hit_light_small_stagger",
            action="hit_light",
            pose_variant="hit_light_small_stagger",
            seed_offset=0,
            positive_template=(
                "masterpiece, best quality, polished anime game sprite keyframe, one full-body character only, "
                "side view facing right, light hit reaction pose, small backward stagger, one foot shifted back, "
                "torso bends only slightly, arms close to body, feet fully visible, clean white background, "
                "no falling pose, no crouch, {identity_traits}"
            ),
        ),
        ActionKeyframeCandidate(
            name="hit_light_guard_recover",
            action="hit_light",
            pose_variant="hit_light_guard_recover",
            seed_offset=700,
            positive_template=(
                "masterpiece, best quality, polished anime game sprite keyframe, one full-body character only, "
                "right-facing side view light hit guard recovery pose, slight crouch, one arm guarding chest, "
                "small weight shift, complete shoes, clean white background, {identity_traits}"
            ),
        ),
    ),
    "hit_heavy": (
        ActionKeyframeCandidate(
            name="hit_heavy_compact_recoil",
            action="hit_heavy",
            pose_variant="hit_heavy_compact_recoil",
            seed_offset=0,
            positive_template=(
                "masterpiece, best quality, polished anime game sprite keyframe, one full-body character only, "
                "side view facing right, heavy damage recoil pose, upper body bent back moderately from impact, "
                "one foot sliding back a short distance, arms tense near the body, feet fully visible, clean white background, "
                "no fall, no extreme crouch, no flying hair, {identity_traits}"
            ),
        ),
        ActionKeyframeCandidate(
            name="hit_heavy_mid_recover",
            action="hit_heavy",
            pose_variant="hit_heavy_mid_recover",
            seed_offset=700,
            positive_template=(
                "masterpiece, best quality, polished anime game sprite keyframe, one full-body character only, "
                "right-facing side view heavy hit recovery pose, medium crouch, one knee bent slightly, one arm guarding body, "
                "readable silhouette, complete shoes, clean white background, no kneeling, no extreme pose, {identity_traits}"
            ),
        ),
    ),
    "attack_sword": (
        ActionKeyframeCandidate(
            name="attack_sword_active",
            action="attack_sword",
            pose_variant="attack_sword_active",
            seed_offset=0,
            positive_template=(
                "masterpiece, best quality, polished anime game sprite keyframe, one full-body character only, "
                "side view facing right, active sword slash pose, both hands connected to one short glowing sword, "
                "diagonal slash follow-through, readable weapon, complete feet, clean white background, {identity_traits}"
            ),
        ),
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate action endpoint keyframes for Wan first/last-frame animation probes."
    )
    parser.add_argument("--action", required=True, choices=tuple(ACTION_CANDIDATES))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_action_keyframes"), type=Path)
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--checkpoint", default="novaOrangeXL_v120.safetensors")
    parser.add_argument("--controlnet", default="SDXL\\OpenPoseXL2.safetensors")
    parser.add_argument("--width", default=1024, type=int)
    parser.add_argument("--height", default=1024, type=int)
    parser.add_argument("--steps", default=28, type=int)
    parser.add_argument("--cfg", default=5.4, type=float)
    parser.add_argument("--sampler", default="dpmpp_2m")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--seed", default=717220, type=int)
    parser.add_argument("--controlnet-strength", default=0.74, type=float)
    parser.add_argument(
        "--source-image",
        default=None,
        type=Path,
        help="Optional full-body start frame for reference-conditioned img2img endpoint generation.",
    )
    parser.add_argument(
        "--denoise",
        default=0.48,
        type=float,
        help="Img2img denoise used only when --source-image is provided.",
    )
    parser.add_argument(
        "--min-endpoint-delta",
        default=12.0,
        type=float,
        help="Minimum mean pixel delta from --source-image for an endpoint to count as action-bearing.",
    )
    add_queue_wait_arguments(parser)
    parser.add_argument("--identity-traits", default=DEFAULT_IDENTITY_TRAITS)
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    args = parser.parse_args()

    server = args.comfy_url.rstrip("/")
    label = _safe_label(f"{args.input.stem}_{args.action}_keyframes")
    run_dir = args.output_root / time.strftime(f"{label}_%Y%m%d_%H%M%S")
    source_dir = run_dir / "generated"
    cleaned_dir = run_dir / "cleaned"
    pose_dir = run_dir / "control_pose"
    workflow_dir = run_dir / "workflow"
    review_dir = run_dir / "review"
    reference_dir = run_dir / "source_reference"
    for path in (source_dir, cleaned_dir, pose_dir, workflow_dir, review_dir, reference_dir):
        path.mkdir(parents=True, exist_ok=True)

    source_image_name = None
    prepared_source_image = None
    if args.source_image is not None:
        prepared_source_image = reference_dir / "source_image.png"
        _prepare_source_image(args.source_image, prepared_source_image, args.width, args.height)
        source_image_name = _upload_image(server, prepared_source_image)

    report: dict[str, Any] = {
        "status": "started",
        "purpose": "Create action endpoint keyframes before Wan first/last-frame generation.",
        "input_reference": str(args.input),
        "action": args.action,
        "settings": {
            "checkpoint": args.checkpoint,
            "controlnet": args.controlnet,
            "width": args.width,
            "height": args.height,
            "steps": args.steps,
            "cfg": args.cfg,
            "sampler": args.sampler,
            "scheduler": args.scheduler,
            "seed": args.seed,
            "controlnet_strength": args.controlnet_strength,
            "mode": "img2img_openpose" if source_image_name else "txt2img_openpose",
            "source_image": str(args.source_image) if args.source_image else None,
            "prepared_source_image": str(prepared_source_image) if prepared_source_image else None,
            "denoise": args.denoise if source_image_name else None,
            "min_endpoint_delta": args.min_endpoint_delta if source_image_name else None,
            "identity_traits": args.identity_traits,
            "negative": NEGATIVE_PROMPT,
        },
        "candidates": [],
    }
    report_path = run_dir / "action_keyframe_report.json"

    try:
        candidates = list(enumerate(ACTION_CANDIDATES[args.action]))
        for index, candidate in progress_iter(
            candidates,
            total=len(candidates),
            desc=f"{args.action} endpoint candidates",
            unit="candidate",
        ):
            seed = args.seed + candidate.seed_offset
            pose_path = pose_dir / f"{candidate.name}.png"
            pose_image = _pose_image(candidate.pose_variant, args.width, args.height)
            pose_image.save(pose_path)
            pose_name = _upload_image(server, pose_path)
            positive = candidate.positive_template.format(identity_traits=args.identity_traits)
            workflow = _workflow(args, positive, NEGATIVE_PROMPT, seed, pose_name, candidate.name, source_image_name)
            workflow_path = workflow_dir / f"{candidate.name}.json"
            workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            prompt_id = _queue_prompt(server, workflow, args=args)
            history = _wait_for_history(server, prompt_id, args.timeout_seconds)
            image_bytes = _download_first_saveimage(server, history, "7")
            source_path = source_dir / f"{index:02d}_{candidate.name}.png"
            source_path.write_bytes(image_bytes)

            cleaned_path = cleaned_dir / f"{index:02d}_{candidate.name}.png"
            start_report = prepare_clean_start_frame(source_path, cleaned_path, width=args.width, height=args.height)
            quality = analyze_frame_quality(cleaned_path, index=index)
            debug_sheet = make_start_frame_debug_sheet(source_path, cleaned_path, review_dir / f"{candidate.name}_debug.png")
            assessment = _assess_candidate(start_report.to_dict(), quality.to_dict(), args.width, args.height)
            source_delta = None
            if prepared_source_image is not None:
                source_delta = _mean_delta(prepared_source_image, cleaned_path)
                if source_delta < args.min_endpoint_delta:
                    assessment["status"] = "manual_review_or_retake"
                    assessment["issue_codes"] = sorted(
                        {*assessment["issue_codes"], "endpoint_delta_too_low"}
                    )
                    assessment["framing_notes"] = [
                        *assessment.get("framing_notes", []),
                        "endpoint remains too close to the source frame to drive first/last action interpolation",
                    ]
            report["candidates"].append(
                {
                    "name": candidate.name,
                    "action": candidate.action,
                    "pose_variant": candidate.pose_variant,
                    "seed": seed,
                    "prompt_id": prompt_id,
                    "positive": positive,
                    "pose_image": str(pose_path),
                    "workflow": str(workflow_path),
                    "source": str(source_path),
                    "cleaned": str(cleaned_path),
                    "debug_sheet": str(debug_sheet),
                    "start_frame_report": start_report.to_dict(),
                    "quality": quality.to_dict(),
                    "source_delta": round(source_delta, 5) if source_delta is not None else None,
                    "assessment": assessment,
                }
            )
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        selected = _select_candidate(report["candidates"])
        selected_dir = run_dir / "selected_keyframe"
        selected_dir.mkdir(parents=True, exist_ok=True)
        selected_path = selected_dir / "end_frame.png"
        Image.open(selected["cleaned"]).save(selected_path)
        report["status"] = "completed"
        report["selected"] = {
            "name": selected["name"],
            "source": selected["source"],
            "cleaned": selected["cleaned"],
            "selected_keyframe": str(selected_path),
            "selection_score": selected["assessment"]["selection_score"],
            "selection_status": selected["assessment"]["status"],
            "issue_codes": selected["assessment"]["issue_codes"],
        }
        report["contact_sheet"] = str(
            make_contact_sheet([Path(item["cleaned"]) for item in report["candidates"]], run_dir / "contact_sheet.png", columns=2)
        )
        summary_path = run_dir / "action_keyframe_review_summary.md"
        summary_path.write_text(_summary(report), encoding="utf-8")
        report["summary"] = str(summary_path)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"run_dir": str(run_dir), "selected_keyframe": str(selected_path), "report": str(report_path)}, indent=2))
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        raise


def _pose_image(variant: str, width: int, height: int) -> Image.Image:
    keypoints = {
        "nose": [0.535, 0.145],
        "neck": [0.50, 0.245],
        "right_shoulder": [0.535, 0.275],
        "right_elbow": [0.57, 0.420],
        "right_wrist": [0.555, 0.565],
        "left_shoulder": [0.465, 0.278],
        "left_elbow": [0.445, 0.425],
        "left_wrist": [0.455, 0.565],
        "right_hip": [0.526, 0.525],
        "right_knee": [0.545, 0.705],
        "right_ankle": [0.585, 0.905],
        "left_hip": [0.474, 0.525],
        "left_knee": [0.465, 0.710],
        "left_ankle": [0.430, 0.905],
    }
    if variant == "run_low_stride":
        keypoints.update(
            {
                "neck": [0.52, 0.250],
                "right_elbow": [0.60, 0.405],
                "right_wrist": [0.59, 0.520],
                "left_elbow": [0.41, 0.405],
                "left_wrist": [0.38, 0.515],
                "right_knee": [0.59, 0.710],
                "right_ankle": [0.66, 0.890],
                "left_knee": [0.43, 0.705],
                "left_ankle": [0.34, 0.875],
            }
        )
    elif variant == "run_compact_forward_stride":
        keypoints.update(
            {
                "neck": [0.535, 0.260],
                "right_wrist": [0.61, 0.465],
                "left_wrist": [0.40, 0.585],
                "right_knee": [0.60, 0.755],
                "right_ankle": [0.69, 0.905],
                "left_knee": [0.42, 0.685],
                "left_ankle": [0.34, 0.855],
            }
        )
    elif variant == "hit_light_small_stagger":
        keypoints.update(
            {
                "nose": [0.515, 0.155],
                "neck": [0.505, 0.260],
                "right_elbow": [0.585, 0.415],
                "right_wrist": [0.575, 0.555],
                "left_elbow": [0.445, 0.420],
                "left_wrist": [0.440, 0.560],
                "right_hip": [0.540, 0.535],
                "left_hip": [0.485, 0.535],
                "right_knee": [0.600, 0.720],
                "right_ankle": [0.675, 0.905],
                "left_knee": [0.450, 0.715],
                "left_ankle": [0.395, 0.905],
            }
        )
    elif variant == "hit_light_guard_recover":
        keypoints.update(
            {
                "nose": [0.530, 0.170],
                "neck": [0.515, 0.285],
                "right_elbow": [0.600, 0.410],
                "right_wrist": [0.635, 0.515],
                "left_elbow": [0.460, 0.405],
                "left_wrist": [0.500, 0.515],
                "right_hip": [0.540, 0.560],
                "left_hip": [0.485, 0.560],
                "right_knee": [0.600, 0.740],
                "right_ankle": [0.665, 0.910],
                "left_knee": [0.435, 0.735],
                "left_ankle": [0.370, 0.910],
            }
        )
    elif variant == "hit_heavy_compact_recoil":
        keypoints.update(
            {
                "nose": [0.500, 0.155],
                "neck": [0.495, 0.285],
                "right_shoulder": [0.530, 0.315],
                "left_shoulder": [0.455, 0.315],
                "right_elbow": [0.595, 0.360],
                "right_wrist": [0.640, 0.430],
                "left_elbow": [0.410, 0.360],
                "left_wrist": [0.365, 0.430],
                "right_hip": [0.550, 0.550],
                "left_hip": [0.495, 0.550],
                "right_knee": [0.625, 0.735],
                "right_ankle": [0.720, 0.900],
                "left_knee": [0.460, 0.735],
                "left_ankle": [0.395, 0.910],
            }
        )
    elif variant == "hit_heavy_mid_recover":
        keypoints.update(
            {
                "nose": [0.540, 0.190],
                "neck": [0.525, 0.315],
                "right_elbow": [0.605, 0.440],
                "right_wrist": [0.635, 0.555],
                "left_elbow": [0.450, 0.435],
                "left_wrist": [0.430, 0.555],
                "right_hip": [0.550, 0.585],
                "left_hip": [0.495, 0.585],
                "right_knee": [0.625, 0.755],
                "right_ankle": [0.700, 0.910],
                "left_knee": [0.445, 0.755],
                "left_ankle": [0.375, 0.910],
            }
        )
    elif variant == "attack_sword_active":
        keypoints.update(
            {
                "nose": [0.55, 0.170],
                "neck": [0.535, 0.290],
                "right_elbow": [0.66, 0.400],
                "right_wrist": [0.76, 0.455],
                "left_elbow": [0.58, 0.405],
                "left_wrist": [0.72, 0.470],
                "right_knee": [0.62, 0.745],
                "right_ankle": [0.73, 0.905],
                "left_knee": [0.43, 0.720],
                "left_ankle": [0.33, 0.900],
            }
        )
    frame = {
        "action": "action_keyframe",
        "variant": variant,
        "frame_index": 0,
        "phase": variant,
        "keypoints": keypoints,
    }
    return render_pose_frame(frame, width, height, style="controlnet_thin")


def _workflow(
    args: argparse.Namespace,
    positive: str,
    negative: str,
    seed: int,
    pose_image_name: str,
    prefix: str,
    source_image_name: str | None,
) -> dict[str, Any]:
    if source_image_name is None:
        return _txt2img_workflow(args, positive, negative, seed, pose_image_name, prefix)
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": positive}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative}},
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["10", 0],
                "negative": ["10", 1],
                "latent_image": ["13", 0],
                "seed": seed,
                "steps": args.steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": args.denoise,
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": f"action_keyframe_{prefix}"}},
        "8": {"class_type": "LoadImage", "inputs": {"image": pose_image_name}},
        "9": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": args.controlnet}},
        "10": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["2", 0],
                "negative": ["3", 0],
                "control_net": ["9", 0],
                "image": ["8", 0],
                "strength": args.controlnet_strength,
                "start_percent": 0.0,
                "end_percent": 0.82,
            },
        },
        "11": {"class_type": "LoadImage", "inputs": {"image": source_image_name}},
        "12": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["11", 0],
                "upscale_method": "lanczos",
                "width": args.width,
                "height": args.height,
                "crop": "disabled",
            },
        },
        "13": {"class_type": "VAEEncode", "inputs": {"pixels": ["12", 0], "vae": ["1", 2]}},
    }


def _prepare_source_image(source: Path, output: Path, width: int, height: int) -> Path:
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
    canvas.paste(resized, ((width - resized.width) // 2, (height - resized.height) // 2))
    canvas.save(output)
    return output


def _mean_delta(left_path: Path, right_path: Path) -> float:
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB").resize(left.size, Image.Resampling.BICUBIC)
    pairs = zip(left.tobytes(), right.tobytes())
    return sum(abs(left_byte - right_byte) for left_byte, right_byte in pairs) / (left.width * left.height * 3)


def _summary(report: dict[str, Any]) -> str:
    selected = report.get("selected", {})
    rows = []
    for candidate in report["candidates"]:
        assessment = candidate["assessment"]
        rows.append(
            "| "
            + " | ".join(
                [
                    candidate["name"],
                    assessment["status"],
                    str(assessment["selection_score"]),
                    str(candidate.get("source_delta") or "n/a"),
                    ", ".join(assessment["issue_codes"]) or "none",
                    candidate["cleaned"],
                ]
            )
            + " |"
        )
    return "\n".join(
        [
            "# Action Keyframe Candidate Review",
            "",
            f"- input: `{report['input_reference']}`",
            f"- action: `{report['action']}`",
            f"- selected: `{selected.get('selected_keyframe', '')}`",
            f"- selected_status: `{selected.get('selection_status', '')}`",
            f"- contact_sheet: `{report.get('contact_sheet', '')}`",
            "",
        "| candidate | status | score | source_delta | issues | cleaned |",
        "|---|---:|---:|---:|---|---|",
            *rows,
            "",
            "Visual review remains required before using the selected image as a Wan first/last endpoint.",
        ]
    ) + "\n"


if __name__ == "__main__":
    main()
