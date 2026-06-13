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


def test_prepare_clean_start_frame_rejects_possible_back_view_when_profile_required(tmp_path: Path) -> None:
    source = tmp_path / "back.png"
    output = tmp_path / "cleaned.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((104, 24, 152, 76), fill=(70, 38, 22))
    draw.rectangle((104, 76, 152, 208), fill=(20, 40, 95))
    image.save(source)

    report = prepare_clean_start_frame(source, output, width=256, height=256, require_profile_detail=True)

    assert report.status == "rejected"
    assert "possible_back_view_or_missing_profile_detail" in report.issue_codes


def test_prepare_clean_start_frame_rejects_guide_residue(tmp_path: Path) -> None:
    source = tmp_path / "guide.png"
    output = tmp_path / "cleaned.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((112, 24, 146, 58), fill=(230, 190, 150))
    draw.rectangle((108, 58, 150, 208), fill=(20, 40, 95))
    draw.line((0, 250, 255, 250), fill=(255, 0, 0), width=3)
    image.save(source)

    report = prepare_clean_start_frame(source, output, width=256, height=256)

    assert report.status == "rejected"
    assert "guide_or_panel_residue" in report.issue_codes


def test_prepare_clean_start_frame_accepts_separated_walk_ready_feet(tmp_path: Path) -> None:
    source = tmp_path / "walk_ready.png"
    output = tmp_path / "cleaned.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((114, 28, 144, 58), fill=(230, 190, 150))
    draw.rectangle((124, 56, 134, 62), fill=(230, 190, 150))
    draw.rectangle((108, 60, 150, 124), fill=(20, 40, 95))
    draw.rectangle((112, 120, 150, 138), fill=(20, 40, 95))
    draw.rectangle((112, 132, 124, 210), fill=(32, 32, 36))
    draw.rectangle((138, 132, 150, 210), fill=(32, 32, 36))
    draw.ellipse((98, 204, 128, 224), fill=(40, 42, 46))
    draw.ellipse((136, 204, 166, 224), fill=(40, 42, 46))
    image.save(source)

    report = prepare_clean_start_frame(source, output, width=256, height=256, require_lower_body_readiness=True)

    assert report.status == "prepared"
    assert "feet_not_separated" not in report.issue_codes
    assert report.lower_body_readiness["foot_component_count"] >= 2
    assert report.lower_body_readiness["foot_separation_ratio"] >= 0.18


def test_prepare_clean_start_frame_rejects_merged_or_hidden_feet(tmp_path: Path) -> None:
    source = tmp_path / "merged_feet.png"
    output = tmp_path / "cleaned.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((114, 28, 144, 58), fill=(230, 190, 150))
    draw.rectangle((104, 60, 154, 210), fill=(20, 40, 95))
    draw.ellipse((106, 204, 154, 224), fill=(40, 42, 46))
    image.save(source)

    report = prepare_clean_start_frame(source, output, width=256, height=256, require_lower_body_readiness=True)

    assert report.status == "rejected"
    assert "feet_not_separated" in report.issue_codes
    assert "lower_legs_occluded" in report.issue_codes


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
