from pathlib import Path

from natural_sprite_lab.pose_templates import load_pose_sequence, render_pose_frame, validate_pose_frame, write_default_templates


def test_write_and_load_default_pose_templates(tmp_path: Path) -> None:
    root = tmp_path / "pose_templates"
    written = write_default_templates(root, frame_count=120, width=128, height=128)

    assert "attack_sword" in written
    sequence = load_pose_sequence(root, "attack_sword")
    assert len(sequence) == 120
    assert sequence[0]["action"] == "attack"
    assert sequence[0]["variant"] == "sword"
    assert not validate_pose_frame(sequence[0])
    assert (root / "attack_sword" / "contact_sheet.png").exists()


def test_render_pose_frame_is_controlnet_image(tmp_path: Path) -> None:
    root = tmp_path / "pose_templates"
    write_default_templates(root, frame_count=4, width=128, height=128)
    frame = load_pose_sequence(root, "hit_knockback")[2]
    image = render_pose_frame(frame, 128, 128)

    assert image.size == (128, 128)
    assert image.getbbox() is not None


def test_load_pose_sequence_uses_numeric_order(tmp_path: Path) -> None:
    root = tmp_path / "pose_templates"
    write_default_templates(root, frame_count=12, width=64, height=64)

    sequence = load_pose_sequence(root, "walk")

    assert [frame["frame_index"] for frame in sequence] == list(range(12))
