from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image
from PIL import ImageDraw

from natural_sprite_lab.comfy_queue import add_queue_wait_arguments
from natural_sprite_lab.comfy_queue import wait_for_queue_capacity_from_args
from natural_sprite_lab.pose_templates import render_pose_frame
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.progress import ProgressTimer
from natural_sprite_lab.progress import progress_iter
from natural_sprite_lab.quality import analyze_frame_quality
from natural_sprite_lab.quality.start_frame import make_start_frame_debug_sheet
from natural_sprite_lab.quality.start_frame import prepare_clean_start_frame
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


DEFAULT_IDENTITY_TRAITS = (
    "same character design as the provided reference image, young anime girl, warm brown bob haircut, "
    "small pink hair clip, large amber eyes, white sailor school uniform, dark navy sailor collar, "
    "red necktie, dark pleated skirt, dark socks, brown loafers"
)

NEGATIVE_PROMPT = (
    "low quality, blurry, jpeg artifacts, cropped head, cropped feet, missing feet, missing shoes, "
    "extra limbs, extra legs, duplicate body, duplicate face, multiple characters, chibi, child body, merged legs, "
    "front view when side view is requested, back view, character sheet, model sheet, turnaround sheet, "
    "multiple views, side-by-side figures, guide lines, red border lines, headgear, animal ears, helmet, "
    "weapon, sword, bow, staff, bicycle, vehicle, prop, chair, background scenery, text, watermark, logo, motion blur, ghost trail, afterimage, "
    "long cloak covering legs, coat hiding legs, skirt hiding knees, shoes touching each other, single foot blob, "
    "black shadow merged with shoes, unreadable lower legs, rear view, looking away from camera, "
    "front-facing full-body portrait, looking at viewer, fashion illustration pose, feet crossed, toes hidden, shoes hidden by skirt"
)


@dataclass(frozen=True)
class ReferenceCandidate:
    name: str
    pose_variant: str
    positive_template: str
    seed_offset: int


CANDIDATES = (
    ReferenceCandidate(
        name="strict_side_profile",
        pose_variant="strict_side",
        seed_offset=0,
        positive_template=(
            "masterpiece, best quality, polished anime game sprite animation start frame, one single character only, "
            "full body, strict right-facing side profile, profile face, one visible eye, nose points right, torso side-on, "
            "feet fully visible and separated, both shoes readable, lower legs unobstructed, centered on canvas, "
            "clean white background, crisp cel shading, {identity_traits}, walk-cycle neutral contact pose, "
            "both shoes on the ground, shoes separated by visible white space, side-view shoe silhouettes, "
            "readable silhouette, complete hands and shoes, no model sheet"
        ),
    ),
    ReferenceCandidate(
        name="slight_three_quarter_side",
        pose_variant="three_quarter_side",
        seed_offset=1000,
        positive_template=(
            "masterpiece, best quality, polished anime game sprite animation start frame, one single character only, "
            "full body, slight 3/4 side view facing right, body turned to the right, not front-facing, "
            "feet fully visible and separated, two shoes readable, lower legs not hidden by clothes, centered on canvas, clean white background, crisp cel shading, {identity_traits}, "
            "walk-cycle neutral contact pose, both shoes on the ground, side-view shoe silhouettes, readable silhouette, complete hands and shoes, no model sheet"
        ),
    ),
    ReferenceCandidate(
        name="strict_side_profile_retake",
        pose_variant="strict_side",
        seed_offset=2000,
        positive_template=(
            "masterpiece, best quality, clean anime game sprite animation start frame, exactly one full-body girl, "
            "right-facing side view only, profile silhouette, profile face, one eye visible, nose and shoes point right, "
            "plain white background, no border, no guide line, crisp cel shading, {identity_traits}, "
            "walk-cycle neutral contact pose with both shoes fully visible and separated by white space, slim visible lower legs"
        ),
    ),
    ReferenceCandidate(
        name="side_walk_ready_retake",
        pose_variant="strict_side",
        seed_offset=3000,
        positive_template=(
            "masterpiece, best quality, single full-body anime game character, right-facing side-view walk start frame, "
            "not a character sheet, not a turnaround, one figure centered, full body from head to shoes, profile face, "
            "clean white background, crisp cel shading, {identity_traits}, readable separated feet and shoes, clear ankles, "
            "both shoes planted on the ground as a walk-cycle contact frame"
        ),
    ),
    ReferenceCandidate(
        name="face_visible_side_sprite",
        pose_variant="strict_side",
        seed_offset=4000,
        positive_template=(
            "masterpiece, best quality, 2d game sprite animation start frame, exactly one full-body character only, "
            "right-facing side view, face visible in profile, one blue eye visible, nose points right, chest points right, "
            "not back view, not rear view, not front view, no second character, no turnaround sheet, centered full body, "
            "head to shoes visible, plain white background, crisp cel shading, {identity_traits}, walk-cycle neutral contact pose, "
            "two separated shoes, visible lower legs, no cloak or coat covering the legs"
        ),
    ),
    ReferenceCandidate(
        name="side_profile_single_sprite",
        pose_variant="strict_side",
        seed_offset=5000,
        positive_template=(
            "high quality anime 2d game sprite, one single full-body woman, right-facing clean side profile, "
            "visible face and one visible eye, visible nose and mouth, complete hands and separated shoes, "
            "no rear view, no back of head, no front-facing pose, no paired figures, no model sheet, no cropped limbs, "
            "white background, sharp cel shaded silhouette, lower legs unobstructed, {identity_traits}"
        ),
    ),
    ReferenceCandidate(
        name="walk_ready_clear_lower_legs",
        pose_variant="strict_side",
        seed_offset=6000,
        positive_template=(
            "masterpiece, best quality, animation-ready 2d game sprite start frame, one full-body character only, "
            "strict right-facing side profile, profile face visible, walk-cycle neutral contact pose, "
            "both lower legs clearly visible, feet apart, shoes separated by white space, ankles readable, "
            "no long coat, no cloak, no skirt covering knees, clean white background, crisp cel shading, {identity_traits}"
        ),
    ),
    ReferenceCandidate(
        name="side_profile_shoes_apart",
        pose_variant="strict_side",
        seed_offset=7000,
        positive_template=(
            "high quality anime game sprite start frame, full body single character, right-facing side profile, "
            "head to shoes visible, face in profile, one eye visible, torso side-on, legs slim and readable, "
            "left shoe and right shoe separated, clear contact shadows under each shoe, plain white background, "
            "no cape, no robe, no model sheet, {identity_traits}"
        ),
    ),
    ReferenceCandidate(
        name="walk_sprite_no_leg_occlusion",
        pose_variant="strict_side",
        seed_offset=8000,
        positive_template=(
            "polished 2d game walk animation start frame, single full-body character, right-facing side view, "
            "walk-cycle neutral contact pose, profile face, visible hands, visible knees, visible ankles, "
            "two distinct feet, two distinct shoes, clothing does not overlap the lower legs, clean white background, "
            "crisp line art and cel shading, {identity_traits}"
        ),
    ),
    ReferenceCandidate(
        name="compact_side_game_sprite",
        pose_variant="three_quarter_side",
        seed_offset=9000,
        positive_template=(
            "compact anime 2d game sprite start frame, one full-body character, slight side view facing right, "
            "not front view, not rear view, face partly visible, clean readable silhouette, "
            "feet shoulder-width apart, shoes separated and fully visible, lower legs not hidden by outfit, "
            "plain white background, no panel, no guide lines, {identity_traits}"
        ),
    ),
    ReferenceCandidate(
        name="profile_walk_contact_no_portrait",
        pose_variant="strict_side",
        seed_offset=10000,
        positive_template=(
            "animation production keyframe for a 2d side-scrolling game, exactly one full-body character, "
            "right-facing profile only, not looking at viewer, no front-facing torso, no character sheet, no prop, "
            "walk-cycle contact pose, front shoe forward and rear shoe back, both shoes planted on one ground line, "
            "clear ankle gap, visible knees, readable shoe silhouettes, plain white background, crisp cel shaded sprite, {identity_traits}"
        ),
    ),
    ReferenceCandidate(
        name="small_stride_side_walk_sprite",
        pose_variant="strict_side",
        seed_offset=11000,
        positive_template=(
            "clean 2d game sprite start frame, one full-body anime girl only, right-facing side profile, "
            "small stride walk-contact pose, nose points right, chest points right, shoulders side-on, "
            "hands close to body, knees visible, ankles visible, two separated brown loafers readable, "
            "no second figure, no model sheet, no bike, no object, plain white background, {identity_traits}"
        ),
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 1024 full-body side-view reference candidates for local Wan animation."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--checkpoint", default="novaOrangeXL_v120.safetensors")
    parser.add_argument("--controlnet", default="SDXL\\OpenPoseXL2.safetensors")
    parser.add_argument("--width", default=1024, type=int)
    parser.add_argument("--height", default=1024, type=int)
    parser.add_argument("--steps", default=32, type=int)
    parser.add_argument("--cfg", default=5.6, type=float)
    parser.add_argument("--sampler", default="dpmpp_2m")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--seed", default=717220, type=int)
    parser.add_argument("--controlnet-strength", default=0.72, type=float)
    parser.add_argument("--sidecar-style", default="none", choices=("none", "foot_contact_lineart"))
    parser.add_argument("--sidecar-controlnet", default="SDXL\\t2i-adapter_diffusers_xl_lineart.safetensors")
    parser.add_argument("--sidecar-strength", default=0.0, type=float)
    parser.add_argument("--sidecar-start-percent", default=0.0, type=float)
    parser.add_argument("--sidecar-end-percent", default=0.45, type=float)
    parser.add_argument("--identity-traits", default=DEFAULT_IDENTITY_TRAITS)
    add_queue_wait_arguments(parser)
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    args = parser.parse_args()

    server = args.comfy_url.rstrip("/")
    label = _safe_label(args.input.stem)
    run_dir = build_timestamped_run_dir(args.output_root, "fullbody_reference", label)
    write_run_profile(run_dir, category="fullbody_reference", label=label, args=args)
    source_dir = run_dir / "generated"
    cleaned_dir = run_dir / "cleaned"
    pose_dir = run_dir / "control_pose"
    sidecar_dir = run_dir / "sidecar_pose"
    workflow_dir = run_dir / "workflow"
    review_dir = run_dir / "review"
    for path in (source_dir, cleaned_dir, pose_dir, sidecar_dir, workflow_dir, review_dir):
        path.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "status": "started",
        "purpose": "Create full-body side-view reference candidates before Wan/VACE walk generation.",
        "input_reference": str(args.input),
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
            "sidecar_style": args.sidecar_style,
            "sidecar_controlnet": args.sidecar_controlnet,
            "sidecar_strength": args.sidecar_strength,
            "sidecar_start_percent": args.sidecar_start_percent,
            "sidecar_end_percent": args.sidecar_end_percent,
            "identity_traits": args.identity_traits,
            "negative": NEGATIVE_PROMPT,
        },
        "candidates": [],
    }
    report_path = run_dir / "reference_candidates_report.json"

    try:
        candidates = list(enumerate(CANDIDATES))
        for index, candidate in progress_iter(
            candidates,
            total=len(candidates),
            desc="fullbody reference candidates",
            unit="candidate",
        ):
            seed = args.seed + candidate.seed_offset
            pose_path = pose_dir / f"{candidate.name}.png"
            pose_image = _pose_image(candidate.pose_variant, args.width, args.height)
            pose_image.save(pose_path)
            pose_name = _upload_image(server, pose_path)
            sidecar_path = None
            sidecar_name = None
            if _sidecar_enabled(args):
                sidecar_path = sidecar_dir / f"{candidate.name}.png"
                sidecar_image = _foot_contact_sidecar_image(candidate.pose_variant, args.width, args.height)
                sidecar_image.save(sidecar_path)
                sidecar_name = _upload_image(server, sidecar_path)
            positive = candidate.positive_template.format(identity_traits=args.identity_traits)
            workflow = _workflow(args, positive, NEGATIVE_PROMPT, seed, pose_name, candidate.name, sidecar_name)
            workflow_path = workflow_dir / f"{candidate.name}.json"
            workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            prompt_id = _queue_prompt(server, workflow, args=args)
            history = _wait_for_history(server, prompt_id, args.timeout_seconds)
            image_bytes = _download_first_saveimage(server, history, "7")
            source_path = source_dir / f"{index:02d}_{candidate.name}.png"
            Image.open(BytesIO(image_bytes)).convert("RGB").save(source_path)

            cleaned_path = cleaned_dir / f"{index:02d}_{candidate.name}.png"
            start_report = prepare_clean_start_frame(
                source_path,
                cleaned_path,
                width=args.width,
                height=args.height,
                require_profile_detail=True,
                require_lower_body_readiness=True,
                max_background_contamination_ratio=0.08,
            )
            quality = analyze_frame_quality(cleaned_path, index=index)
            debug_sheet = make_start_frame_debug_sheet(source_path, cleaned_path, review_dir / f"{candidate.name}_debug.png")
            assessment = _assess_candidate(start_report.to_dict(), quality.to_dict(), args.width, args.height)
            report["candidates"].append(
                {
                    "name": candidate.name,
                    "pose_variant": candidate.pose_variant,
                    "seed": seed,
                    "prompt_id": prompt_id,
                    "positive": positive,
                    "pose_image": str(pose_path),
                    "sidecar_image": str(sidecar_path) if sidecar_path else None,
                    "workflow": str(workflow_path),
                    "source": str(source_path),
                    "cleaned": str(cleaned_path),
                    "debug_sheet": str(debug_sheet),
                    "start_frame_report": start_report.to_dict(),
                    "quality": quality.to_dict(),
                    "assessment": assessment,
                }
            )
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        selected = _select_candidate(report["candidates"])
        selected_dir = run_dir / "selected_reference"
        selected_dir.mkdir(parents=True, exist_ok=True)
        selected_path = selected_dir / "start_frame.png"
        Image.open(selected["cleaned"]).save(selected_path)
        animation_start_path = selected_dir / "animation_probe_start_source.png"
        Image.open(selected["source"]).save(animation_start_path)
        rechecked_path = selected_dir / "start_frame_rechecked.png"
        cleaned_reference_recheck = prepare_clean_start_frame(
            selected_path,
            rechecked_path,
            width=args.width,
            height=args.height,
            require_profile_detail=True,
            require_lower_body_readiness=True,
            max_background_contamination_ratio=0.08,
        )
        selection_status = selected["assessment"]["status"]
        animation_probe_allowed = selection_status == "candidate_ok"
        report["status"] = "completed"
        report["selected"] = {
            "asset_status": "start_frame_candidate_only",
            "name": selected["name"],
            "source": selected["source"],
            "cleaned": selected["cleaned"],
            "selected_reference": str(selected_path),
            "animation_probe_start_image": str(animation_start_path),
            "cleaned_reference_recheck": cleaned_reference_recheck.to_dict(),
            "selection_score": selected["assessment"]["selection_score"],
            "selection_status": selection_status,
            "animation_probe_allowed": animation_probe_allowed,
            "blocking_status": None if animation_probe_allowed else "blocked_start_reference_quality",
            "issue_codes": selected["assessment"]["issue_codes"],
            "lower_body_readiness": selected["start_frame_report"].get("lower_body_readiness", {}),
            "agent_review_checklist": {
                "side_view_confidence": "manual_review_required",
                "foot_readability": "manual_review_required",
                "lower_leg_occlusion": "manual_review_required",
                "expected_walk_suitability": "manual_review_required",
            },
        }
        report["contact_sheet"] = str(
            make_contact_sheet([Path(item["cleaned"]) for item in report["candidates"]], run_dir / "contact_sheet.png", columns=2)
        )
        report["source_contact_sheet"] = str(
            make_contact_sheet([Path(item["source"]) for item in report["candidates"]], run_dir / "source_contact_sheet.png", columns=2)
        )
        summary_path = run_dir / "reference_review_summary.md"
        summary_path.write_text(_summary(report), encoding="utf-8")
        memo_path = run_dir / "memo.md"
        with memo_path.open("a", encoding="utf-8") as memo:
            memo.write("\n## Start-Frame Review Checklist\n\n")
            memo.write("- selected asset status: `start_frame_candidate_only`\n")
            memo.write(f"- animation probe allowed: `{animation_probe_allowed}`\n")
            memo.write("- use `selected_reference/animation_probe_start_source.png` for Wan probes so the frame is normalized exactly once\n")
            if not animation_probe_allowed:
                memo.write("- blocking status: `blocked_start_reference_quality`\n")
            memo.write("- side-view confidence: manual review required\n")
            memo.write("- foot readability: manual review required\n")
            memo.write("- lower-leg occlusion: manual review required\n")
            memo.write("- expected walk suitability: manual review required\n")
        report["summary"] = str(summary_path)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"run_dir": str(run_dir), "selected_reference": str(selected_path), "report": str(report_path)}, indent=2))
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        raise


def _sidecar_enabled(args: argparse.Namespace) -> bool:
    return getattr(args, "sidecar_style", "none") != "none" and float(getattr(args, "sidecar_strength", 0.0)) > 0.0


def _pose_frame(variant: str) -> dict[str, Any]:
    if variant == "strict_side":
        center = 0.50
        shoulder_span = 0.035
        hip_span = 0.026
        nose_x = 0.535
    else:
        center = 0.50
        shoulder_span = 0.070
        hip_span = 0.052
        nose_x = 0.545
    return {
        "action": "walk",
        "variant": variant,
        "frame_index": 0,
        "phase": "neutral_fullbody_reference",
        "keypoints": {
            "nose": [nose_x, 0.145],
            "neck": [center, 0.245],
            "right_shoulder": [center + shoulder_span, 0.275],
            "right_elbow": [center + shoulder_span + 0.035, 0.420],
            "right_wrist": [center + shoulder_span + 0.020, 0.565],
            "left_shoulder": [center - shoulder_span, 0.278],
            "left_elbow": [center - shoulder_span - 0.020, 0.425],
            "left_wrist": [center - shoulder_span - 0.005, 0.565],
            "right_hip": [center + hip_span, 0.525],
            "right_knee": [center + 0.045, 0.705],
            "right_ankle": [center + 0.095, 0.905],
            "left_hip": [center - hip_span, 0.525],
            "left_knee": [center - 0.035, 0.710],
            "left_ankle": [center - 0.070, 0.905],
        },
    }


def _pose_image(variant: str, width: int, height: int) -> Image.Image:
    frame = _pose_frame(variant)
    return render_pose_frame(frame, width, height, style="controlnet_thin")


def _foot_contact_sidecar_image(variant: str, width: int, height: int) -> Image.Image:
    frame = _pose_frame(variant)
    keypoints = frame["keypoints"]
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    def xy(name: str) -> tuple[int, int]:
        point = keypoints[name]
        return int(point[0] * width), int(point[1] * height)

    def line(a: str, b: str, fill: tuple[int, int, int], line_width: int) -> None:
        draw.line([xy(a), xy(b)], fill=fill, width=line_width)

    stroke = max(3, width // 170)
    soft_stroke = max(2, width // 240)
    ground_y = int(0.925 * height)
    draw.line(
        [(int(0.34 * width), ground_y), (int(0.66 * width), ground_y)],
        fill=(190, 190, 190),
        width=max(2, width // 260),
    )
    for hip, knee, ankle in (
        ("right_hip", "right_knee", "right_ankle"),
        ("left_hip", "left_knee", "left_ankle"),
    ):
        line(hip, knee, (45, 45, 45), stroke)
        line(knee, ankle, (45, 45, 45), stroke)
        ax, ay = xy(ankle)
        shoe_w = max(38, int(width * 0.070))
        shoe_h = max(12, int(height * 0.020))
        draw.rounded_rectangle(
            [ax - shoe_w // 3, ground_y - shoe_h, ax + shoe_w, ground_y + shoe_h // 2],
            radius=max(3, shoe_h // 3),
            outline=(20, 20, 20),
            width=soft_stroke,
        )
        draw.ellipse(
            [ax - stroke, ay - stroke, ax + stroke, ay + stroke],
            outline=(20, 20, 20),
            width=soft_stroke,
        )
    return image


def _workflow(
    args: argparse.Namespace,
    positive: str,
    negative: str,
    seed: int,
    pose_image_name: str,
    prefix: str,
    sidecar_image_name: str | None = None,
) -> dict[str, Any]:
    sampler_positive = ["10", 0]
    sampler_negative = ["10", 1]
    workflow: dict[str, Any] = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": positive}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": args.width, "height": args.height, "batch_size": 1}},
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": sampler_positive,
                "negative": sampler_negative,
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": args.steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": 1.0,
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": f"fullbody_ref_{prefix}"}},
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
    }
    if _sidecar_enabled(args) and sidecar_image_name:
        workflow["11"] = {"class_type": "LoadImage", "inputs": {"image": sidecar_image_name}}
        workflow["12"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": args.sidecar_controlnet}}
        workflow["13"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["10", 0],
                "negative": ["10", 1],
                "control_net": ["12", 0],
                "image": ["11", 0],
                "strength": args.sidecar_strength,
                "start_percent": args.sidecar_start_percent,
                "end_percent": args.sidecar_end_percent,
            },
        }
        workflow["5"]["inputs"]["positive"] = ["13", 0]
        workflow["5"]["inputs"]["negative"] = ["13", 1]
    return workflow


def _assess_candidate(
    start_report: dict[str, Any],
    quality: dict[str, Any],
    width: int,
    height: int,
) -> dict[str, Any]:
    issue_codes = set(str(code) for code in start_report.get("issue_codes", []))
    issue_codes.update(str(code) for code in quality.get("issue_codes", []))
    bbox = start_report.get("main_bbox")
    bbox_score = 0.0
    framing_notes: list[str] = []
    if bbox:
        left, top, right, bottom = [float(value) for value in bbox]
        bbox_height = (bottom - top) / height
        bbox_width = (right - left) / width
        bottom_ratio = bottom / height
        top_ratio = top / height
        if bbox_height < 0.56:
            issue_codes.add("not_full_body_enough")
            framing_notes.append("foreground bbox is too short for a full-body Wan reference")
        if bottom_ratio < 0.76:
            issue_codes.add("feet_not_near_canvas_bottom")
            framing_notes.append("detected feet/shoes do not reach the lower canvas area")
        if top_ratio > 0.26:
            issue_codes.add("head_not_near_canvas_top")
            framing_notes.append("detected head starts too low for full-body framing")
        if bbox_width > 0.58:
            issue_codes.add("foreground_too_wide_for_side_reference")
            framing_notes.append("foreground is too wide for a side-view reference")
        bbox_score = max(0.0, min(1.0, bbox_height)) - max(0.0, bbox_width - 0.42)
    else:
        issue_codes.add("missing_foreground")

    hard_failure = bool(quality.get("hard_failure")) or any(
        code in issue_codes
        for code in {
            "missing_foreground",
            "extra_foreground_components_removed",
            "large_secondary_component",
            "foreground_too_small",
            "foreground_too_large",
            "duplicate_silhouette_area_high",
            "lower_body_blob_count_high",
            "not_full_body_enough",
            "feet_not_near_canvas_bottom",
            "foreground_too_wide_for_side_reference",
            "guide_or_panel_residue",
            "background_contamination_high",
            "possible_back_view_or_missing_profile_detail",
            "feet_not_separated",
            "shoes_unreadable",
            "lower_legs_occluded",
            "foot_zone_merged",
        }
    )
    score = float(quality.get("score", 0.0)) + bbox_score
    score -= 0.30 * len([code for code in issue_codes if code != "extra_foreground_components_removed"])
    status = "candidate_ok" if not hard_failure else "manual_review_or_retake"
    return {
        "status": status,
        "selection_score": round(score, 5),
        "issue_codes": sorted(issue_codes),
        "framing_notes": framing_notes,
        "requires_visual_review": True,
    }


def _select_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        raise ValueError("No candidates generated.")
    return max(
        candidates,
        key=lambda item: (
            item["assessment"]["status"] == "candidate_ok",
            float(item["assessment"]["selection_score"]),
            -len(item["assessment"]["issue_codes"]),
        ),
    )


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
                    ", ".join(assessment["issue_codes"]) or "none",
                    candidate["cleaned"],
                ]
            )
            + " |"
        )
    return "\n".join(
        [
            "# Full-Body Reference Candidate Review",
            "",
            f"- input: `{report['input_reference']}`",
            f"- selected: `{selected.get('selected_reference', '')}`",
            f"- selected_status: `{selected.get('selection_status', '')}`",
            f"- contact_sheet: `{report.get('contact_sheet', '')}`",
            "",
            "| candidate | status | score | issues | cleaned |",
            "|---|---:|---:|---|---|",
            *rows,
            "",
            "Visual review remains required before treating the selected image as an adopted Wan start reference.",
        ]
    ) + "\n"


def _upload_image(server_url: str, path: Path) -> str:
    data = path.read_bytes()
    filename = f"fullbody_ref_{uuid.uuid4().hex}.png"
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
            request = urllib.request.Request(f"{server_url}/history/{prompt_id}", method="GET")
            history = json.loads(_open(request, timeout=30).decode("utf-8"))
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
            time.sleep(1.0)
    raise TimeoutError(f"Timed out waiting for ComfyUI prompt: {prompt_id}")


def _download_first_saveimage(server_url: str, history: dict[str, Any], node_id: str) -> bytes:
    output = history.get("outputs", {}).get(node_id, {})
    images = output.get("images", [])
    if not images:
        raise RuntimeError(f"No SaveImage output found for node {node_id}")
    image = images[0]
    query = urllib.parse.urlencode(
        {
            "filename": image["filename"],
            "subfolder": image.get("subfolder", ""),
            "type": image.get("type", "output"),
        }
    )
    request = urllib.request.Request(f"{server_url}/view?{query}", method="GET")
    return _open(request, timeout=60)


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
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "fullbody_reference"


if __name__ == "__main__":
    main()
