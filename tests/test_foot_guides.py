from pathlib import Path

from natural_sprite_lab.foot_guides import render_foot_guide
from natural_sprite_lab.foot_guides import walk_foot_guide_for
from natural_sprite_lab.foot_guides import write_default_foot_guides


def test_walk_foot_guide_contains_separated_feet() -> None:
    guide = walk_foot_guide_for(15, 120)

    assert guide.action == "walk"
    left_x = guide.left_foot["center"][0]
    right_x = guide.right_foot["center"][0]
    assert abs(left_x - right_x) > 0.08
    assert guide.stride_envelope["left"] < guide.stride_envelope["right"]


def test_render_foot_guide_is_nonblank() -> None:
    guide = walk_foot_guide_for(30, 120)
    image = render_foot_guide(guide, 128, 128)

    assert image.getbbox() is not None


def test_write_default_foot_guides(tmp_path: Path) -> None:
    written = write_default_foot_guides(tmp_path / "foot_guides", frame_count=8, width=128, height=128)

    assert set(written) == {"walk"}
    assert len(written["walk"]["frames"]) == 8
    assert (tmp_path / "foot_guides" / "walk" / "frame_000.json").exists()
    assert (tmp_path / "foot_guides" / "walk" / "control" / "frame_000.png").exists()
    assert (tmp_path / "foot_guides" / "index.json").exists()
