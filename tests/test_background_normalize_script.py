from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "normalize_connected_background.py"
_SPEC = importlib.util.spec_from_file_location("normalize_connected_background", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

normalize_frame_background = _MODULE.normalize_frame_background


def test_normalize_frame_background_whitens_border_connected_background(tmp_path: Path) -> None:
    frame = tmp_path / "frame.png"
    output = tmp_path / "out.png"
    mask = tmp_path / "mask.png"
    image = Image.new("RGB", (32, 32), (150, 165, 180))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 6, 19, 27), fill=(20, 35, 80))
    draw.rectangle((14, 10, 17, 22), fill=(230, 205, 185))
    image.save(frame)

    report = normalize_frame_background(
        frame,
        output,
        mask,
        distance_threshold=80,
        protect_threshold=100,
        protect_grow=2,
    )

    normalized = Image.open(output).convert("RGB")
    assert normalized.getpixel((0, 0)) == (255, 255, 255)
    assert normalized.getpixel((15, 12)) == (230, 205, 185)
    assert report["changed_coverage"] > 0.6


def test_normalize_frame_background_does_not_fill_enclosed_hole(tmp_path: Path) -> None:
    frame = tmp_path / "frame.png"
    output = tmp_path / "out.png"
    mask = tmp_path / "mask.png"
    image = Image.new("RGB", (32, 32), (150, 165, 180))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 23, 23), fill=(20, 35, 80))
    draw.rectangle((13, 13, 18, 18), fill=(150, 165, 180))
    image.save(frame)

    normalize_frame_background(
        frame,
        output,
        mask,
        distance_threshold=80,
        protect_threshold=100,
        protect_grow=1,
    )

    normalized = Image.open(output).convert("RGB")
    assert normalized.getpixel((0, 0)) == (255, 255, 255)
    assert normalized.getpixel((15, 15)) == (150, 165, 180)
