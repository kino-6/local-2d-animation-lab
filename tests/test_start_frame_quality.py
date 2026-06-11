from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from natural_sprite_lab.quality.start_frame import make_character_mask, prepare_clean_start_frame


def test_prepare_clean_start_frame_removes_extra_character(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "cleaned.png"
    image = Image.new("RGB", (512, 512), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((170, 40, 350, 480), fill=(30, 70, 130))
    draw.rectangle((34, 40, 96, 150), fill=(120, 70, 30))
    image.save(source)

    report = prepare_clean_start_frame(source, output, width=256, height=256)

    assert output.exists()
    assert report.status == "prepared_with_warnings"
    assert "extra_foreground_components_removed" in report.issue_codes
    assert report.component_count == 2
    cleaned = Image.open(output).convert("RGB")
    assert cleaned.size == (256, 256)
    assert cleaned.getbbox() is not None


def test_prepare_clean_start_frame_rejects_empty_input(tmp_path: Path) -> None:
    source = tmp_path / "empty.png"
    output = tmp_path / "cleaned.png"
    Image.new("RGB", (128, 128), (255, 255, 255)).save(source)

    report = prepare_clean_start_frame(source, output, width=128, height=128)

    assert report.status == "rejected"
    assert "missing_foreground" in report.issue_codes


def test_make_character_mask_keeps_foreground(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "mask.png"
    image = Image.new("RGB", (128, 128), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 20, 90, 116), fill=(20, 70, 140))
    image.save(source)

    make_character_mask(source, output, grow=0, blur_radius=0)

    mask = Image.open(output).convert("L")
    assert mask.getpixel((60, 60)) == 255
    assert mask.getpixel((4, 4)) == 0
