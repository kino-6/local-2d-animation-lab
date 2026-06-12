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

from PIL import Image, ImageDraw

from natural_sprite_lab.comfy_queue import add_queue_wait_arguments
from natural_sprite_lab.comfy_queue import wait_for_queue_capacity_from_args
from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.progress import ProgressTimer
from natural_sprite_lab.progress import progress_iter


POSITIVE_PROMPT = (
    "masterpiece, best quality, polished anime game sprite, full body young woman character, "
    "clean crisp line art, clean cel shading, stable face, stable outfit, sharp hands, sharp legs, "
    "bright plain white background, readable 2d game animation frame, no ghost trails"
)

NEGATIVE_PROMPT = (
    "low quality, blurry, motion blur, ghost trail, afterimage, smeared limb, transparent limb, "
    "extra limbs, missing limbs, extra character, duplicate body, broken hands, broken feet, "
    "dark background, black background, strong cast shadow, background scenery, text, watermark, "
    "identity drift, face melting, changing outfit"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refine Wan-generated frames through local SDXL img2img.")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_wan_img2img_refine"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--checkpoint", default="novaOrangeXL_v120.safetensors")
    parser.add_argument("--width", default=1024, type=int)
    parser.add_argument("--height", default=1024, type=int)
    parser.add_argument("--steps", default=18, type=int)
    parser.add_argument("--cfg", default=5.5, type=float)
    parser.add_argument("--denoise", default=0.25, type=float)
    parser.add_argument("--sampler", default="dpmpp_2m")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--seed", default=707070, type=int)
    parser.add_argument("--seed-step", default=0, type=int)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--background-cleanup-threshold", default=0, type=int)
    parser.add_argument("--background-cleanup-min-channel", default=150, type=int)
    parser.add_argument("--positive", default=POSITIVE_PROMPT)
    parser.add_argument("--negative", default=NEGATIVE_PROMPT)
    add_queue_wait_arguments(parser)
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    args = parser.parse_args()

    source_frames = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not source_frames:
        raise FileNotFoundError(f"No png frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.frames_dir.parent.name}_img2img_d{args.denoise:.2f}")
    run_dir = args.output_root / time.strftime(f"{label}_%Y%m%d_%H%M%S")
    frames_dir = run_dir / "frames"
    source_dir = run_dir / "source_frames"
    workflow_dir = run_dir / "workflow"
    frames_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    workflow_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "status": "started",
        "purpose": "Refine Wan-generated action frames with low-denoise SDXL img2img.",
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
            "background_cleanup_threshold": args.background_cleanup_threshold,
            "background_cleanup_min_channel": args.background_cleanup_min_channel,
            "positive": args.positive,
            "negative": args.negative,
        },
        "prompt_ids": [],
        "frame_reports": [],
    }
    report_path = run_dir / "img2img_refine_report.json"

    try:
        refined_paths: list[Path] = []
        copied_sources: list[Path] = []
        indexed_sources = list(enumerate(source_frames))
        for index, source in progress_iter(
            indexed_sources,
            total=len(indexed_sources),
            desc="img2img refine frames",
            unit="frame",
        ):
            prepared_source = _prepare_source(
                source,
                source_dir / f"source_{index:03d}.png",
                args.width,
                args.height,
                args.background_cleanup_threshold,
                args.background_cleanup_min_channel,
            )
            copied_sources.append(prepared_source)
            image_name = _upload_image(args.comfy_url.rstrip("/"), prepared_source)
            workflow = _workflow(args, image_name, index)
            workflow_path = workflow_dir / f"frame_{index:03d}.json"
            workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            prompt_id = _queue_prompt(args.comfy_url.rstrip("/"), workflow, args=args)
            report["prompt_ids"].append(prompt_id)
            history = _wait_for_history(args.comfy_url.rstrip("/"), prompt_id, args.timeout_seconds)
            image_bytes = _download_first_saveimage(args.comfy_url.rstrip("/"), history, "9")
            output_path = frames_dir / f"frame_{index:03d}.png"
            Image.open(BytesIO(image_bytes)).convert("RGBA").save(output_path)
            refined_paths.append(output_path)
            report["frame_reports"].append(
                {
                    "index": index,
                    "source": str(source),
                    "prepared_source": str(prepared_source),
                    "output": str(output_path),
                    "source_delta": _mean_delta(prepared_source, output_path),
                }
            )

        preview = make_preview_gif(refined_paths, run_dir / "preview.gif", duration_ms=round(1000 / args.fps), loop=True)
        contact_sheet = make_contact_sheet(refined_paths, run_dir / "contact_sheet.png", columns=min(6, len(refined_paths)))
        source_contact_sheet = make_contact_sheet(copied_sources, run_dir / "source_contact_sheet.png", columns=min(6, len(copied_sources)))
        comparison = _make_comparison_sheet(copied_sources, refined_paths, run_dir / "comparison_sheet.png")
        report.update(
            {
                "status": "completed",
                "frame_count": len(refined_paths),
                "frames_dir": str(frames_dir),
                "preview_gif": str(preview),
                "contact_sheet": str(contact_sheet),
                "source_contact_sheet": str(source_contact_sheet),
                "comparison_sheet": str(comparison),
                "motion_metrics": _motion_metrics(refined_paths),
                "source_motion_metrics": _motion_metrics(copied_sources),
                "mean_source_delta": round(
                    sum(item["source_delta"] for item in report["frame_reports"]) / len(report["frame_reports"]),
                    3,
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
                key: report[key]
                for key in (
                    "status",
                    "frame_count",
                    "preview_gif",
                    "contact_sheet",
                    "comparison_sheet",
                    "motion_metrics",
                    "mean_source_delta",
                )
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _workflow(args: argparse.Namespace, image_name: str, index: int) -> dict[str, Any]:
    seed = args.seed + index * args.seed_step
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "3": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["2", 0],
                "upscale_method": "lanczos",
                "width": args.width,
                "height": args.height,
                "crop": "disabled",
            },
        },
        "4": {"class_type": "VAEEncode", "inputs": {"pixels": ["3", 0], "vae": ["1", 2]}},
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
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": f"natural_sprite_lab_img2img_refine_{index:03d}"},
        },
    }


def _prepare_source(
    source: Path,
    output: Path,
    width: int,
    height: int,
    cleanup_threshold: int,
    cleanup_min_channel: int,
) -> Path:
    image = Image.open(source).convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    flattened = background.convert("RGB")
    if cleanup_threshold > 0:
        flattened = _cleanup_near_background(flattened, cleanup_threshold, cleanup_min_channel)
    scale = min(width / flattened.width, height / flattened.height)
    resized = flattened.resize(
        (max(1, round(flattened.width * scale)), max(1, round(flattened.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    canvas.paste(resized, ((width - resized.width) // 2, (height - resized.height) // 2))
    canvas.save(output)
    return output


def _cleanup_near_background(image: Image.Image, threshold: int, min_channel: int) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    samples = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
        pixels[width // 2, 0],
        pixels[width // 2, height - 1],
    ]
    background = tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))
    output = image.copy()
    out = output.load()
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            if distance <= threshold and min(red, green, blue) >= min_channel:
                out[x, y] = (255, 255, 255)
    return output


def _upload_image(server_url: str, path: Path) -> str:
    data = path.read_bytes()
    filename = f"wan_img2img_refine_{uuid.uuid4().hex}.png"
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


def _make_comparison_sheet(source_paths: list[Path], refined_paths: list[Path], output_path: Path) -> Path:
    thumbs: list[tuple[str, Image.Image]] = []
    for index, (source, refined) in enumerate(zip(source_paths, refined_paths)):
        thumbs.append((f"{index:02d} src", Image.open(source).convert("RGB")))
        thumbs.append((f"{index:02d} img2img", Image.open(refined).convert("RGB")))
    thumb_w = 256
    thumb_h = 256
    columns = 4
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


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "img2img_refine"


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
