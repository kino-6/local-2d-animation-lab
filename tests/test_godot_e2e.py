from __future__ import annotations

import json
import shutil
import subprocess
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


def _last_json_line(output: str) -> dict[str, object]:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"No JSON payload found in Godot output:\n{output}")
