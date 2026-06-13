from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract local BiRefNet foreground masks through ComfyUI and composite frames on a clean background."
    )
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--model", default="birefnet.safetensors")
    parser.add_argument("--background", default="white", choices=("white", "transparent"))
    parser.add_argument("--mask-blur", default=1.0, type=float)
    parser.add_argument("--mask-grow", default=1, type=int)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    args = parser.parse_args()

    frame_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_birefnet")
    run_dir = build_timestamped_run_dir(args.output_root, "birefnet_foreground", label)
    write_run_profile(run_dir, category="birefnet_foreground", label=label, args=args)
    frames_out = run_dir / "frames"
    masks_out = run_dir / "foreground_masks"
    rgba_out = run_dir / "rgba_frames"
    workflows_out = run_dir / "workflow"
    for path in (frames_out, masks_out, rgba_out, workflows_out):
        path.mkdir(parents=True, exist_ok=True)

    uploaded = [_upload_image(args.comfy_url.rstrip("/"), path) for path in frame_paths]
    workflow, save_node_ids = _workflow(args.model, uploaded)
    workflow_path = workflows_out / "birefnet_masks.json"
    workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    prompt_id = _queue_prompt(args.comfy_url.rstrip("/"), workflow)
    history = _wait_for_history(args.comfy_url.rstrip("/"), prompt_id, args.timeout_seconds)

    output_paths: list[Path] = []
    mask_paths: list[Path] = []
    rgba_paths: list[Path] = []
    frame_reports: list[dict[str, Any]] = []
    previous_mask: Image.Image | None = None
    for index, (frame_path, save_node_id) in enumerate(zip(frame_paths, save_node_ids)):
        mask_bytes = _download_first_saveimage(args.comfy_url.rstrip("/"), history, save_node_id)
        mask = Image.open(BytesIO(mask_bytes)).convert("L")
        mask = _prepare_mask(mask, grow=args.mask_grow, blur=args.mask_blur)
        image = Image.open(frame_path).convert("RGBA").resize(mask.size, Image.Resampling.BICUBIC)

        rgba_path = rgba_out / f"frame_{index:03d}.png"
        mask_path = masks_out / f"foreground_mask_{index:03d}.png"
        output_path = frames_out / f"frame_{index:03d}.png"
        rgba = _join_alpha(image, mask)
        rgba.save(rgba_path)
        mask.save(mask_path)
        composite = _composite(image, mask, args.background)
        composite.save(output_path)

        report = _frame_report(index, frame_path, output_path, mask_path, rgba_path, mask, previous_mask)
        frame_reports.append(report)
        previous_mask = mask
        output_paths.append(output_path)
        mask_paths.append(mask_path)
        rgba_paths.append(rgba_path)

    contact_sheet = make_contact_sheet(output_paths, run_dir / "contact_sheet.png", columns=min(6, len(output_paths)))
    mask_contact_sheet = make_contact_sheet(mask_paths, run_dir / "foreground_mask_contact_sheet.png", columns=min(6, len(mask_paths)))
    preview = make_preview_gif(output_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
    report = {
        "status": "completed",
        "source_frames_dir": str(args.frames_dir),
        "frames_dir": str(frames_out),
        "rgba_frames_dir": str(rgba_out),
        "foreground_masks_dir": str(masks_out),
        "contact_sheet": str(contact_sheet),
        "foreground_mask_contact_sheet": str(mask_contact_sheet),
        "preview_gif": str(preview),
        "workflow": str(workflow_path),
        "prompt_id": prompt_id,
        "settings": {
            "model": args.model,
            "background": args.background,
            "mask_blur": args.mask_blur,
            "mask_grow": args.mask_grow,
            "fps": args.fps,
        },
        "summary": _summarize(frame_reports),
        "frame_reports": frame_reports,
    }
    report_path = run_dir / "birefnet_foreground_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    print(json.dumps({"summary": report["summary"], "preview_gif": str(preview)}, indent=2, ensure_ascii=False))


def _workflow(model: str, image_names: list[str]) -> tuple[dict[str, Any], list[str]]:
    workflow: dict[str, Any] = {
        "1": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": model}},
    }
    save_node_ids: list[str] = []
    for index, image_name in enumerate(image_names):
        base = 10 + index * 4
        load_id = str(base)
        remove_id = str(base + 1)
        mask_image_id = str(base + 2)
        save_id = str(base + 3)
        workflow[load_id] = {"class_type": "LoadImage", "inputs": {"image": image_name}}
        workflow[remove_id] = {
            "class_type": "RemoveBackground",
            "inputs": {"image": [load_id, 0], "bg_removal_model": ["1", 0]},
        }
        workflow[mask_image_id] = {"class_type": "MaskToImage", "inputs": {"mask": [remove_id, 0]}}
        workflow[save_id] = {
            "class_type": "SaveImage",
            "inputs": {"images": [mask_image_id, 0], "filename_prefix": f"natural_sprite_lab_birefnet_mask_{index:03d}"},
        }
        save_node_ids.append(save_id)
    return workflow, save_node_ids


def _prepare_mask(mask: Image.Image, *, grow: int, blur: float) -> Image.Image:
    result = mask.convert("L")
    if grow > 0:
        result = result.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    if blur > 0:
        result = result.filter(ImageFilter.GaussianBlur(blur))
    return result


def _join_alpha(image: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def _composite(image: Image.Image, mask: Image.Image, background: str) -> Image.Image:
    rgba = _join_alpha(image, mask)
    if background == "transparent":
        return rgba
    canvas = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    canvas.alpha_composite(rgba)
    return canvas.convert("RGB")


def _frame_report(
    index: int,
    source: Path,
    output: Path,
    mask_path: Path,
    rgba_path: Path,
    mask: Image.Image,
    previous_mask: Image.Image | None,
) -> dict[str, Any]:
    coverage = _mask_coverage(mask)
    bbox = mask.getbbox()
    mask_delta = 0.0
    if previous_mask is not None:
        mask_delta = float(ImageStat.Stat(ImageChops.difference(previous_mask, mask)).mean[0]) / 255.0
    structure = _mask_structure(mask)
    return {
        "index": index,
        "source": str(source),
        "output": str(output),
        "foreground_mask": str(mask_path),
        "rgba_frame": str(rgba_path),
        "foreground_coverage": round(coverage, 5),
        "foreground_bbox": list(bbox) if bbox else None,
        "foreground_bbox_fill": structure["foreground_bbox_fill"],
        "lower_body_max_width_ratio": structure["lower_body_max_width_ratio"],
        "lower_body_mean_width_ratio": structure["lower_body_mean_width_ratio"],
        "mask_delta_from_previous": round(mask_delta, 5),
        "gate": _mask_gate(coverage, mask_delta, index, structure),
    }


def _mask_gate(coverage: float, mask_delta: float, index: int, structure: dict[str, float]) -> str:
    if coverage < 0.025:
        return "retake_foreground_too_small"
    if coverage > 0.72:
        return "retake_foreground_too_large"
    if index > 0 and mask_delta > 0.34:
        return "review_mask_temporal_jump"
    if structure["foreground_bbox_fill"] and structure["foreground_bbox_fill"] < 0.39:
        return "review_sparse_foreground_bbox"
    if structure["lower_body_max_width_ratio"] > 0.32:
        return "review_lower_body_silhouette_wide"
    return "mask_ok"


def _mask_structure(mask: Image.Image) -> dict[str, float]:
    binary = mask.convert("L").point(lambda value: 255 if value >= 128 else 0)
    bbox = binary.getbbox()
    if bbox is None:
        return {
            "foreground_bbox_fill": 0.0,
            "lower_body_max_width_ratio": 0.0,
            "lower_body_mean_width_ratio": 0.0,
        }
    left, top, right, bottom = bbox
    bbox_area = max(1, (right - left) * (bottom - top))
    foreground_pixels = float(ImageStat.Stat(binary.crop(bbox)).sum[0]) / 255.0
    fill = foreground_pixels / bbox_area
    lower_top = round(top + (bottom - top) * 0.56)
    pixels = binary.load()
    widths: list[int] = []
    for y in range(lower_top, bottom):
        xs = [x for x in range(left, right) if pixels[x, y] >= 128]
        if xs:
            widths.append(max(xs) - min(xs) + 1)
    max_width = max(widths) if widths else 0
    mean_width = sum(widths) / len(widths) if widths else 0.0
    image_width = max(1, binary.width)
    return {
        "foreground_bbox_fill": round(fill, 5),
        "lower_body_max_width_ratio": round(max_width / image_width, 5),
        "lower_body_mean_width_ratio": round(mean_width / image_width, 5),
    }


def _summarize(frame_reports: list[dict[str, Any]]) -> dict[str, Any]:
    gates: dict[str, int] = {}
    for report in frame_reports:
        gate = str(report["gate"])
        gates[gate] = gates.get(gate, 0) + 1
    mean_coverage = sum(float(report["foreground_coverage"]) for report in frame_reports) / len(frame_reports)
    mean_mask_delta = sum(float(report["mask_delta_from_previous"]) for report in frame_reports[1:]) / max(1, len(frame_reports) - 1)
    return {
        "frames": len(frame_reports),
        "mean_foreground_coverage": round(mean_coverage, 5),
        "mean_mask_delta": round(mean_mask_delta, 5),
        "gates": gates,
    }


def _mask_coverage(mask: Image.Image) -> float:
    stat = ImageStat.Stat(mask)
    return float(stat.mean[0]) / 255.0


def _upload_image(server_url: str, path: Path) -> str:
    body, content_type = _multipart_image("image", f"birefnet_{uuid.uuid4().hex}.png", path.read_bytes())
    request = urllib.request.Request(
        f"{server_url}/upload/image",
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    payload = json.loads(_open(request, timeout=30).decode("utf-8"))
    return str(payload.get("name"))


def _queue_prompt(server_url: str, workflow: dict[str, Any]) -> str:
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
    deadline = time.monotonic() + timeout_seconds
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
        time.sleep(1.0)
    raise TimeoutError(f"Timed out waiting for ComfyUI prompt: {prompt_id}")


def _download_first_saveimage(server_url: str, history: dict[str, Any], node_id: str) -> bytes:
    images = history.get("outputs", {}).get(node_id, {}).get("images", [])
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


def _multipart_image(field: str, filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = f"----natural-sprite-lab-{uuid.uuid4().hex}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode("utf-8"),
            b"Content-Type: image/png\r\n\r\n",
            data,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def _open(request: urllib.request.Request, *, timeout: float) -> bytes:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "birefnet_foreground"


if __name__ == "__main__":
    main()
