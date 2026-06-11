from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "person_cutout_background.py"
_SPEC = importlib.util.spec_from_file_location("person_cutout_background", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

cutout_background_frame = _MODULE.cutout_background_frame


def test_cutout_background_frame_keeps_main_subject_and_whitens_background(tmp_path: Path) -> None:
    frame = tmp_path / "frame.png"
    output = tmp_path / "out.png"
    mask = tmp_path / "mask.png"
    image = Image.new("RGB", (40, 40), (150, 165, 180))
    draw = ImageDraw.Draw(image)
    draw.rectangle((14, 6, 24, 34), fill=(25, 45, 90))
    draw.rectangle((16, 10, 21, 22), fill=(225, 198, 178))
    image.save(frame)

    report = cutout_background_frame(frame, output, mask, subject_threshold=90, grow=2, blur=0)

    result = Image.open(output).convert("RGB")
    assert result.getpixel((0, 0)) == (255, 255, 255)
    assert result.getpixel((18, 14)) == (225, 198, 178)
    assert 0.05 < report["person_coverage"] < 0.5


def test_cutout_background_frame_drops_separate_background_artifact(tmp_path: Path) -> None:
    frame = tmp_path / "frame.png"
    output = tmp_path / "out.png"
    mask = tmp_path / "mask.png"
    image = Image.new("RGB", (40, 40), (150, 165, 180))
    draw = ImageDraw.Draw(image)
    draw.rectangle((14, 6, 24, 34), fill=(25, 45, 90))
    draw.rectangle((2, 30, 6, 36), fill=(40, 50, 70))
    image.save(frame)

    cutout_background_frame(frame, output, mask, subject_threshold=90, grow=1, blur=0)

    result = Image.open(output).convert("RGB")
    assert result.getpixel((4, 33)) == (255, 255, 255)
