from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


DEFAULT_CONTROLNET_ROOT = Path("C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI/models/controlnet")


@dataclass(frozen=True)
class ModelCandidate:
    key: str
    filename: str
    url: str
    tags: tuple[str, ...]
    reason: str


CANDIDATES: dict[str, ModelCandidate] = {
    "t2i_lineart_sdxl": ModelCandidate(
        key="t2i_lineart_sdxl",
        filename="t2i-adapter_diffusers_xl_lineart.safetensors",
        url="https://huggingface.co/lllyasviel/sd_control_collection/resolve/main/"
        "t2i-adapter_diffusers_xl_lineart.safetensors",
        tags=("sdxl", "t2i-adapter", "lineart", "sidecar"),
        reason="Preferred first probe: lower-body shoe boxes and leg outlines are closer to lineart/sketch than OpenPose.",
    ),
    "t2i_sketch_sdxl": ModelCandidate(
        key="t2i_sketch_sdxl",
        filename="t2i-adapter_diffusers_xl_sketch.safetensors",
        url="https://huggingface.co/lllyasviel/sd_control_collection/resolve/main/"
        "t2i-adapter_diffusers_xl_sketch.safetensors",
        tags=("sdxl", "t2i-adapter", "sketch", "sidecar"),
        reason="Fallback if lineart cannot load; accepts sparse outline-like sidecars.",
    ),
    "sargezt_softedge_sdxl": ModelCandidate(
        key="sargezt_softedge_sdxl",
        filename="sargezt_xl_softedge.safetensors",
        url="https://huggingface.co/lllyasviel/sd_control_collection/resolve/main/sargezt_xl_softedge.safetensors",
        tags=("sdxl", "controlnet", "softedge", "sidecar"),
        reason="Fallback for softer silhouettes if lineart/sketch is too brittle or leaks.",
    ),
    "diffusers_canny_mid_sdxl": ModelCandidate(
        key="diffusers_canny_mid_sdxl",
        filename="diffusers_xl_canny_mid.safetensors",
        url="https://huggingface.co/lllyasviel/sd_control_collection/resolve/main/diffusers_xl_canny_mid.safetensors",
        tags=("sdxl", "controlnet", "canny", "sidecar"),
        reason="Fallback for edge-carrier compatibility checks.",
    ),
    "xinsir_union_sdxl": ModelCandidate(
        key="xinsir_union_sdxl",
        filename="controlnet++_union_sdxl.safetensors",
        url="https://huggingface.co/xinsir/controlnet-union-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors",
        tags=("sdxl", "controlnet", "union", "lineart", "softedge", "depth", "segment"),
        reason="Broad candidate only after local loader/control-type behavior is verified.",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory and acquire sidecar-suitable SDXL control models.")
    parser.add_argument("--controlnet-root", default=DEFAULT_CONTROLNET_ROOT, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="List locally available sidecar/control candidates.")
    inventory_parser.add_argument("--write-report", action="store_true")

    download_parser = subparsers.add_parser("download", help="Download one known model candidate if missing.")
    download_parser.add_argument("--candidate", default="t2i_lineart_sdxl", choices=tuple(CANDIDATES))
    download_parser.add_argument("--subdir", default="SDXL")
    download_parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    if args.command == "inventory":
        report = inventory_control_models(args.controlnet_root)
        if args.write_report:
            run_dir = _report_run_dir(args.output_root, args.run_label or "sidecar_model_inventory")
            _write_json(run_dir / "model_inventory_report.json", report)
            print(json.dumps({"report": str(run_dir / "model_inventory_report.json"), **report}, indent=2))
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    candidate = CANDIDATES[args.candidate]
    report = download_candidate(candidate, args.controlnet_root, subdir=args.subdir, force=args.force)
    run_dir = _report_run_dir(args.output_root, args.run_label or f"{candidate.key}_acquisition")
    _write_json(run_dir / "model_acquisition_report.json", report)
    print(json.dumps({"report": str(run_dir / "model_acquisition_report.json"), **report}, indent=2, ensure_ascii=False))


def inventory_control_models(root: Path) -> dict[str, Any]:
    files = sorted(root.rglob("*")) if root.exists() else []
    model_files = [path for path in files if path.is_file() and path.suffix.lower() in {".safetensors", ".pth", ".bin"}]
    local = [_describe_model_file(path, root) for path in model_files]
    candidate_status = []
    for candidate in CANDIDATES.values():
        matches = [item for item in local if item["name"].lower() == candidate.filename.lower()]
        candidate_status.append(
            {
                "key": candidate.key,
                "filename": candidate.filename,
                "present": bool(matches),
                "matches": matches,
                "tags": list(candidate.tags),
                "reason": candidate.reason,
                "url": candidate.url,
            }
        )
    return {
        "status": "completed",
        "controlnet_root": str(root),
        "model_count": len(local),
        "local_models": local,
        "candidate_status": candidate_status,
        "sidecar_tags_present": sorted({tag for item in local for tag in item["tags"] if tag != "other"}),
    }


def download_candidate(candidate: ModelCandidate, root: Path, *, subdir: str = "SDXL", force: bool = False) -> dict[str, Any]:
    target_dir = root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / candidate.filename
    if target.exists() and not force:
        return {
            "status": "already_present",
            "candidate": asdict(candidate),
            "target": str(target),
            "bytes": target.stat().st_size,
        }

    tmp = target.with_suffix(target.suffix + ".part")
    start = time.monotonic()
    with urllib.request.urlopen(candidate.url) as response, tmp.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        copied = _copy_with_progress(response, handle, total=total, label=candidate.filename)
    tmp.replace(target)
    elapsed = round(time.monotonic() - start, 3)
    return {
        "status": "downloaded",
        "candidate": asdict(candidate),
        "target": str(target),
        "bytes": target.stat().st_size,
        "streamed_bytes": copied,
        "elapsed_seconds": elapsed,
    }


def _describe_model_file(path: Path, root: Path) -> dict[str, Any]:
    name = path.name
    lowered = name.lower()
    tags = []
    for token in ("lineart", "sketch", "canny", "softedge", "depth", "seg", "segment", "union", "openpose", "t2i"):
        if token in lowered:
            tags.append(token)
    return {
        "name": name,
        "relative_path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "tags": tags or ["other"],
    }


def _copy_with_progress(response: Any, handle: Any, *, total: int, label: str) -> int:
    copied = 0
    try:
        from tqdm.auto import tqdm
    except Exception:  # pragma: no cover - fallback for minimal environments
        tqdm = None

    bar = tqdm(total=total or None, unit="B", unit_scale=True, desc=f"download {label}") if tqdm else None
    try:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            copied += len(chunk)
            if bar:
                bar.update(len(chunk))
            elif copied % (64 * 1024 * 1024) < len(chunk):
                print(f"downloaded {copied} bytes for {label}", file=sys.stderr)
    finally:
        if bar:
            bar.close()
    return copied


def _report_run_dir(output_root: Path, label: str) -> Path:
    run_dir = build_timestamped_run_dir(output_root, "model_management", label)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_run_profile(run_dir, category="model_management", label=label, extra={})
    return run_dir


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
