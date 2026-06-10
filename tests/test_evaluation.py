from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from natural_sprite_lab.evaluation import evaluate_animation


def _frame(path: Path, rects: list[tuple[int, int, int, int]], color: tuple[int, int, int] = (60, 80, 180)) -> Path:
    image = Image.new("RGBA", (96, 96), (250, 250, 250, 255))
    for left, top, right, bottom in rects:
        for y in range(top, bottom):
            for x in range(left, right):
                if 0 <= x < image.width and 0 <= y < image.height:
                    image.putpixel((x, y), (*color, 255))
    image.save(path)
    return path


def _spec(action: str, variant: str | None = None, active: bool = True) -> SimpleNamespace:
    tags = ["active_frame"] if active and action == "attack" else []
    if active and action == "hit":
        tags = ["reaction_frame"]
    return SimpleNamespace(
        action=action,
        frame_plan=[
            {
                "action_variant": variant or action,
                "semantic_tags": tags,
                "game_events": [{"type": "attack_active"}] if tags and action == "attack" else [],
            }
        ]
        * 4,
        director_metadata={},
    )


def test_evaluation_detects_foreground_and_background_issues(tmp_path: Path) -> None:
    paths = [
        _frame(tmp_path / "f0.png", [(1, 1, 11, 11), (30, 30, 40, 40), (60, 60, 70, 70)]),
        _frame(tmp_path / "f1.png", [(1, 1, 11, 11), (30, 30, 40, 40), (60, 60, 70, 70)]),
        _frame(tmp_path / "f2.png", [(1, 1, 11, 11), (30, 30, 40, 40), (60, 60, 70, 70)]),
        _frame(tmp_path / "f3.png", [(1, 1, 11, 11), (30, 30, 40, 40), (60, 60, 70, 70)]),
    ]

    report = evaluate_animation(paths)

    assert "missing_or_tiny_foreground" in report["issue_codes"]
    assert "multiple_or_fragmented_foreground" in report["issue_codes"]
    assert "background_contamination" in report["issue_codes"]


def test_evaluation_detects_motion_drift_loop_and_color_issues(tmp_path: Path) -> None:
    paths = [
        _frame(tmp_path / "f0.png", [(4, 34, 44, 54)], (30, 40, 190)),
        _frame(tmp_path / "f1.png", [(18, 4, 62, 92)], (220, 30, 30)),
        _frame(tmp_path / "f2.png", [(34, 36, 76, 58)], (30, 200, 70)),
        _frame(tmp_path / "f3.png", [(52, 4, 92, 92)], (220, 220, 30)),
    ]

    report = evaluate_animation(paths, spec=_spec("walk"))

    assert "center_drift" in report["issue_codes"]
    assert "scale_drift" in report["issue_codes"]
    assert "color_drift" in report["issue_codes"]
    assert "weak_loop_closure" in report["issue_codes"]


def test_evaluation_detects_weak_motion_and_action_mismatch(tmp_path: Path) -> None:
    paths = [_frame(tmp_path / f"f{index}.png", [(28, 16, 68, 88)]) for index in range(4)]

    report = evaluate_animation(paths, spec=_spec("attack", "sword"), backend_metadata={"pose_template_name": "hit_heavy"})

    assert "weak_motion" in report["issue_codes"]
    assert "weak_attack_motion" in report["issue_codes"]
    assert "pose_action_mismatch" in report["issue_codes"]


def test_evaluation_detects_weapon_bow_and_hit_specific_issues(tmp_path: Path) -> None:
    paths = [_frame(tmp_path / f"f{index}.png", [(28, 16, 68, 88)]) for index in range(4)]

    bow = evaluate_animation(paths, spec=_spec("attack", "bow", active=False))
    hit = evaluate_animation(paths, spec=_spec("hit", "heavy", active=True))

    assert "bow_phase_missing" in bow["issue_codes"]
    assert "bow_string_arrow_breakage_likely" in bow["issue_codes"]
    assert "weak_hit_recoil" in hit["issue_codes"]
