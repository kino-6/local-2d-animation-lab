from __future__ import annotations

import json
from pathlib import Path

from natural_sprite_lab.motion_source import filter_motion_source_frames, load_motion_source, write_motion_source_template
from natural_sprite_lab.pose_templates import load_pose_sequence, render_pose_frame, validate_pose_frame, write_default_templates


def test_import_openpose_body25_directory_to_local_template(tmp_path: Path) -> None:
    source = tmp_path / "openpose"
    source.mkdir()
    for index, offset in enumerate((0.0, 8.0, 16.0)):
        (source / f"frame_{index:012d}_keypoints.json").write_text(
            json.dumps({"people": [{"pose_keypoints_2d": _body25_keypoints(offset)}]}),
            encoding="utf-8",
        )
    target_root = tmp_path / "target_templates"
    write_default_templates(target_root, frame_count=4, width=128, height=128)

    report = write_motion_source_template(
        source,
        tmp_path / "pose_templates",
        action="run",
        frame_count=6,
        target_template_root=target_root,
        target_template_name="run",
        render_width=128,
        render_height=128,
    )

    sequence = load_pose_sequence(tmp_path / "pose_templates", "run")
    assert report["source_frames"] == 3
    assert report["frame_count"] == 6
    assert len(sequence) == 6
    assert not validate_pose_frame(sequence[0])
    assert "confidence" in sequence[0]
    assert (tmp_path / "pose_templates" / "run" / "contact_sheet.png").exists()


def test_load_motion_source_accepts_existing_template_json(tmp_path: Path) -> None:
    source = tmp_path / "template.json"
    source.write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "action": "run",
                        "variant": "run",
                        "frame_index": 0,
                        "phase": "contact",
                        "keypoints": {name: [0.5, 0.5, 0.75] for name in _local_keypoints()},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    frames = load_motion_source(source)

    assert len(frames) == 1
    assert frames[0].confidence["nose"] == 0.75


def test_render_pose_frame_uses_confidence_weighting() -> None:
    frame = {
        "action": "run",
        "variant": "run",
        "frame_index": 0,
        "phase": "contact",
        "keypoints": {name: [0.5, 0.5] for name in _local_keypoints()},
        "confidence": {name: 0.2 for name in _local_keypoints()},
    }

    image = render_pose_frame(frame, 64, 64, style="wan_confidence_lower")

    assert image.getpixel((0, 0)) == (255, 255, 255)
    assert image.getbbox() == (0, 0, 64, 64)


def test_filter_motion_source_frames_drops_low_confidence_and_respects_range(tmp_path: Path) -> None:
    source = tmp_path / "openpose"
    source.mkdir()
    for index, confidence in enumerate((0.04, 0.7, 0.8, 0.03)):
        (source / f"frame_{index:012d}_keypoints.json").write_text(
            json.dumps({"people": [{"pose_keypoints_2d": _body25_keypoints(8.0 * index, confidence=confidence)}]}),
            encoding="utf-8",
        )

    frames = load_motion_source(source, min_confidence=0.01)
    selected = filter_motion_source_frames(
        frames,
        start_index=1,
        end_index=3,
        min_frame_mean_confidence=0.5,
    )

    assert [frame.source_index for frame in selected] == [1, 2]


def test_filter_motion_source_frames_can_drop_low_ankle_separation(tmp_path: Path) -> None:
    source = tmp_path / "openpose"
    source.mkdir()
    (source / "frame_000000000000_keypoints.json").write_text(
        json.dumps({"people": [{"pose_keypoints_2d": _body25_keypoints_with_ankles(left_ankle_x=62.0, right_ankle_x=64.0)}]}),
        encoding="utf-8",
    )
    (source / "frame_000000000001_keypoints.json").write_text(
        json.dumps({"people": [{"pose_keypoints_2d": _body25_keypoints_with_ankles(left_ankle_x=40.0, right_ankle_x=88.0)}]}),
        encoding="utf-8",
    )

    frames = load_motion_source(source)
    selected = filter_motion_source_frames(frames, min_ankle_x_separation=0.2)

    assert [frame.source_index for frame in selected] == [1]


def _body25_keypoints(offset: float, confidence: float = 0.9) -> list[float]:
    points = [(0.0, 0.0, 0.0)] * 25
    values = {
        0: (64.0 + offset, 30.0, confidence),
        1: (64.0 + offset, 46.0, confidence),
        2: (78.0 + offset, 52.0, confidence),
        3: (88.0 + offset, 72.0, confidence),
        4: (94.0 + offset, 92.0, confidence),
        5: (50.0 + offset, 52.0, confidence),
        6: (40.0 + offset, 72.0, confidence),
        7: (34.0 + offset, 92.0, confidence),
        9: (74.0 + offset, 92.0, confidence),
        10: (84.0 + offset, 126.0, confidence),
        11: (88.0 + offset, 158.0, confidence),
        12: (54.0 + offset, 92.0, confidence),
        13: (44.0 + offset, 126.0, confidence),
        14: (40.0 + offset, 158.0, confidence),
    }
    for index, point in values.items():
        points[index] = point
    return [component for point in points for component in point]


def _body25_keypoints_with_ankles(left_ankle_x: float, right_ankle_x: float) -> list[float]:
    values = _body25_keypoints(0.0)
    values[11 * 3] = right_ankle_x
    values[14 * 3] = left_ankle_x
    return values


def _local_keypoints() -> tuple[str, ...]:
    return (
        "nose",
        "neck",
        "right_shoulder",
        "right_elbow",
        "right_wrist",
        "left_shoulder",
        "left_elbow",
        "left_wrist",
        "right_hip",
        "right_knee",
        "right_ankle",
        "left_hip",
        "left_knee",
        "left_ankle",
    )
