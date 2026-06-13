from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import deque
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from natural_sprite_lab.comfy_queue import add_queue_wait_arguments
from natural_sprite_lab.comfy_queue import wait_for_queue_capacity_from_args
from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.progress import ProgressTimer
from natural_sprite_lab.progress import progress_iter
from natural_sprite_lab.quality import analyze_frame_quality
from natural_sprite_lab.quality import prepare_analysis_frame
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


POSITIVE_PROMPT = (
    "masterpiece, best quality, polished anime game sprite frame, plain white background, "
    "clean cel shading, crisp line art, remove ghost trails and afterimages only, "
    "preserve the original character body, pose, outfit, face, colors, hands, feet, and weapon"
)

NEGATIVE_PROMPT = (
    "new pose, changed body, changed outfit, changed face, extra limbs, duplicate legs, "
    "broken hands, broken feet, detached weapon, broken weapon, motion blur, ghost trail, "
    "afterimage, smeared limb, extra character, background scenery, text, watermark"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect and locally repair Wan/img2img frame artifacts using explicit masks."
    )
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--checkpoint", default="novaOrangeXL_v120.safetensors")
    parser.add_argument("--width", default=1024, type=int)
    parser.add_argument("--height", default=1024, type=int)
    parser.add_argument("--steps", default=24, type=int)
    parser.add_argument("--cfg", default=5.6, type=float)
    parser.add_argument("--denoise", default=0.72, type=float)
    parser.add_argument("--sampler", default="dpmpp_2m")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--seed", default=111333, type=int)
    parser.add_argument("--seed-step", default=0, type=int)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--weak-threshold", default=34, type=int)
    parser.add_argument("--strong-threshold", default=92, type=int)
    parser.add_argument("--protect-grow", default=19, type=int)
    parser.add_argument("--mask-grow", default=7, type=int)
    parser.add_argument("--min-mask-coverage", default=0.0004, type=float)
    parser.add_argument("--max-mask-coverage", default=0.18, type=float)
    parser.add_argument(
        "--analysis-max-size",
        default=512,
        type=int,
        help="Downscale frames for artifact analysis only. Set 0 to analyze at full resolution.",
    )
    parser.add_argument("--weapon", choices=("none", "sword", "axe", "bow"), default="none")
    parser.add_argument("--mask-only", action="store_true")
    parser.add_argument(
        "--correction-plan",
        default=None,
        type=Path,
        help="Optional masked correction plan. Only allowed plan actions may be inpainted.",
    )
    parser.add_argument("--allowed-plan-action", default="local_inpaint_candidate")
    parser.add_argument(
        "--only-plan-action",
        default=None,
        help="If set, process only frames whose correction-plan action matches this value.",
    )
    parser.add_argument("--positive", default=POSITIVE_PROMPT)
    parser.add_argument("--negative", default=NEGATIVE_PROMPT)
    parser.add_argument(
        "--external-mask-dir",
        default=None,
        type=Path,
        help="Optional directory of frame_###.png masks from region diagnostics.",
    )
    add_queue_wait_arguments(parser)
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")
    plan_actions = _plan_action_by_index(args.correction_plan)
    indexed_frames = _select_indexed_frames(frame_paths, plan_actions, args.only_plan_action)
    if not indexed_frames:
        raise ValueError(f"No frames matched only-plan-action={args.only_plan_action!r}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_artifact_repair")
    run_dir = build_timestamped_run_dir(args.output_root, "artifact_repair", label)
    write_run_profile(
        run_dir,
        category="artifact_repair",
        label=label,
        args=args,
        memo="Masked artifact analysis/repair run. Strong structural failures should remain quality-gate failures.",
    )
    source_dir = run_dir / "source_frames"
    masks_dir = run_dir / "masks"
    person_masks_dir = run_dir / "person_masks"
    background_masks_dir = run_dir / "background_cleanup_masks"
    overlays_dir = run_dir / "overlays"
    repaired_dir = run_dir / "frames"
    workflow_dir = run_dir / "workflow"
    for path in (source_dir, masks_dir, person_masks_dir, background_masks_dir, overlays_dir, repaired_dir, workflow_dir):
        path.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "status": "started",
        "purpose": (
            "Repair only explicitly masked artifacts. Strong duplicate limbs and broken weapons "
            "are quality-gate failures, not problems to hide with img2img."
        ),
        "source_frames_dir": str(args.frames_dir),
        "settings": {
            "checkpoint": args.checkpoint,
            "width": args.width,
            "height": args.height,
            "steps": args.steps,
            "cfg": args.cfg,
            "denoise": args.denoise,
            "sampler": args.sampler,
            "scheduler": args.scheduler,
            "seed": args.seed,
            "seed_step": args.seed_step,
            "weak_threshold": args.weak_threshold,
            "strong_threshold": args.strong_threshold,
            "protect_grow": args.protect_grow,
            "mask_grow": args.mask_grow,
            "min_mask_coverage": args.min_mask_coverage,
            "max_mask_coverage": args.max_mask_coverage,
            "analysis_max_size": args.analysis_max_size,
            "weapon": args.weapon,
            "mask_only": args.mask_only,
            "correction_plan": str(args.correction_plan) if args.correction_plan else None,
            "allowed_plan_action": args.allowed_plan_action,
            "only_plan_action": args.only_plan_action,
            "external_mask_dir": str(args.external_mask_dir) if args.external_mask_dir else None,
            "positive": args.positive,
            "negative": args.negative,
        },
        "prompt_ids": [],
        "frame_reports": [],
    }
    report_path = run_dir / "artifact_repair_report.json"

    try:
        source_outputs: list[Path] = []
        mask_outputs: list[Path] = []
        person_mask_outputs: list[Path] = []
        background_mask_outputs: list[Path] = []
        overlay_outputs: list[Path] = []
        repaired_outputs: list[Path] = []

        previous_prepared: Path | None = None
        for index, source in progress_iter(
            indexed_frames,
            total=len(indexed_frames),
            desc="artifact repair frames",
            unit="frame",
        ):
            prepared = _prepare_source(source, source_dir / f"source_{index:03d}.png", args.width, args.height)
            analysis = _analyze_frame(prepared, args)
            external_mask_path = _external_mask_path(args.external_mask_dir, index)
            if external_mask_path:
                _apply_external_repair_mask(analysis, external_mask_path, args)
            quality_source = prepare_analysis_frame(
                prepared,
                run_dir / "analysis_frames" / f"analysis_{index:03d}.png",
                args.analysis_max_size,
            )
            previous_quality_source = (
                prepare_analysis_frame(
                    previous_prepared,
                    run_dir / "analysis_frames" / f"analysis_prev_{index:03d}.png",
                    args.analysis_max_size,
                )
                if previous_prepared
                else None
            )
            quality = analyze_frame_quality(quality_source, index=index, previous_path=previous_quality_source)
            previous_prepared = prepared
            for issue_code in quality.issue_codes:
                if issue_code not in analysis["issue_codes"]:
                    analysis["issue_codes"].append(issue_code)
            if quality.hard_failure:
                analysis["gate"] = "retake_required"
            mask_path = masks_dir / f"mask_{index:03d}.png"
            person_mask_path = person_masks_dir / f"person_mask_{index:03d}.png"
            background_mask_path = background_masks_dir / f"background_cleanup_mask_{index:03d}.png"
            overlay_path = overlays_dir / f"overlay_{index:03d}.png"
            analysis["repair_mask"].save(mask_path)
            analysis["person_mask"].save(person_mask_path)
            analysis["background_cleanup_mask"].save(background_mask_path)
            _make_overlay(prepared, analysis["repair_mask"], analysis, overlay_path)

            frame_report = {
                key: value
                for key, value in analysis.items()
                if key
                not in {
                    "repair_mask",
                    "foreground_mask",
                    "strong_mask",
                    "protected_mask",
                    "person_mask",
                    "background_cleanup_mask",
                }
            }
            frame_report.update(
                {
                    "index": index,
                    "source": str(source),
                    "prepared_source": str(prepared),
                    "repair_mask": str(mask_path),
                    "person_mask": str(person_mask_path),
                    "background_cleanup_mask": str(background_mask_path),
                    "overlay": str(overlay_path),
                    "quality_metrics": quality.to_dict(),
                }
            )
            plan_action = plan_actions.get(index)
            if plan_action:
                frame_report["correction_plan_action"] = plan_action
                if plan_action == "retake_required":
                    frame_report["gate"] = "retake_required"
                    if "correction_plan_retake_required" not in frame_report["issue_codes"]:
                        frame_report["issue_codes"].append("correction_plan_retake_required")

            repaired_path = repaired_dir / f"frame_{index:03d}.png"
            if args.mask_only or frame_report["mask_coverage"] < args.min_mask_coverage:
                Image.open(prepared).save(repaired_path)
                frame_report["repair_mode"] = "copied_no_inpaint"
                frame_report["source_delta"] = 0.0
            elif not _plan_allows_inpaint(plan_action, args.allowed_plan_action):
                Image.open(prepared).save(repaired_path)
                frame_report["repair_mode"] = "blocked_by_correction_plan"
                frame_report["source_delta"] = 0.0
            elif frame_report["gate"] == "retake_required":
                Image.open(prepared).save(repaired_path)
                frame_report["repair_mode"] = "blocked_retake_required"
                frame_report["source_delta"] = 0.0
            elif frame_report["mask_coverage"] > args.max_mask_coverage:
                Image.open(prepared).save(repaired_path)
                frame_report["repair_mode"] = "blocked_mask_too_large"
                frame_report["source_delta"] = 0.0
                frame_report["issue_codes"].append("repair_mask_too_large")
                frame_report["gate"] = "retake_required"
            else:
                image_name = _upload_image(args.comfy_url.rstrip("/"), prepared, "source")
                mask_name = _upload_image(args.comfy_url.rstrip("/"), mask_path, "mask")
                workflow = _workflow(args, image_name, mask_name, index)
                workflow_path = workflow_dir / f"frame_{index:03d}.json"
                workflow_path.write_text(
                    json.dumps(workflow, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                prompt_id = _queue_prompt(args.comfy_url.rstrip("/"), workflow, args=args)
                report["prompt_ids"].append(prompt_id)
                history = _wait_for_history(args.comfy_url.rstrip("/"), prompt_id, args.timeout_seconds)
                image_bytes = _download_first_saveimage(args.comfy_url.rstrip("/"), history, "11")
                Image.open(BytesIO(image_bytes)).convert("RGBA").save(repaired_path)
                frame_report["repair_mode"] = "comfy_masked_inpaint"
                frame_report["workflow"] = str(workflow_path)
                frame_report["source_delta"] = _mean_delta(prepared, repaired_path)

            source_outputs.append(prepared)
            mask_outputs.append(mask_path)
            person_mask_outputs.append(person_mask_path)
            background_mask_outputs.append(background_mask_path)
            overlay_outputs.append(overlay_path)
            repaired_outputs.append(repaired_path)
            report["frame_reports"].append(frame_report)

        source_contact = make_contact_sheet(source_outputs, run_dir / "source_contact_sheet.png", columns=min(6, len(source_outputs)))
        mask_contact = make_contact_sheet(mask_outputs, run_dir / "mask_contact_sheet.png", columns=min(6, len(mask_outputs)))
        person_mask_contact = make_contact_sheet(
            person_mask_outputs,
            run_dir / "person_mask_contact_sheet.png",
            columns=min(6, len(person_mask_outputs)),
        )
        background_mask_contact = make_contact_sheet(
            background_mask_outputs,
            run_dir / "background_cleanup_mask_contact_sheet.png",
            columns=min(6, len(background_mask_outputs)),
        )
        overlay_contact = make_contact_sheet(overlay_outputs, run_dir / "overlay_contact_sheet.png", columns=min(6, len(overlay_outputs)))
        repaired_contact = make_contact_sheet(repaired_outputs, run_dir / "contact_sheet.png", columns=min(6, len(repaired_outputs)))
        comparison = _make_comparison_sheet(source_outputs, mask_outputs, repaired_outputs, run_dir / "comparison_sheet.png")
        preview = make_preview_gif(repaired_outputs, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
        report.update(
            {
                "status": "completed",
                "frame_count": len(repaired_outputs),
                "frames_dir": str(repaired_dir),
                "preview_gif": str(preview),
                "source_contact_sheet": str(source_contact),
                "mask_contact_sheet": str(mask_contact),
                "person_mask_contact_sheet": str(person_mask_contact),
                "background_cleanup_mask_contact_sheet": str(background_mask_contact),
                "overlay_contact_sheet": str(overlay_contact),
                "contact_sheet": str(repaired_contact),
                "comparison_sheet": str(comparison),
                "source_motion_metrics": _motion_metrics(source_outputs),
                "repaired_motion_metrics": _motion_metrics(repaired_outputs),
                "summary": _summarize_reports(report["frame_reports"]),
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
                key: report[key]
                for key in (
                    "status",
                    "frame_count",
                    "preview_gif",
                    "comparison_sheet",
                    "source_motion_metrics",
                    "repaired_motion_metrics",
                    "summary",
                )
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _workflow(args: argparse.Namespace, image_name: str, mask_name: str, index: int) -> dict[str, Any]:
    seed = args.seed + index * args.seed_step
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "3": {"class_type": "LoadImageMask", "inputs": {"image": mask_name, "channel": "red"}},
        "4": {"class_type": "VAEEncodeForInpaint", "inputs": {"pixels": ["2", 0], "vae": ["1", 2], "mask": ["3", 0], "grow_mask_by": 4}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": args.positive}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": args.negative}},
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": args.steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": args.denoise,
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {
            "class_type": "ImageCompositeMasked",
            "inputs": {
                "destination": ["2", 0],
                "source": ["8", 0],
                "x": 0,
                "y": 0,
                "resize_source": False,
                "mask": ["3", 0],
            },
        },
        "11": {
            "class_type": "SaveImage",
            "inputs": {"images": ["9", 0], "filename_prefix": f"natural_sprite_lab_artifact_repair_{index:03d}"},
        },
    }


def _prepare_source(source: Path, output: Path, width: int, height: int) -> Path:
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


def _analyze_frame(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    source_image = Image.open(path).convert("RGB")
    image = _resize_for_analysis(source_image, args.analysis_max_size)
    scale_x = source_image.width / image.width
    scale_y = source_image.height / image.height
    weak_mask = _foreground_by_background_distance(image, args.weak_threshold)
    strong_mask = _foreground_by_background_distance(image, args.strong_threshold)
    components = _connected_components(strong_mask, min_pixels=48)
    main_component = max(components, key=lambda item: item["pixels"], default=None)
    main_mask = _component_mask(strong_mask.size, main_component["points"]) if main_component else Image.new("L", image.size, 0)
    protected = _grow_mask(main_mask, args.protect_grow)

    small_component_mask = Image.new("L", image.size, 0)
    for component in components:
        if main_component and component is main_component:
            continue
        if component["pixels"] < max(2600, (main_component or {"pixels": 0})["pixels"] * 0.13):
            _draw_points(small_component_mask, component["points"], 255)

    repair_mask = ImageChops.subtract(weak_mask, protected)
    repair_mask = ImageChops.lighter(repair_mask, small_component_mask)
    repair_mask = _remove_low_mask_values(repair_mask, 128)
    repair_mask = _grow_mask(repair_mask, args.mask_grow)
    repair_mask = ImageChops.subtract(repair_mask, protected)
    repair_mask = repair_mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    background_cleanup_mask = ImageChops.subtract(weak_mask, protected)
    background_cleanup_mask = _remove_low_mask_values(background_cleanup_mask, 128)

    bbox = strong_mask.getbbox()
    lower_blob_count = _count_lower_body_blobs(strong_mask, bbox)
    weapon_report = _weapon_report(image, strong_mask, args.weapon)
    mask_coverage = _mask_coverage(repair_mask)
    issue_codes: list[str] = []
    if mask_coverage >= args.min_mask_coverage:
        issue_codes.append("masked_ghost_or_small_artifact")
    if mask_coverage > args.max_mask_coverage:
        issue_codes.append("repair_mask_too_large")
    if len(components) >= 5 and mask_coverage >= args.min_mask_coverage:
        issue_codes.append("strong_duplicate_silhouette_risk")
    if lower_blob_count > 2:
        issue_codes.append("double_foot_or_duplicate_leg_risk")
    issue_codes.extend(weapon_report["issue_codes"])
    lower_body_pale_afterimage_coverage = _lower_body_pale_afterimage_coverage(image, bbox)
    review_labels = _visual_review_labels(
        image,
        protected,
        repair_mask,
        bbox,
        args.min_mask_coverage,
        lower_body_pale_afterimage_coverage,
    )

    hard_issue_codes = {
        "double_foot_or_duplicate_leg_risk",
        "strong_duplicate_silhouette_risk",
        "weapon_missing",
        "weapon_fragmented",
        "weapon_not_elongated",
        "weapon_detached",
        "repair_mask_too_large",
    }
    gate = "repair_candidate"
    if any(code in hard_issue_codes for code in issue_codes):
        gate = "retake_required"
    elif mask_coverage < args.min_mask_coverage:
        gate = "no_repair_needed"

    output_size = source_image.size
    return {
        "foreground_mask": _restore_mask_size(weak_mask, output_size),
        "strong_mask": _restore_mask_size(strong_mask, output_size),
        "protected_mask": _restore_mask_size(protected, output_size),
        "person_mask": _restore_mask_size(protected, output_size),
        "background_cleanup_mask": _restore_mask_size(background_cleanup_mask, output_size),
        "repair_mask": _restore_mask_size(repair_mask, output_size),
        "foreground_bbox": _scale_bbox(bbox, scale_x, scale_y) if bbox else None,
        "strong_component_count": len(components),
        "main_component_pixels": round(main_component["pixels"] * scale_x * scale_y) if main_component else 0,
        "lower_body_blob_count": lower_blob_count,
        "mask_coverage": round(mask_coverage, 5),
        "mask_pixels": round(_mask_pixels(repair_mask) * scale_x * scale_y),
        "lower_body_pale_afterimage_coverage": round(lower_body_pale_afterimage_coverage, 5),
        "weapon": weapon_report,
        "issue_codes": issue_codes,
        "review_labels": review_labels,
        "gate": gate,
    }


def _external_mask_path(mask_dir: Path | None, index: int) -> Path | None:
    if mask_dir is None:
        return None
    path = mask_dir / f"frame_{index:03d}.png"
    return path if path.exists() else None


def _apply_external_repair_mask(analysis: dict[str, Any], mask_path: Path, args: argparse.Namespace) -> None:
    external = Image.open(mask_path).convert("L")
    external = _restore_mask_size(external, analysis["repair_mask"].size)
    external = _remove_low_mask_values(external, 128)
    external = _grow_mask(external, args.mask_grow)
    external = ImageChops.subtract(external, analysis["protected_mask"])
    external = external.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    coverage = _mask_coverage(external)
    analysis["repair_mask"] = external
    analysis["mask_coverage"] = round(coverage, 5)
    analysis["mask_pixels"] = _mask_pixels(external)
    analysis["external_mask"] = str(mask_path)
    analysis["issue_codes"] = [
        code
        for code in analysis["issue_codes"]
        if code not in {"masked_ghost_or_small_artifact", "repair_mask_too_large"}
    ]
    if coverage >= args.min_mask_coverage:
        analysis["issue_codes"].append("masked_ghost_or_small_artifact")
        if analysis["gate"] == "no_repair_needed":
            analysis["gate"] = "repair_candidate"
    else:
        hard_codes = {"double_foot_or_duplicate_leg_risk", "strong_duplicate_silhouette_risk"}
        if not any(code in analysis["issue_codes"] for code in hard_codes):
            analysis["gate"] = "no_repair_needed"
    if coverage > args.max_mask_coverage:
        analysis["issue_codes"].append("repair_mask_too_large")
        analysis["gate"] = "retake_required"


def _resize_for_analysis(image: Image.Image, max_size: int) -> Image.Image:
    if max_size <= 0:
        return image.copy()
    longest = max(image.size)
    if longest <= max_size:
        return image.copy()
    scale = max_size / longest
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.BICUBIC,
    )


def _restore_mask_size(mask: Image.Image, size: tuple[int, int]) -> Image.Image:
    if mask.size == size:
        return mask
    return mask.resize(size, Image.Resampling.NEAREST)


def _scale_bbox(
    bbox: tuple[int, int, int, int],
    scale_x: float,
    scale_y: float,
) -> list[int]:
    left, top, right, bottom = bbox
    return [
        round(left * scale_x),
        round(top * scale_y),
        round(right * scale_x),
        round(bottom * scale_y),
    ]


def _foreground_by_background_distance(image: Image.Image, threshold: int) -> Image.Image:
    bg = _estimate_background(image)
    out = Image.new("L", image.size, 0)
    pixels = image.load()
    mask = out.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            distance = abs(red - bg[0]) + abs(green - bg[1]) + abs(blue - bg[2])
            if distance >= threshold:
                mask[x, y] = 255
    return out


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


def _connected_components(mask: Image.Image, min_pixels: int) -> list[dict[str, Any]]:
    width, height = mask.size
    pixels = mask.load()
    visited: set[tuple[int, int]] = set()
    components: list[dict[str, Any]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in visited:
                continue
            points: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited.add((x, y))
            while queue:
                px, py = queue.popleft()
                points.append((px, py))
                for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    if pixels[nx, ny] == 0 or (nx, ny) in visited:
                        continue
                    visited.add((nx, ny))
                    queue.append((nx, ny))
            if len(points) >= min_pixels:
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                components.append(
                    {
                        "points": points,
                        "pixels": len(points),
                        "bbox": (min(xs), min(ys), max(xs) + 1, max(ys) + 1),
                    }
                )
    return sorted(components, key=lambda item: item["pixels"], reverse=True)


def _component_mask(size: tuple[int, int], points: list[tuple[int, int]]) -> Image.Image:
    mask = Image.new("L", size, 0)
    _draw_points(mask, points, 255)
    return mask


def _draw_points(mask: Image.Image, points: list[tuple[int, int]], value: int) -> None:
    pixels = mask.load()
    for x, y in points:
        pixels[x, y] = value


def _count_lower_body_blobs(mask: Image.Image, bbox: tuple[int, int, int, int] | None) -> int:
    if bbox is None:
        return 0
    left, top, right, bottom = bbox
    lower_top = round(top + (bottom - top) * 0.58)
    foot_zone_top = round(top + (bottom - top) * 0.74)
    lower = Image.new("L", mask.size, 0)
    lower.paste(mask.crop((left, lower_top, right, bottom)), (left, lower_top))
    components = _connected_components(lower, min_pixels=80)
    foot_like = []
    for component in components:
        x0, y0, x1, y1 = component["bbox"]
        if y1 < lower_top:
            continue
        if y1 < foot_zone_top:
            continue
        if (x1 - x0) >= 8 and (y1 - y0) >= 8:
            foot_like.append(component)
    return len(foot_like)


def _visual_review_labels(
    image: Image.Image,
    protected_mask: Image.Image,
    repair_mask: Image.Image,
    bbox: tuple[int, int, int, int] | None,
    min_mask_coverage: float,
    lower_body_pale_afterimage_coverage: float,
) -> list[str]:
    labels: list[str] = []
    if _guide_line_leakage_coverage(image, protected_mask) >= 0.00003:
        labels.append("visible_guide_line_leakage_review")
    if bbox is not None:
        if _lower_zone_coverage(repair_mask, bbox) >= min_mask_coverage:
            labels.append("foot_shadow_or_contact_artifact_review")
        if _skin_afterimage_coverage(image, protected_mask, bbox) >= 0.00008:
            labels.append("skin_colored_afterimage_near_legs_review")
        if lower_body_pale_afterimage_coverage >= 0.055:
            labels.append("lower_body_pale_afterimage_review")
        left, top, right, bottom = bbox
        if (bottom - top) / max(1, image.height) < 0.34:
            labels.append("face_detail_readability_at_game_scale_review")
    return labels


def _guide_line_leakage_coverage(image: Image.Image, protected_mask: Image.Image) -> float:
    pixels = image.load()
    protected = _grow_mask(protected_mask, 4).load()
    count = 0
    for y in range(image.height):
        for x in range(image.width):
            if protected[x, y] > 0:
                continue
            red, green, blue = pixels[x, y]
            saturated_red = red > 175 and green < 130 and blue < 130
            saturated_green = green > 155 and red < 140 and blue < 150
            saturated_blue = blue > 165 and red < 150 and green < 170
            if saturated_red or saturated_green or saturated_blue:
                count += 1
    return count / max(1, image.width * image.height)


def _lower_zone_coverage(mask: Image.Image, bbox: tuple[int, int, int, int]) -> float:
    left, top, right, bottom = bbox
    lower_top = round(top + (bottom - top) * 0.70)
    if lower_top >= bottom:
        return 0.0
    lower = mask.crop((left, lower_top, right, bottom))
    return _mask_coverage(lower)


def _skin_afterimage_coverage(
    image: Image.Image,
    protected_mask: Image.Image,
    bbox: tuple[int, int, int, int],
) -> float:
    left, top, right, bottom = bbox
    lower_top = round(top + (bottom - top) * 0.55)
    protected = _grow_mask(protected_mask, 3).load()
    pixels = image.load()
    count = 0
    total = 0
    for y in range(lower_top, bottom):
        for x in range(left, right):
            if protected[x, y] > 0:
                continue
            total += 1
            red, green, blue = pixels[x, y]
            skin_like = red > 170 and green > 115 and blue > 90 and red > green + 8 and green > blue - 5
            if skin_like:
                count += 1
    return count / max(1, total)


def _lower_body_pale_afterimage_coverage(
    image: Image.Image,
    bbox: tuple[int, int, int, int] | None,
) -> float:
    if bbox is None:
        return 0.0
    left, top, right, bottom = bbox
    width = right - left
    left = max(0, left - round(width * 0.12))
    right = min(image.width, right + round(width * 0.12))
    lower_top = round(top + (bottom - top) * 0.56)
    if lower_top >= bottom:
        return 0.0
    pixels = image.load()
    count = 0
    total = 0
    for y in range(lower_top, bottom):
        for x in range(left, right):
            total += 1
            red, green, blue = pixels[x, y]
            high = max(red, green, blue)
            low = min(red, green, blue)
            saturation = high - low
            brightness = (red + green + blue) / 3
            white_distance = abs(red - 255) + abs(green - 255) + abs(blue - 255)
            pale_gray = 38 < white_distance < 310 and 95 < brightness < 238 and saturation < 48
            blue_gray = (
                white_distance > 40
                and 85 < brightness < 235
                and blue >= red - 5
                and green >= red - 15
                and saturation < 78
            )
            skin_like = red > 165 and green > 105 and blue > 80 and red > green + 8 and green > blue - 10
            if (pale_gray or blue_gray) and not skin_like:
                count += 1
    return count / max(1, total)


def _weapon_report(image: Image.Image, strong_mask: Image.Image, weapon: str) -> dict[str, Any]:
    if weapon == "none":
        return {"issue_codes": [], "component_count": 0, "largest_bbox": None, "largest_aspect": 0.0}
    mask = _weapon_color_mask(image, weapon)
    components = _connected_components(mask, min_pixels=60)
    if not components:
        return {"issue_codes": ["weapon_missing"], "component_count": 0, "largest_bbox": None, "largest_aspect": 0.0}
    largest = components[0]
    x0, y0, x1, y1 = largest["bbox"]
    aspect = max(x1 - x0, y1 - y0) / max(1, min(x1 - x0, y1 - y0))
    issue_codes = []
    if len(components) > 2:
        issue_codes.append("weapon_fragmented")
    if aspect < 2.2 and weapon in {"sword", "bow"}:
        issue_codes.append("weapon_not_elongated")
    strong_overlap = _overlap_pixels(mask, strong_mask)
    if strong_overlap < max(20, largest["pixels"] * 0.015):
        issue_codes.append("weapon_detached")
    return {
        "issue_codes": issue_codes,
        "component_count": len(components),
        "largest_bbox": list(largest["bbox"]),
        "largest_pixels": largest["pixels"],
        "largest_aspect": round(aspect, 3),
        "strong_overlap_pixels": strong_overlap,
    }


def _weapon_color_mask(image: Image.Image, weapon: str) -> Image.Image:
    out = Image.new("L", image.size, 0)
    pixels = image.load()
    mask = out.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            if weapon == "sword":
                keep = blue > 105 and blue > red + 18 and blue > green - 8
            elif weapon == "bow":
                keep = red + green + blue < 430 and abs(red - green) < 75 and blue < 180
            else:
                keep = red + green < 330 and blue < 170
            if keep:
                mask[x, y] = 255
    return out.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))


def _make_overlay(source: Path, mask: Image.Image, analysis: dict[str, Any], output: Path) -> Path:
    image = Image.open(source).convert("RGBA")
    red = Image.new("RGBA", image.size, (255, 40, 30, 120))
    image.alpha_composite(Image.composite(red, Image.new("RGBA", image.size, (0, 0, 0, 0)), mask))
    draw = ImageDraw.Draw(image)
    text = f"{analysis['gate']} mask={analysis['mask_coverage']:.3f} issues={','.join(analysis['issue_codes']) or 'none'}"
    draw.rectangle((8, 8, min(image.width - 8, 8 + len(text) * 7), 30), fill=(255, 255, 255, 220))
    draw.text((12, 12), text, fill=(20, 20, 20))
    image.save(output)
    return output


def _make_comparison_sheet(source_paths: list[Path], mask_paths: list[Path], repaired_paths: list[Path], output_path: Path) -> Path:
    thumbs: list[tuple[str, Image.Image]] = []
    for index, (source, mask, repaired) in enumerate(zip(source_paths, mask_paths, repaired_paths)):
        thumbs.append((f"{index:02d} src", Image.open(source).convert("RGB")))
        thumbs.append((f"{index:02d} mask", Image.open(mask).convert("RGB")))
        thumbs.append((f"{index:02d} repair", Image.open(repaired).convert("RGB")))
    thumb_w = 220
    thumb_h = 220
    columns = 3
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + 20)), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(thumbs):
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = (index % columns) * thumb_w
        y = (index // columns) * (thumb_h + 20)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x + 4, y + thumb_h + 4), label, fill=(20, 20, 20))
    sheet.save(output_path)
    return output_path


def _grow_mask(mask: Image.Image, pixels: int) -> Image.Image:
    if pixels <= 0:
        return mask.copy()
    size = pixels * 2 + 1
    return mask.filter(ImageFilter.MaxFilter(size))


def _remove_low_mask_values(mask: Image.Image, threshold: int) -> Image.Image:
    return mask.point(lambda value: 255 if value >= threshold else 0)


def _mask_coverage(mask: Image.Image) -> float:
    return _mask_pixels(mask) / (mask.width * mask.height)


def _mask_pixels(mask: Image.Image) -> int:
    return round(ImageStat.Stat(mask).sum[0] / 255)


def _overlap_pixels(left: Image.Image, right: Image.Image) -> int:
    return _mask_pixels(ImageChops.multiply(left, right))


def _summarize_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    issue_counts: dict[str, int] = {}
    review_label_counts: dict[str, int] = {}
    gates: dict[str, int] = {}
    for report in reports:
        gates[report["gate"]] = gates.get(report["gate"], 0) + 1
        for code in report["issue_codes"]:
            issue_counts[code] = issue_counts.get(code, 0) + 1
        for label in report.get("review_labels", []):
            review_label_counts[label] = review_label_counts.get(label, 0) + 1
    mean_mask = sum(report["mask_coverage"] for report in reports) / len(reports)
    repaired = sum(1 for report in reports if report["repair_mode"] == "comfy_masked_inpaint")
    return {
        "gate_counts": gates,
        "issue_counts": issue_counts,
        "review_label_counts": review_label_counts,
        "mean_mask_coverage": round(mean_mask, 5),
        "inpainted_frames": repaired,
        "candidate_status": _candidate_status(gates, issue_counts, review_label_counts),
        "recommendation": _recommendation(gates, issue_counts, repaired),
    }


def _plan_action_by_index(path: Path | None) -> dict[int, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    actions: dict[int, str] = {}
    for item in payload.get("frame_plans", []):
        if "index" not in item:
            continue
        actions[int(item["index"])] = str(item.get("action", ""))
    return actions


def _select_indexed_frames(
    frame_paths: list[Path],
    plan_actions: dict[int, str],
    only_plan_action: str | None,
) -> list[tuple[int, Path]]:
    indexed = list(enumerate(frame_paths))
    if not only_plan_action:
        return indexed
    return [(index, path) for index, path in indexed if plan_actions.get(index) == only_plan_action]


def _plan_allows_inpaint(plan_action: str | None, allowed_action: str) -> bool:
    return not plan_action or plan_action == allowed_action


def _candidate_status(
    gates: dict[str, int],
    issue_counts: dict[str, int],
    review_label_counts: dict[str, int],
) -> str:
    if gates.get("retake_required"):
        return "rejected"
    structural_issue_codes = {
        "strong_duplicate_silhouette_risk",
        "double_foot_or_duplicate_leg_risk",
        "repair_mask_too_large",
        "weapon_missing",
        "weapon_fragmented",
        "weapon_not_elongated",
        "weapon_detached",
    }
    if any(issue_counts.get(code) for code in structural_issue_codes):
        return "rejected"
    if review_label_counts:
        return "selected_proof_only"
    if gates.get("repair_candidate"):
        return "diagnostic"
    return "adopted_full_source"


def _recommendation(gates: dict[str, int], issue_counts: dict[str, int], repaired: int) -> str:
    if gates.get("retake_required"):
        return "retake_or_retrim_span_before_refine"
    if issue_counts.get("weapon_fragmented") or issue_counts.get("weapon_missing"):
        return "retake_with_weapon_control_mask"
    if issue_counts.get("double_foot_or_duplicate_leg_risk") or issue_counts.get("repair_mask_too_large"):
        return "retake_or_retrim_span_before_refine"
    if repaired > 0:
        return "review_comparison_sheet_for_adoption"
    return "no_repair_needed_or_mask_threshold_too_strict"


def _upload_image(server_url: str, path: Path, role: str) -> str:
    data = path.read_bytes()
    filename = f"artifact_repair_{role}_{uuid.uuid4().hex}.png"
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


def _motion_metrics(frame_paths: list[Path]) -> dict[str, Any]:
    if len(frame_paths) < 2:
        return {"mean_frame_delta": 0.0, "max_frame_delta": 0.0, "min_frame_delta": 0.0}
    deltas = [_mean_delta(left, right) for left, right in zip(frame_paths, frame_paths[1:])]
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


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "artifact_repair"


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
