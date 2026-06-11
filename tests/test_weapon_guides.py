from pathlib import Path

from natural_sprite_lab.weapon_guides import render_weapon_guide
from natural_sprite_lab.weapon_guides import weapon_guide_for
from natural_sprite_lab.weapon_guides import write_default_weapon_guides


def test_weapon_guide_frame_contains_expected_controls() -> None:
    sword = weapon_guide_for("sword", index=48, count=120)
    bow = weapon_guide_for("bow", index=30, count=120)

    assert sword.weapon == "sword"
    assert sword.lines
    assert "main_hand" in sword.anchors
    assert bow.weapon == "bow"
    assert {"bow_top", "bow_bottom", "draw_hand", "arrow_tip"} <= set(bow.anchors)


def test_render_weapon_guide_is_nonblank() -> None:
    guide = weapon_guide_for("axe", index=50, count=120)
    image = render_weapon_guide(guide, 128, 128)

    assert image.getbbox() is not None


def test_write_default_weapon_guides(tmp_path: Path) -> None:
    written = write_default_weapon_guides(tmp_path / "weapon_guides", frame_count=8, width=128, height=128)

    assert set(written) == {"sword", "axe", "bow"}
    assert (tmp_path / "weapon_guides" / "sword" / "frame_000.json").exists()
    assert (tmp_path / "weapon_guides" / "sword" / "control" / "frame_000.png").exists()
    assert (tmp_path / "weapon_guides" / "index.json").exists()
