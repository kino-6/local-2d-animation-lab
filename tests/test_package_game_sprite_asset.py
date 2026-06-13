from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "package_game_sprite_asset.py"
_SPEC = importlib.util.spec_from_file_location("package_game_sprite_asset", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_remove_background_creates_alpha() -> None:
    source = Image.new("RGB", (64, 64), (255, 255, 255))
    draw = ImageDraw.Draw(source)
    draw.rectangle((24, 10, 40, 55), fill=(10, 20, 30))
    path = Path("test_sprite_source.png")
    try:
        source.save(path)
        rgba, report = _MODULE._remove_background(path, threshold=30, min_channel=220)
    finally:
        path.unlink(missing_ok=True)

    assert rgba.mode == "RGBA"
    assert rgba.getchannel("A").getbbox() is not None
    assert report["alpha_coverage"] > 0
    assert rgba.getpixel((0, 0))[3] == 0


def test_remove_background_preserves_internal_white_highlight() -> None:
    source = Image.new("RGB", (64, 64), (255, 255, 255))
    draw = ImageDraw.Draw(source)
    draw.rectangle((20, 12, 44, 56), fill=(10, 20, 30))
    draw.rectangle((28, 24, 35, 31), fill=(252, 252, 252))
    path = Path("test_sprite_highlight.png")
    try:
        source.save(path)
        rgba, _ = _MODULE._remove_background(path, threshold=30, min_channel=220)
    finally:
        path.unlink(missing_ok=True)

    assert rgba.getpixel((0, 0))[3] == 0
    assert rgba.getpixel((30, 26))[3] == 255


def test_package_game_sprite_asset_cli(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(2):
        image = Image.new("RGB", (96, 128), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((38 + index, 16, 58 + index, 112), fill=(20, 25, 30))
        image.save(frames / f"frame_{index:03d}.png")

    output_root = tmp_path / "assets"
    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--frames-dir",
            str(frames),
            "--output-root",
            str(output_root),
            "--run-label",
            "test_asset",
            "--asset-name",
            "test_character",
            "--animation",
            "idle",
            "--frame-width",
            "128",
            "--frame-height",
            "128",
            "--target-height",
            "104",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    run_dir = Path(payload["run_dir"])

    assert (run_dir / "frames" / "frame_000.png").exists()
    assert (run_dir / "spritesheet.png").exists()
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["asset_kind"] == "2d_game_sprite"
    assert manifest["pivot"] == {"x": 0.5, "y": 1.0}
