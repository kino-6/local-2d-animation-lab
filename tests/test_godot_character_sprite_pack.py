from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_character_sprite_asset_pack_loads_in_godot() -> None:
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("Godot CLI is not installed")

    repo_root = Path(__file__).resolve().parents[1]
    manifest = repo_root / "outputs" / "adoptable" / "character_sprite_asset_pack" / "manifest.json"
    assert manifest.exists()

    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(repo_root / "godot"),
            "--script",
            "res://tests/pack_e2e_runner.gd",
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
    payload = _last_json_line(result.stdout)
    assert payload["ok"] is True
    assert payload["production_ready"] is True
    assert payload["action_count"] == 8
    assert set(payload["actions"]) == {
        "walk",
        "idle",
        "run",
        "jump",
        "hurt",
        "dodge_backstep",
        "parry_sword",
        "attack_sword_light",
    }
    assert payload["actions"]["walk"]["frame_count"] == 8
    assert payload["actions"]["idle"]["frame_count"] == 4
    assert payload["actions"]["run"]["frame_count"] == 8
    assert payload["actions"]["jump"]["frame_count"] == 12
    assert payload["actions"]["hurt"]["frame_count"] == 8
    assert payload["actions"]["dodge_backstep"]["frame_count"] == 8
    assert payload["actions"]["parry_sword"]["frame_count"] == 8
    assert payload["actions"]["attack_sword_light"]["frame_count"] == 12
    assert payload["actions"]["walk"]["loop"] is True
    assert payload["actions"]["run"]["loop"] is True
    assert payload["actions"]["jump"]["loop"] is False
    assert payload["actions"]["hurt"]["loop"] is False
    assert payload["actions"]["dodge_backstep"]["loop"] is False
    assert payload["actions"]["parry_sword"]["loop"] is False
    assert payload["actions"]["attack_sword_light"]["loop"] is False


def _last_json_line(output: str) -> dict[str, object]:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"No JSON payload found in Godot output:\n{output}")
