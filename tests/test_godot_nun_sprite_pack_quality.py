from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat


def test_nun_sprite_pack_reports_visual_quality_in_godot() -> None:
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
    assert manifest.exists()

    result = _run_pack_e2e(godot, repo_root, manifest)
    assert result.returncode == 0, result.stderr + result.stdout
    payload = _last_json_line(result.stdout + "\n" + result.stderr)

    assert payload["ok"] is True
    assert payload["production_ready"] is True
    assert payload["actions"]["jump"]["frame_count"] == 12
    assert payload["visual_quality"]["available"] is True
    assert payload["visual_quality"]["decision"] == "production_ready"
    assert payload["visual_quality"]["blocking_actions"] == []
    assert payload["actions"]["jump"]["visual_quality"]["decision"] == "production_ready"
    assert payload["actions"]["jump"]["visual_quality"]["findings"] == []
    assert payload["actions"]["hurt"]["visual_quality"]["findings"] == []


def test_nun_sprite_pack_strict_godot_quality_gate_passes_after_hurt_retake() -> None:
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

    result = _run_pack_e2e(godot, repo_root, manifest, "--require-production-ready")
    assert result.returncode == 0, result.stderr + result.stdout
    payload = _last_json_line(result.stdout + "\n" + result.stderr)
    assert payload["ok"] is True
    assert payload["visual_quality"]["production_ready"] is True
    assert payload["visual_quality"]["blocking_actions"] == []


def test_nun_sprite_pack_preview_gifs_are_e2e_reviewable() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pack = repo_root / "outputs" / "adoptable" / "nun_skirt_boots_character_sprite_asset_pack"
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))

    for action, info in manifest["actions"].items():
        gif_path = pack / "actions" / action / "preview.gif"
        assert gif_path.exists(), action
        with Image.open(gif_path) as gif:
            assert gif.n_frames == info["frame_count"], action
            assert gif.size == (256, 384), action
            frames = [_gif_frame(gif, index) for index in range(gif.n_frames)]
            step_deltas = [_mean_delta(frames[index], frames[index + 1]) for index in range(len(frames) - 1)]
            assert max(step_deltas, default=0) > 0.2 or gif.n_frames == 1, action


def _run_pack_e2e(
    godot: str,
    repo_root: Path,
    manifest: Path,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
            *extra_args,
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _last_json_line(output: str) -> dict[str, object]:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"No JSON payload found in Godot output:\n{output}")


def _gif_frame(gif: Image.Image, index: int) -> Image.Image:
    gif.seek(index)
    return gif.convert("RGBA")


def _mean_delta(left: Image.Image, right: Image.Image) -> float:
    return ImageStat.Stat(ImageChops.difference(left, right).convert("L")).mean[0]
