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
        leg_side_offset=0.09,
    )

    assert report["source_frames"] == 24
    assert report["mean_confidence"] > 0.65
    assert report["motion_diagnostics"]["passes_min_ankle_x_separation"]
    assert report["motion_diagnostics"]["passes_foot_box_separation"]
    assert report["motion_diagnostics"]["sampled_min_foot_box_x_gap"] >= 0.012
    assert report["motion_diagnostics"]["contact_counts"]["left"] > 0
    assert report["motion_diagnostics"]["contact_counts"]["right"] > 0
    assert report["motion_diagnostics"]["sampled_indices"] == [0, 3, 6, 9, 12, 15, 18, 21]
    template_dir = tmp_path / "run_synthetic_sideview_walk_test"
    assert (template_dir / "contact_sheet.png").exists()
    assert (template_dir / "lower_body_sidecar_contact_sheet.png").exists()
    assert (template_dir / "motion_source_report.json").exists()
    assert (template_dir / "lower_body_sidecar" / "frame_000.png").exists()
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
    assert saved_report["motion_diagnostics"]["unclear_ankle_separation_count"] == 0
    first_frame = json.loads((template_dir / "frame_000.json").read_text(encoding="utf-8"))
    assert first_frame["foot_contact"]["ground_y"] == 0.86
    assert first_frame["foot_contact"]["left_foot"]["toe"][0] > first_frame["foot_contact"]["left_foot"]["heel"][0]
    assert first_frame["foot_contact"]["right_foot"]["box"][0] < first_frame["foot_contact"]["right_foot"]["box"][2]


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


def test_build_synthetic_sideview_motion_source_records_arm_swing_scale(tmp_path: Path) -> None:
    builder = _load_builder()
    report = builder(
        output_root=tmp_path,
        template_name="calm_arm_walk",
        frame_count=16,
        arm_swing_scale=0.35,
        leg_side_offset=0.08,
    )

    assert report["settings"]["arm_swing_scale"] == 0.35
    assert report["settings"]["leg_side_offset"] == 0.08
    frames = load_pose_sequence(tmp_path, "calm_arm_walk")
    wrist_x_values = [frame["keypoints"]["left_wrist"][0] for frame in frames]
    assert max(wrist_x_values) - min(wrist_x_values) < 0.07


def test_lower_body_sidecar_renderer_is_nonblank(tmp_path: Path) -> None:
    module = _load_module()
    frame = module.synthetic_sideview_frame(
        0,
        8,
        action="walk",
        variant="sidecar_test",
        stride=0.14,
        lift=0.07,
        body_bob=0.012,
        arm_swing_scale=0.35,
        leg_side_offset=0.09,
    ).to_dict()

    image = module.render_lower_body_sidecar(frame, 128, 128)

    assert image.getbbox() is not None
    assert image.getpixel((64, round(frame["foot_contact"]["ground_y"] * 128))) != (255, 255, 255)


def _load_builder():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_synthetic_sideview_motion_source.py"
    spec = importlib.util.spec_from_file_location("build_synthetic_sideview_motion_source", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_synthetic_sideview_motion_source


def _load_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_synthetic_sideview_motion_source.py"
    spec = importlib.util.spec_from_file_location("build_synthetic_sideview_motion_source", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
