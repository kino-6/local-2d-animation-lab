from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_COMFY_ROOT = Path("C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI")
MODEL_DIRS = (
    "checkpoints",
    "controlnet",
    "diffusion_models",
    "unet",
    "vae",
    "clip",
    "clip_vision",
    "loras",
    "background_removal",
)
IMPORTANT_MODEL_PATTERNS = (
    "novaOrangeXL_v120",
    "OpenPoseXL2",
    "wan2.1_i2v_480p_14B_fp16",
    "Wan2.1-Fun-1.3B-Control",
    "Wan2.1-Fun-14B-Control",
    "wan2.1_vace_1.3B_fp16",
    "sdpose_wholebody_fp16",
    "birefnet",
    "sdxl_vae",
)
EXTRA_MODEL_PATH_KEYS = {
    "checkpoints": "checkpoints",
    "controlnet": "controlnet",
    "diffusion_models": "diffusion_models",
    "vae": "vae",
    "clip": "clip",
    "clip_vision": "clip_vision",
    "loras": "loras",
    "background_removal": "background_removal",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Snapshot local model and ComfyUI environment for reproducible PDCA results."
    )
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--comfy-root", default=DEFAULT_COMFY_ROOT, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_environment_snapshot"), type=Path)
    parser.add_argument("--model-dir", action="append", default=None, choices=MODEL_DIRS)
    parser.add_argument("--important-pattern", action="append", default=None)
    parser.add_argument("--hash-all", action="store_true")
    parser.add_argument("--hash-max-mb", default=20480.0, type=float)
    parser.add_argument("--skip-comfy", action="store_true")
    args = parser.parse_args()

    model_dirs = tuple(args.model_dir or MODEL_DIRS)
    important_patterns = tuple(args.important_pattern or IMPORTANT_MODEL_PATTERNS)
    run_dir = args.output_root / time.strftime("environment_snapshot_%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    snapshot = build_snapshot(
        comfy_url=args.comfy_url.rstrip("/"),
        comfy_root=args.comfy_root,
        model_dirs=model_dirs,
        important_patterns=important_patterns,
        hash_all=args.hash_all,
        hash_max_mb=args.hash_max_mb,
        skip_comfy=args.skip_comfy,
    )
    json_path = run_dir / "environment_snapshot.json"
    summary_path = run_dir / "environment_snapshot_summary.md"
    json_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_path.write_text(render_markdown_summary(snapshot), encoding="utf-8")
    print(summary_path)


def build_snapshot(
    *,
    comfy_url: str,
    comfy_root: Path,
    model_dirs: tuple[str, ...],
    important_patterns: tuple[str, ...],
    hash_all: bool,
    hash_max_mb: float,
    skip_comfy: bool,
) -> dict[str, Any]:
    object_info = {} if skip_comfy else _fetch_json(f"{comfy_url}/object_info")
    return {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "repo": _repo_info(),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "comfy": {
            "url": comfy_url,
            "root": str(comfy_root),
            "object_info_available": bool(object_info),
            "node_count": len(object_info),
            "important_node_presence": _important_node_presence(object_info),
            "model_choices": _model_choices(object_info),
        },
        "models": inventory_models(
            comfy_root=comfy_root,
            model_dirs=model_dirs,
            important_patterns=important_patterns,
            hash_all=hash_all,
            hash_max_mb=hash_max_mb,
        ),
    }


def inventory_models(
    *,
    comfy_root: Path,
    model_dirs: tuple[str, ...],
    important_patterns: tuple[str, ...],
    hash_all: bool,
    hash_max_mb: float,
) -> dict[str, Any]:
    models_root = comfy_root / "models"
    extra_model_paths = parse_extra_model_paths(comfy_root / "extra_model_paths.yaml")
    result: dict[str, Any] = {
        "root": str(models_root),
        "extra_model_paths_file": str(comfy_root / "extra_model_paths.yaml"),
        "directories": {},
        "important_patterns": list(important_patterns),
    }
    for model_dir in model_dirs:
        roots = [models_root / model_dir]
        roots.extend(extra_model_paths.get(EXTRA_MODEL_PATH_KEYS.get(model_dir, model_dir), []))
        files = []
        for root in roots:
            for path in sorted(root.rglob("*")) if root.exists() else []:
                if path.is_file():
                    files.append(_file_record(path, root, important_patterns, hash_all, hash_max_mb))
        result["directories"][model_dir] = {
            "paths": [str(root) for root in roots],
            "exists": any(root.exists() for root in roots),
            "file_count": len(files),
            "files": files,
        }
    return result


def render_markdown_summary(snapshot: dict[str, Any]) -> str:
    lines = [
        "# Local Environment Snapshot",
        "",
        f"- created_at: `{snapshot['created_at']}`",
        f"- repo: `{snapshot['repo'].get('commit', 'unknown')}` on `{snapshot['repo'].get('branch', 'unknown')}`",
        f"- python: `{snapshot['runtime']['python']}`",
        f"- platform: `{snapshot['runtime']['platform']}`",
        f"- ComfyUI url: `{snapshot['comfy']['url']}`",
        f"- ComfyUI root: `{snapshot['comfy']['root']}`",
        f"- ComfyUI object_info nodes: `{snapshot['comfy']['node_count']}`",
        "",
        "## Important Nodes",
        "",
    ]
    for name, available in snapshot["comfy"]["important_node_presence"].items():
        lines.append(f"- `{name}`: `{available}`")
    lines.extend(["", "## Model Directories", ""])
    for name, directory in snapshot["models"]["directories"].items():
        lines.append(f"### {name}")
        paths = directory.get("paths") or [directory.get("path", "-")]
        lines.append(f"- paths: {', '.join(f'`{path}`' for path in paths)}")
        lines.append(f"- exists: `{directory['exists']}`")
        lines.append(f"- file_count: `{directory['file_count']}`")
        important = [item for item in directory["files"] if item["important"]]
        if important:
            lines.append("- important files:")
            for item in important:
                hash_text = item.get("sha256") or item.get("sha256_status", "not_hashed")
                lines.append(
                    f"  - `{item['relative_path']}` size `{item['size_bytes']}` mtime `{item['mtime']}` sha256 `{hash_text}`"
                )
        lines.append("")
    lines.extend(["## Model Choices From ComfyUI", ""])
    for loader, choices in snapshot["comfy"]["model_choices"].items():
        preview = ", ".join(f"`{choice}`" for choice in choices[:20])
        suffix = " ..." if len(choices) > 20 else ""
        lines.append(f"- `{loader}` ({len(choices)}): {preview}{suffix}")
    return "\n".join(lines) + "\n"


def _file_record(
    path: Path,
    root: Path,
    important_patterns: tuple[str, ...],
    hash_all: bool,
    hash_max_mb: float,
) -> dict[str, Any]:
    stat = path.stat()
    important = _matches_any(path.name, important_patterns)
    should_hash = (hash_all or important) and stat.st_size <= hash_max_mb * 1024 * 1024
    record: dict[str, Any] = {
        "relative_path": path.relative_to(root).as_posix(),
        "root": str(root),
        "size_bytes": stat.st_size,
        "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
        "important": important,
    }
    if should_hash:
        record["sha256"] = _sha256(path)
    elif hash_all or important:
        record["sha256_status"] = "skipped_size_limit"
    else:
        record["sha256_status"] = "not_requested"
    return record


def parse_extra_model_paths(path: Path) -> dict[str, list[Path]]:
    if not path.exists():
        return {}
    result: dict[str, list[Path]] = {}
    current_key: str | None = None
    in_block = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  ") and not line.startswith("    ") and ":" in stripped:
            current_key = stripped.split(":", 1)[0]
            in_block = stripped.endswith("|-") or stripped.endswith("|")
            result.setdefault(current_key, [])
            continue
        if current_key and in_block and line.startswith("    "):
            result[current_key].append(Path(stripped))
    return result


def _matches_any(value: str, patterns: tuple[str, ...]) -> bool:
    lower = value.lower()
    return any(pattern.lower() in lower for pattern in patterns)


def _important_node_presence(object_info: dict[str, Any]) -> dict[str, bool]:
    names = (
        "CheckpointLoaderSimple",
        "ControlNetLoader",
        "UNETLoader",
        "WanImageToVideo",
        "WanFirstLastFrameToVideo",
        "WanAnimateToVideo",
        "WanFunControlToVideo",
        "WanVaceToVideo",
        "SDPoseKeypointExtractor",
        "BiRefNetRMBG",
    )
    return {name: name in object_info for name in names}


def _model_choices(object_info: dict[str, Any]) -> dict[str, list[str]]:
    loaders = {
        "CheckpointLoaderSimple": "ckpt_name",
        "ControlNetLoader": "control_net_name",
        "UNETLoader": "unet_name",
        "VAELoader": "vae_name",
        "CLIPLoader": "clip_name",
        "CLIPVisionLoader": "clip_name",
    }
    return {loader: _combo_options(object_info, loader, field) for loader, field in loaders.items()}


def _combo_options(object_info: dict[str, Any], node: str, field: str) -> list[str]:
    values = object_info.get(node, {}).get("input", {}).get("required", {}).get(field)
    if not values or not isinstance(values, list) or not values:
        return []
    choices = values[0]
    return sorted(str(choice) for choice in choices) if isinstance(choices, list) else []


def _repo_info() -> dict[str, str]:
    return {
        "branch": _git(["branch", "--show-current"]),
        "commit": _git(["rev-parse", "HEAD"]),
        "status_short": _git(["status", "--short"]),
    }


def _git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError):
        return {}


if __name__ == "__main__":
    main()
