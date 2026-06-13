from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stabilize_masked_sprite_sequence.py"
_SPEC = importlib.util.spec_from_file_location("stabilize_masked_sprite_sequence", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_masked_rgb_stabilization_keeps_background_white_and_improves_luma(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    masks = tmp_path / "masks"
    frames.mkdir()
    masks.mkdir()
    _frame(frames / "frame_000.png", color=(120, 80, 60))
    _frame(frames / "frame_001.png", color=(40, 70, 35))
    _frame(frames / "frame_002.png", color=(30, 55, 30))
    for index in range(3):
        _mask(masks / f"foreground_mask_{index:03d}.png")

    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--frames-dir",
            str(frames),
            "--masks-dir",
            str(masks),
            "--output-root",
            str(tmp_path / "out"),
            "--run-label",
            "masked_stabilize_test",
            "--color-mode",
            "rgb_mean",
            "--brightness-strength",
            "1.0",
            "--max-factor",
            "4.0",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["after_summary"]["foreground_luma_mean"] > payload["before_summary"]["foreground_luma_mean"]
    output = Image.open(Path(payload["run_dir"]) / "frames" / "frame_001.png").convert("RGB")
    assert output.getpixel((0, 0)) == (255, 255, 255)
    assert output.getpixel((24, 24))[0] > 90


def test_rgb_mean_correction_moves_masked_color_toward_target() -> None:
    frame = Image.new("RGB", (16, 16), (255, 255, 255))
    mask = Image.new("L", (16, 16), 0)
    for y in range(4, 12):
        for x in range(4, 12):
            frame.putpixel((x, y), (40, 80, 30))
            mask.putpixel((x, y), 255)

    metric = _MODULE._masked_metrics(frame, mask)
    target = {"foreground_luma": 0.0, "foreground_saturation": 0.0, "foreground_rgb": [120.0, 80.0, 60.0]}
    corrected, correction = _MODULE._correct(
        frame,
        mask,
        metric,
        target_metrics=target,
        color_mode="rgb_mean",
        brightness_strength=1.0,
        saturation_strength=0.0,
        min_factor=0.65,
        max_factor=4.0,
    )

    after = _MODULE._masked_metrics(corrected, mask)
    assert correction["red_factor"] > correction["green_factor"]
    assert after["foreground_rgb"][0] > metric["foreground_rgb"][0]
    assert corrected.getpixel((0, 0)) == (255, 255, 255)


def test_histogram_match_moves_masked_distribution_toward_target() -> None:
    target_frame = Image.new("RGB", (16, 16), (255, 255, 255))
    frame = Image.new("RGB", (16, 16), (255, 255, 255))
    mask = Image.new("L", (16, 16), 0)
    for y in range(4, 12):
        for x in range(4, 12):
            target_frame.putpixel((x, y), (130, 80, 55))
            frame.putpixel((x, y), (35, 45, 35))
            mask.putpixel((x, y), 255)

    metric = _MODULE._masked_metrics(frame, mask)
    target_histograms = _MODULE._masked_histograms(target_frame, mask)
    corrected, correction = _MODULE._correct(
        frame,
        mask,
        metric,
        target_metrics=_MODULE._masked_metrics(target_frame, mask),
        color_mode="histogram_match",
        brightness_strength=1.0,
        saturation_strength=0.0,
        min_factor=0.65,
        max_factor=4.0,
        target_histograms=target_histograms,
    )

    after = _MODULE._masked_metrics(corrected, mask)
    assert correction["histogram_strength"] == 1.0
    assert after["foreground_rgb"][0] > metric["foreground_rgb"][0]
    assert after["foreground_luma"] > metric["foreground_luma"]
    assert corrected.getpixel((0, 0)) == (255, 255, 255)


def _frame(path: Path, *, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (48, 48), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 8, 32, 40), fill=color)
    image.save(path)


def _mask(path: Path) -> None:
    mask = Image.new("L", (48, 48), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((16, 8, 32, 40), fill=255)
    mask.save(path)
