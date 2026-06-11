from __future__ import annotations

import json
import shutil
import subprocess
import importlib.util
from pathlib import Path

import pytest
from PIL import Image

from natural_sprite_lab.backends import DummyBackend
from natural_sprite_lab.pipeline import run_pipeline
from natural_sprite_lab.planning import WalkCycleDirector


def test_generated_attack_manifest_loads_in_godot(tmp_path: Path) -> None:
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("Godot CLI is not installed")

    source = tmp_path / "hero.png"
    Image.new("RGBA", (96, 128), (210, 120, 80, 255)).save(source)
    outputs = run_pipeline(
        source_image=source,
        prompt="Create an 8-frame bow attack animation facing right.",
        backend=DummyBackend(),
        output_root=tmp_path / "outputs",
        run_id="godot_attack_run",
        director=WalkCycleDirector(use_ollama=False),
    )

    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(repo_root / "godot"),
            "--script",
            "res://tests/e2e_runner.gd",
            "--",
            "--manifest",
            str(outputs.manifest_path),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = _last_json_line(result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "attack"
    assert payload["frame_count"] == 8
    assert payload["frame_size"]["width"] > 0
    assert payload["frame_size"]["height"] > 0
    assert payload["using_composited"] is True


def test_pdca_summary_best_asset_loads_in_godot(tmp_path: Path) -> None:
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("Godot CLI is not installed")

    source = tmp_path / "hero.png"
    Image.new("RGBA", (96, 128), (210, 120, 80, 255)).save(source)
    outputs = run_pipeline(
        source_image=source,
        prompt="Create an 8-frame light hit reaction animation facing right.",
        backend=DummyBackend(),
        output_root=tmp_path / "outputs",
        run_id="godot_summary_run",
        director=WalkCycleDirector(use_ollama=False),
    )
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "best_by_asset": {
                    "hit_light": {
                        "run_dir": str(outputs.run_dir),
                        "score": 1.0,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parents[1]
    validate_summary = _load_validate_summary(repo_root)
    result = validate_summary(summary_path, godot=godot, godot_project=repo_root / "godot")

    assert result["results"][0]["ok"] is True
    assert result["results"][0]["asset"] == "hit_light"


def test_direct_manifest_validation_loads_review_package_manifest(tmp_path: Path) -> None:
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("Godot CLI is not installed")

    source = tmp_path / "hero.png"
    Image.new("RGBA", (96, 128), (210, 120, 80, 255)).save(source)
    outputs = run_pipeline(
        source_image=source,
        prompt="Create an 8-frame running animation facing right.",
        backend=DummyBackend(),
        output_root=tmp_path / "outputs",
        run_id="godot_direct_manifest_run",
        director=WalkCycleDirector(use_ollama=False),
    )

    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "godot_validate_summary.py"
    spec = importlib.util.spec_from_file_location("godot_validate_summary", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.validate_manifest(outputs.manifest_path, godot=godot, godot_project=repo_root / "godot")

    assert result["ok"] is True
    assert result["frame_count"] == 8


def _last_json_line(output: str) -> dict[str, object]:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"No JSON payload found in Godot output:\n{output}")


def _load_validate_summary(repo_root: Path):
    module_path = repo_root / "scripts" / "godot_validate_summary.py"
    spec = importlib.util.spec_from_file_location("godot_validate_summary", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_summary
