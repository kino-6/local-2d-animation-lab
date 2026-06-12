from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "snapshot_local_environment.py"
_SPEC = importlib.util.spec_from_file_location("snapshot_local_environment", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_inventory_models_hashes_important_file(tmp_path: Path) -> None:
    model = tmp_path / "models" / "checkpoints" / "novaOrangeXL_v120.safetensors"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"model")

    inventory = _MODULE.inventory_models(
        comfy_root=tmp_path,
        model_dirs=("checkpoints",),
        important_patterns=("novaOrangeXL_v120",),
        hash_all=False,
        hash_max_mb=1.0,
    )

    file_record = inventory["directories"]["checkpoints"]["files"][0]
    assert file_record["important"] is True
    assert file_record["sha256"] == "9372c470eeadd5ecd9c3c74c2b3cb633f8e2f2fad799250a0f70d652b6b825e4"


def test_inventory_models_includes_extra_model_paths(tmp_path: Path) -> None:
    comfy_root = tmp_path / "ComfyUI"
    extra_root = tmp_path / "Models" / "StableDiffusion"
    extra_root.mkdir(parents=True)
    (extra_root / "novaOrangeXL_v120.safetensors").write_bytes(b"model")
    comfy_root.mkdir()
    (comfy_root / "extra_model_paths.yaml").write_text(
        "stability_matrix:\n"
        "  checkpoints: |-\n"
        f"    {extra_root.as_posix()}\n",
        encoding="utf-8",
    )

    inventory = _MODULE.inventory_models(
        comfy_root=comfy_root,
        model_dirs=("checkpoints",),
        important_patterns=("novaOrangeXL_v120",),
        hash_all=False,
        hash_max_mb=1.0,
    )

    files = inventory["directories"]["checkpoints"]["files"]
    assert files[0]["relative_path"] == "novaOrangeXL_v120.safetensors"


def test_render_markdown_summary_includes_model_choices() -> None:
    snapshot = {
        "created_at": "2026-06-12 00:00:00 +0900",
        "repo": {"branch": "main", "commit": "abc"},
        "runtime": {"python": "3.14", "platform": "Windows"},
        "comfy": {
            "url": "http://127.0.0.1:8188",
            "root": "C:/ComfyUI",
            "node_count": 1,
            "important_node_presence": {"WanImageToVideo": True},
            "model_choices": {"CheckpointLoaderSimple": ["novaOrangeXL_v120.safetensors"]},
        },
        "models": {
            "directories": {
                "checkpoints": {
                    "paths": ["C:/ComfyUI/models/checkpoints"],
                    "exists": True,
                    "file_count": 1,
                    "files": [
                        {
                            "relative_path": "novaOrangeXL_v120.safetensors",
                            "size_bytes": 5,
                            "mtime": "2026-06-12 00:00:00",
                            "important": True,
                            "sha256": "abc",
                        }
                    ],
                }
            }
        },
    }

    summary = _MODULE.render_markdown_summary(snapshot)

    assert "novaOrangeXL_v120.safetensors" in summary
    assert "WanImageToVideo" in summary
