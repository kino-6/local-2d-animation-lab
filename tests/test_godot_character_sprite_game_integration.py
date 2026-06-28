from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_nun_sprite_pack_loads_as_game_player() -> None:
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("Godot CLI is not installed")

    repo_root = Path(__file__).resolve().parents[1]
    manifest = (
        repo_root
        / "outputs"
        / "adoptable"
        / "nun_skirt_boots_character_sprite_asset_pack"
        / "manifest.json"
    )

    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(repo_root / "godot"),
            "--script",
            "res://tests/character_sprite_pack_game_runner.gd",
            "--",
            "--manifest",
            str(manifest),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = _last_json_line(result.stdout + "\n" + result.stderr)
    assert payload["ok"] is True
    assert payload["production_ready"] is True
    assert payload["action_count"] == 6
    assert payload["observed_actions"] == [
        "idle",
        "walk",
        "run",
        "jump",
        "attack_sword_light",
        "hurt",
    ]
    assert payload["collision_size"]["width"] > 0
    assert payload["collision_size"]["height"] > 0


def _last_json_line(output: str) -> dict[str, object]:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"No JSON payload found in Godot output:\n{output}")

