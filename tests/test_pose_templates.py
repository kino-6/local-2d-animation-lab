from pathlib import Path

from natural_sprite_lab.pose_templates import load_pose_sequence, render_pose_frame, validate_pose_frame, write_default_templates


def test_write_and_load_default_pose_templates(tmp_path: Path) -> None:
    root = tmp_path / "pose_templates"
    written = write_default_templates(root, frame_count=120, width=128, height=128)

    assert "attack_sword" in written
    assert "run" in written
    sequence = load_pose_sequence(root, "attack_sword")
    assert len(sequence) == 120
    assert sequence[0]["action"] == "attack"
    assert sequence[0]["variant"] == "sword"
    assert not validate_pose_frame(sequence[0])
    assert (root / "attack_sword" / "contact_sheet.png").exists()
    run_sequence = load_pose_sequence(root, "run")
    assert len(run_sequence) == 120
    assert {frame["phase"] for frame in run_sequence} >= {"contact", "drive", "flight", "recover"}


def test_render_pose_frame_is_controlnet_image(tmp_path: Path) -> None:
    root = tmp_path / "pose_templates"
    write_default_templates(root, frame_count=4, width=128, height=128)
    frame = load_pose_sequence(root, "hit_knockback")[2]
    image = render_pose_frame(frame, 128, 128)

    assert image.size == (128, 128)
    assert image.getbbox() is not None


def test_render_pose_frame_supports_wan_styles(tmp_path: Path) -> None:
    root = tmp_path / "pose_templates"
    write_default_templates(root, frame_count=4, width=128, height=128)
    frame = load_pose_sequence(root, "run")[1]

    wan_line = render_pose_frame(frame, 128, 128, style="wan_line")
    wan_lower = render_pose_frame(frame, 128, 128, style="wan_lower")
    wan_balanced = render_pose_frame(frame, 128, 128, style="wan_balanced")
    vace_depth_proxy = render_pose_frame(frame, 128, 128, style="vace_depth_proxy")
    vace_side_proxy = render_pose_frame(frame, 128, 128, style="vace_side_proxy")

    assert wan_line.getpixel((0, 0)) == (255, 255, 255)
    assert wan_lower.getpixel((0, 0)) == (255, 255, 255)
    assert wan_balanced.getpixel((0, 0)) == (255, 255, 255)
    assert vace_depth_proxy.getpixel((0, 0)) == (255, 255, 255)
    assert vace_side_proxy.getpixel((0, 0)) == (255, 255, 255)
    assert wan_line.getbbox() == (0, 0, 128, 128)
    assert _non_white_pixels(wan_balanced) > 0
    assert _non_white_pixels(vace_depth_proxy) > _non_white_pixels(wan_balanced)
    assert _non_white_pixels(vace_side_proxy) > _non_white_pixels(wan_balanced)
    assert wan_balanced.tobytes() != wan_line.tobytes()
    assert vace_side_proxy.tobytes() != vace_depth_proxy.tobytes()


def test_render_pose_frame_supports_thin_controlnet_style(tmp_path: Path) -> None:
    root = tmp_path / "pose_templates"
    write_default_templates(root, frame_count=4, width=128, height=128)
    frame = load_pose_sequence(root, "run")[1]

    thick = render_pose_frame(frame, 128, 128, style="controlnet")
    thin = render_pose_frame(frame, 128, 128, style="controlnet_thin")

    assert thin.getpixel((0, 0)) == (0, 0, 0)
    assert _non_black_pixels(thin) < _non_black_pixels(thick)


def test_load_pose_sequence_uses_numeric_order(tmp_path: Path) -> None:
    root = tmp_path / "pose_templates"
    write_default_templates(root, frame_count=12, width=64, height=64)

    sequence = load_pose_sequence(root, "walk")

    assert [frame["frame_index"] for frame in sequence] == list(range(12))


def _non_black_pixels(image) -> int:
    data = image.convert("RGB").tobytes()
    return sum(1 for index in range(0, len(data), 3) if data[index : index + 3] != b"\x00\x00\x00")


def _non_white_pixels(image) -> int:
    data = image.convert("RGB").tobytes()
    return sum(1 for index in range(0, len(data), 3) if data[index : index + 3] != b"\xff\xff\xff")
