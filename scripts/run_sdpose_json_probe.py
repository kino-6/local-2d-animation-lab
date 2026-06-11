from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the local ComfyUI SDPose -> POSE_KEYPOINT JSON saver path."
    )
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument(
        "--input",
        default=Path("outputs_next_phase_startframe/auto_cleaned_run_strong_pose_20260611_032832/start_frame.png"),
        type=Path,
    )
    parser.add_argument("--output-root", default=Path("outputs_sdpose_json_probe"), type=Path)
    parser.add_argument("--run-label", default="sdpose_json_probe")
    parser.add_argument("--checkpoint", default="sdpose_wholebody_fp16.safetensors")
    parser.add_argument("--vae", default="sdxl_vae.safetensors")
    parser.add_argument("--timeout-seconds", default=600.0, type=float)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    server = args.comfy_url.rstrip("/")
    object_info = _get_json(server, "/object_info", timeout=20)
    queue = _get_json(server, "/queue", timeout=20)
    has_saver = "NaturalSpriteSavePoseKeypointsJSON" in object_info
    has_sdpose = args.checkpoint in object_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    status = {
        "has_saver": has_saver,
        "has_sdpose_checkpoint": has_sdpose,
        "queue_running": len(queue.get("queue_running", [])),
        "queue_pending": len(queue.get("queue_pending", [])),
    }
    if args.check_only or not (has_saver and has_sdpose):
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return

    run_dir = args.output_root / time.strftime(f"{_safe_label(args.run_label)}_%Y%m%d_%H%M%S")
    workflow_dir = run_dir / "workflow"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    image_name = _upload_image(server, args.input)
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": args.vae}},
        "3": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "4": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["3", 0],
                "upscale_method": "lanczos",
                "width": 512,
                "height": 512,
                "crop": "center",
            },
        },
        "5": {
            "class_type": "SDPoseKeypointExtractor",
            "inputs": {"model": ["1", 0], "vae": ["2", 0], "image": ["4", 0], "batch_size": 1},
        },
        "6": {
            "class_type": "NaturalSpriteSavePoseKeypointsJSON",
            "inputs": {
                "keypoints": ["5", 0],
                "folder_name": "natural_sprite_lab/pose_keypoints",
                "filename_prefix": _safe_label(args.run_label),
            },
        },
    }
    workflow_path = workflow_dir / "sdpose_json_probe_api.json"
    workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    prompt_id = _queue_prompt(server, workflow)
    history = _wait_for_history(server, prompt_id, args.timeout_seconds)
    output = history.get("outputs", {}).get("6", {})
    report = {
        "status": "completed",
        "input": str(args.input),
        "workflow": str(workflow_path),
        "prompt_id": prompt_id,
        "saver_output": output,
    }
    report_path = run_dir / "sdpose_json_probe_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def _safe_label(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip()) or "sdpose_json_probe"


def _get_json(server: str, path: str, timeout: float) -> dict[str, Any]:
    with urllib.request.urlopen(server + path, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _upload_image(server: str, path: Path) -> str:
    data = path.read_bytes()
    filename = f"sdpose_json_probe_{uuid.uuid4().hex}.png"
    boundary = f"----natural-sprite-lab-{uuid.uuid4().hex}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("ascii"),
            (
                f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
                "Content-Type: image/png\r\n\r\n"
            ).encode("ascii"),
            data,
            f"\r\n--{boundary}--\r\n".encode("ascii"),
        ]
    )
    request = urllib.request.Request(
        server + "/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    payload = json.loads(urllib.request.urlopen(request, timeout=60).read().decode("utf-8"))
    return str(payload.get("name") or filename)


def _queue_prompt(server: str, workflow: dict[str, Any]) -> str:
    body = json.dumps({"prompt": workflow, "client_id": str(uuid.uuid4())}).encode("utf-8")
    request = urllib.request.Request(
        server + "/prompt",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    payload = json.loads(urllib.request.urlopen(request, timeout=60).read().decode("utf-8"))
    return str(payload["prompt_id"])


def _wait_for_history(server: str, prompt_id: str, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        history = _get_json(server, f"/history/{prompt_id}", timeout=60)
        if prompt_id in history:
            item = history[prompt_id]
            if item.get("status", {}).get("status_str") == "error" or item.get("node_errors"):
                raise RuntimeError(json.dumps(item.get("node_errors") or item.get("status"), indent=2))
            return item
        time.sleep(2)
    raise TimeoutError(prompt_id)


if __name__ == "__main__":
    main()
