import importlib.util
import json
from pathlib import Path

from natural_sprite_lab.pose_templates import load_pose_sequence


def test_build_synthetic_sideview_motion_source_writes_template(tmp_path: Path) -> None:
    builder = _load_builder()
    report = builder(
        output_root=tmp_path,
        template_name="run_synthetic_sideview_walk_test",
        frame_count=24,
        render_style="wan_confidence_lower",
    )

    assert report["source_frames"] == 24
    assert report["mean_confidence"] > 0.65
    template_dir = tmp_path / "run_synthetic_sideview_walk_test"
    assert (template_dir / "contact_sheet.png").exists()
    assert (template_dir / "motion_source_report.json").exists()
    frames = load_pose_sequence(tmp_path, "run_synthetic_sideview_walk_test")
    assert len(frames) == 24
    assert {frame["phase"] for frame in frames} >= {"contact", "passing", "opposite_contact", "recover"}
    separations = [
        abs(frame["keypoints"]["left_ankle"][0] - frame["keypoints"]["right_ankle"][0])
        for frame in frames
    ]
    assert min(separations) >= 0.035
    saved_report = json.loads((template_dir / "motion_source_report.json").read_text(encoding="utf-8"))
    assert saved_report["template_name"] == "run_synthetic_sideview_walk_test"


def test_build_synthetic_sideview_motion_source_can_write_alignment_report(tmp_path: Path) -> None:
    builder = _load_builder()
    target_root = tmp_path / "target"
    builder(
        output_root=target_root,
        template_name="target_walk",
        frame_count=12,
        render_style="vace_walk_lower_hint",
    )

    report = builder(
        output_root=tmp_path,
        template_name="aligned_walk",
        frame_count=12,
        render_style="vace_walk_confidence_hint",
        align_to_template_root=target_root,
        align_to_template_name="target_walk",
    )

    assert report["alignment"]["target_template_name"] == "target_walk"
    assert "max_body_scale_drift" in report["alignment"]["post_alignment"]
    saved_report = json.loads((tmp_path / "aligned_walk" / "motion_source_report.json").read_text(encoding="utf-8"))
    assert "post_alignment" in saved_report["alignment"]


def _load_builder():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_synthetic_sideview_motion_source.py"
    spec = importlib.util.spec_from_file_location("build_synthetic_sideview_motion_source", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_synthetic_sideview_motion_source
