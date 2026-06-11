from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import folder_paths


class NaturalSpriteSavePoseKeypointsJSON:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "keypoints": ("POSE_KEYPOINT",),
                "folder_name": ("STRING", {"default": "natural_sprite_lab/pose_keypoints"}),
                "filename_prefix": ("STRING", {"default": "pose_keypoints"}),
            }
        }

    RETURN_TYPES: tuple = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "natural_sprite_lab/pose"

    def save(self, keypoints: Any, folder_name: str, filename_prefix: str) -> dict[str, Any]:
        safe_folder = _safe_relative(folder_name)
        safe_prefix = _safe_filename(filename_prefix) or "pose_keypoints"
        output_root = Path(folder_paths.get_output_directory())
        target_dir = output_root / safe_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        path = _next_path(target_dir, safe_prefix)
        payload = {
            "format": "openpose_frames",
            "frames": keypoints if isinstance(keypoints, list) else [keypoints],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"ui": {"text": [str(path)]}}


def _safe_relative(value: str) -> Path:
    parts = [_safe_filename(part) for part in Path(value).parts if part not in {"", ".", ".."}]
    return Path(*[part for part in parts if part]) if parts else Path("natural_sprite_lab/pose_keypoints")


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())


def _next_path(directory: Path, prefix: str) -> Path:
    for index in range(100000):
        path = directory / f"{prefix}_{index:05d}.json"
        if not path.exists():
            return path
    raise RuntimeError(f"Could not allocate output path in {directory}")


NODE_CLASS_MAPPINGS = {
    "NaturalSpriteSavePoseKeypointsJSON": NaturalSpriteSavePoseKeypointsJSON,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NaturalSpriteSavePoseKeypointsJSON": "Natural Sprite Save Pose Keypoints JSON",
}
