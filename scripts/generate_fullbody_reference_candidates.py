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

from natural_sprite_lab.comfy_queue import add_queue_wait_arguments
from natural_sprite_lab.comfy_queue import wait_for_queue_capacity_from_args
from natural_sprite_lab.pose_templates import render_pose_frame
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.progress import ProgressTimer
from natural_sprite_lab.progress import progress_iter
from natural_sprite_lab.quality import analyze_frame_quality
from natural_sprite_lab.quality.start_frame import make_start_frame_debug_sheet
from natural_sprite_lab.quality.start_frame import prepare_clean_start_frame


DEFAULT_IDENTITY_TRAITS = (
    "same character design as the provided reference image, young anime girl, warm brown bob haircut, "
    "small pink hair clip, large amber eyes, white sailor school uniform, dark navy sailor collar, "
    "red necktie, dark pleated skirt, dark socks, brown loafers"
)

NEGATIVE_PROMPT = (
    "low quality, blurry, jpeg artifacts, cropped head, cropped feet, missing feet, missing shoes, "
    "extra limbs, extra legs, duplicate body, duplicate face, multiple characters, chibi, child body, "
    "front view when side view is requested, back view, character sheet, model sheet, turnaround sheet, "
    "multiple views, side-by-side figures, guide lines, red border lines, headgear, animal ears, helmet, "
    "weapon, sword, bow, staff, background scenery, text, watermark, logo, motion blur, ghost trail, afterimage"
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
            "feet fully visible, centered on canvas, clean white background, crisp cel shading, {identity_traits}, "
            "neutral standing walk-ready pose, readable silhouette, complete hands and shoes, no model sheet"
        ),
    ),
    ReferenceCandidate(
        name="slight_three_quarter_side",
        pose_variant="three_quarter_side",
        seed_offset=1000,
        positive_template=(
            "masterpiece, best quality, polished anime game sprite animation start frame, one single character only, "
            "full body, slight 3/4 side view facing right, body turned to the right, not front-facing, "
            "feet fully visible, centered on canvas, clean white background, crisp cel shading, {identity_traits}, "
            "neutral standing walk-ready pose, readable silhouette, complete hands and shoes, no model sheet"
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
            "standing walk-ready pose with both shoes fully visible"
        ),
    ),
    ReferenceCandidate(
        name="side_walk_ready_retake",
        pose_variant="strict_side",
        seed_offset=3000,
        positive_template=(
            "masterpiece, best quality, single full-body anime game character, right-facing side-view walk start frame, "
            "not a character sheet, not a turnaround, one figure centered, full body from head to shoes, profile face, "
            "clean white background, crisp cel shading, {identity_traits}, readable feet and shoes"
        ),
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 1024 full-body side-view reference candidates for local Wan animation."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_fullbody_reference"), type=Path)
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
    parser.add_argument("--identity-traits", default=DEFAULT_IDENTITY_TRAITS)
    add_queue_wait_arguments(parser)
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    args = parser.parse_args()

    server = args.comfy_url.rstrip("/")
    run_dir = args.output_root / time.strftime(f"{_safe_label(args.input.stem)}_%Y%m%d_%H%M%S")
    source_dir = run_dir / "generated"
    cleaned_dir = run_dir / "cleaned"
    pose_dir = run_dir / "control_pose"
    workflow_dir = run_dir / "workflow"
    review_dir = run_dir / "review"
    for path in (source_dir, cleaned_dir, pose_dir, workflow_dir, review_dir):
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
            positive = candidate.positive_template.format(identity_traits=args.identity_traits)
            workflow = _workflow(args, positive, NEGATIVE_PROMPT, seed, pose_name, candidate.name)
            workflow_path = workflow_dir / f"{candidate.name}.json"
            workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            prompt_id = _queue_prompt(server, workflow, args=args)
            history = _wait_for_history(server, prompt_id, args.timeout_seconds)
            image_bytes = _download_first_saveimage(server, history, "7")
            source_path = source_dir / f"{index:02d}_{candidate.name}.png"
            Image.open(BytesIO(image_bytes)).convert("RGB").save(source_path)

            cleaned_path = cleaned_dir / f"{index:02d}_{candidate.name}.png"
            start_report = prepare_clean_start_frame(source_path, cleaned_path, width=args.width, height=args.height)
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
        report["status"] = "completed"
        report["selected"] = {
            "name": selected["name"],
            "source": selected["source"],
            "cleaned": selected["cleaned"],
            "selected_reference": str(selected_path),
            "selection_score": selected["assessment"]["selection_score"],
            "selection_status": selected["assessment"]["status"],
            "issue_codes": selected["assessment"]["issue_codes"],
        }
        report["contact_sheet"] = str(
            make_contact_sheet([Path(item["cleaned"]) for item in report["candidates"]], run_dir / "contact_sheet.png", columns=2)
        )
        report["source_contact_sheet"] = str(
            make_contact_sheet([Path(item["source"]) for item in report["candidates"]], run_dir / "source_contact_sheet.png", columns=2)
        )
        summary_path = run_dir / "reference_review_summary.md"
        summary_path.write_text(_summary(report), encoding="utf-8")
        report["summary"] = str(summary_path)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"run_dir": str(run_dir), "selected_reference": str(selected_path), "report": str(report_path)}, indent=2))
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        raise


def _pose_image(variant: str, width: int, height: int) -> Image.Image:
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
    frame = {
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
    return render_pose_frame(frame, width, height, style="controlnet_thin")


def _workflow(
    args: argparse.Namespace,
    positive: str,
    negative: str,
    seed: int,
    pose_image_name: str,
    prefix: str,
) -> dict[str, Any]:
    workflow: dict[str, Any] = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": positive}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": args.width, "height": args.height, "batch_size": 1}},
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["10", 0],
                "negative": ["10", 1],
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
