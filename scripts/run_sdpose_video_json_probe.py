from __future__ import annotations

import argparse
import json
import shutil
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any


DEFAULT_COMFY_ROOT = Path("C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run local ComfyUI video -> SDPose -> POSE_KEYPOINT JSON export."
    )
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--comfy-root", default=DEFAULT_COMFY_ROOT, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_sdpose_video_json_probe"), type=Path)
    parser.add_argument("--run-label", default="sdpose_video_json_probe")
    parser.add_argument("--checkpoint", default="sdpose_wholebody_fp16.safetensors")
    parser.add_argument("--vae", default="sdxl_vae.safetensors")
    parser.add_argument("--batch-size", default=16, type=int)
    parser.add_argument("--timeout-seconds", default=1200.0, type=float)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--wait-for-idle", action="store_true")
    parser.add_argument("--idle-timeout-seconds", default=1800.0, type=float)
    args = parser.parse_args()

    server = args.comfy_url.rstrip("/")
    object_info = _get_json(server, "/object_info", timeout=20)
    queue = _wait_for_idle(server, args.idle_timeout_seconds) if args.wait_for_idle else _get_json(server, "/queue", timeout=20)
    has_saver = "NaturalSpriteSavePoseKeypointsJSON" in object_info
    has_sdpose = args.checkpoint in object_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    has_load_video = "LoadVideo" in object_info and "GetVideoComponents" in object_info
    status = {
        "has_saver": has_saver,
        "has_sdpose_checkpoint": has_sdpose,
        "has_video_nodes": has_load_video,
        "queue_running": len(queue.get("queue_running", [])),
        "queue_pending": len(queue.get("queue_pending", [])),
    }
    if args.check_only or not (has_saver and has_sdpose and has_load_video):
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return

    if not args.wait_for_idle and (status["queue_running"] or status["queue_pending"]):
        print(json.dumps(status | {"status": "busy"}, indent=2, ensure_ascii=False))
        return

    if not args.video.exists():
        raise FileNotFoundError(args.video)

    run_label = _safe_label(args.run_label)
    run_dir = args.output_root / time.strftime(f"{run_label}_%Y%m%d_%H%M%S")
    workflow_dir = run_dir / "workflow"
    workflow_dir.mkdir(parents=True, exist_ok=True)

    video_name = _copy_video_to_comfy_input(args.video, args.comfy_root, run_label)
    workflow = {
        "1": {"class_type": "LoadVideo", "inputs": {"file": video_name}},
        "2": {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}},
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": args.vae}},
        "5": {
            "class_type": "SDPoseKeypointExtractor",
            "inputs": {
                "model": ["3", 0],
                "vae": ["4", 0],
                "image": ["2", 0],
                "batch_size": args.batch_size,
            },
        },
        "6": {
            "class_type": "NaturalSpriteSavePoseKeypointsJSON",
            "inputs": {
                "keypoints": ["5", 0],
                "folder_name": "natural_sprite_lab/pose_keypoints",
                "filename_prefix": run_label,
            },
        },
    }
    workflow_path = workflow_dir / "sdpose_video_json_probe_api.json"
    workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    prompt_id = _queue_prompt(server, workflow)
    history = _wait_for_history(server, prompt_id, args.timeout_seconds)
    output = history.get("outputs", {}).get("6", {})
    report = {
        "status": "completed",
        "source_video": str(args.video),
        "comfy_input_video": video_name,
        "workflow": str(workflow_path),
        "prompt_id": prompt_id,
        "saver_output": output,
    }
    report_path = run_dir / "sdpose_video_json_probe_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def _copy_video_to_comfy_input(source: Path, comfy_root: Path, run_label: str) -> str:
    input_dir = comfy_root / "input" / "natural_sprite_lab"
    input_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{run_label}_{uuid.uuid4().hex[:8]}{source.suffix.lower()}"
    target = input_dir / safe_name
    shutil.copy2(source, target)
    return f"natural_sprite_lab/{safe_name}"


def _safe_label(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip()) or "sdpose_video_json_probe"


def _get_json(server: str, path: str, timeout: float) -> dict[str, Any]:
    with urllib.request.urlopen(server + path, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_idle(server: str, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = _get_json(server, "/queue", timeout=20)
        if not latest.get("queue_running") and not latest.get("queue_pending"):
            return latest
        time.sleep(5)
    raise TimeoutError(
        "Timed out waiting for ComfyUI queue to become idle: "
        + json.dumps(
            {
                "queue_running": len(latest.get("queue_running", [])),
                "queue_pending": len(latest.get("queue_pending", [])),
            },
            ensure_ascii=False,
        )
    )


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
