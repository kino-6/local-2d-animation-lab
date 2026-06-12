from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

from natural_sprite_lab.pose_alignment import pose_alignment_report
from natural_sprite_lab.pose_templates import KEYPOINTS, PoseFrame, load_pose_sequence, render_pose_frame
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet


OPENPOSE_BODY25_INDEX = {
    "nose": 0,
    "neck": 1,
    "right_shoulder": 2,
    "right_elbow": 3,
    "right_wrist": 4,
    "left_shoulder": 5,
    "left_elbow": 6,
    "left_wrist": 7,
    "right_hip": 9,
    "right_knee": 10,
    "right_ankle": 11,
    "left_hip": 12,
    "left_knee": 13,
    "left_ankle": 14,
}

COCO17_INDEX = {
    "nose": 0,
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_wrist": 9,
    "right_wrist": 10,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14,
    "left_ankle": 15,
    "right_ankle": 16,
}


@dataclass(frozen=True)
class RawPoseFrame:
    keypoints: dict[str, tuple[float, float]]
    confidence: dict[str, float]
    source_index: int


def write_motion_source_template(
    source: Path,
    output_root: Path,
    *,
    action: str,
    variant: str | None = None,
    frame_count: int = 120,
    target_template_root: Path | None = None,
    target_template_name: str | None = None,
    render_width: int = 512,
    render_height: int = 512,
    render_style: str = "wan_confidence_lower",
    min_confidence: float = 0.05,
    source_start_index: int | None = None,
    source_end_index: int | None = None,
    min_frame_mean_confidence: float | None = None,
    min_ankle_x_separation: float | None = None,
) -> dict[str, Any]:
    raw_frames = load_motion_source(source, min_confidence=min_confidence)
    raw_frames = filter_motion_source_frames(
        raw_frames,
        start_index=source_start_index,
        end_index=source_end_index,
        min_frame_mean_confidence=min_frame_mean_confidence,
        min_ankle_x_separation=min_ankle_x_separation,
    )
    if not raw_frames:
        raise ValueError(f"No readable pose frames found: {source}")
    target_frame = _load_target_frame(target_template_root, target_template_name or action)
    alignment_report = _alignment_report_for_raw_frames(
        raw_frames,
        target_frame,
        action=action,
        variant=variant or action,
        min_confidence=min_confidence,
    )
    pose_frames = build_aligned_template(
        raw_frames,
        action=action,
        variant=variant or action,
        frame_count=frame_count,
        target_frame=target_frame,
        min_confidence=min_confidence,
    )

    template_name = f"{action}_{variant}" if variant and variant != action else action
    action_dir = output_root / template_name
    render_dir = action_dir / "controlnet"
    action_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)

    image_paths: list[Path] = []
    for frame in pose_frames:
        json_path = action_dir / f"frame_{frame.frame_index:03d}.json"
        image_path = render_dir / f"frame_{frame.frame_index:03d}.png"
        json_path.write_text(
            json.dumps(frame.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        render_pose_frame(frame.to_dict(), render_width, render_height, style=render_style).save(image_path)
        image_paths.append(image_path)

    contact_sheet = make_contact_sheet(image_paths, action_dir / "contact_sheet.png")
    report = {
        "status": "completed",
        "source": str(source),
        "output_template": str(action_dir),
        "template_name": template_name,
        "source_frames": len(raw_frames),
        "frame_count": len(pose_frames),
        "target_template": target_template_name or action,
        "render_style": render_style,
        "contact_sheet": str(contact_sheet),
        "mean_confidence": round(_mean_confidence(frame.confidence for frame in pose_frames), 5),
        "source_filter": {
            "start_index": source_start_index,
            "end_index": source_end_index,
            "min_frame_mean_confidence": min_frame_mean_confidence,
            "min_ankle_x_separation": min_ankle_x_separation,
            "retained_source_indices": [frame.source_index for frame in raw_frames],
        },
        "alignment": alignment_report,
    }
    (action_dir / "motion_source_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def load_motion_source(source: Path, *, min_confidence: float = 0.05) -> list[RawPoseFrame]:
    if source.is_dir():
        files = sorted(source.glob("*.json"), key=_numeric_path_key)
        frames: list[RawPoseFrame] = []
        for path in files:
            frames.extend(_frames_from_payload(json.loads(path.read_text(encoding="utf-8")), min_confidence))
        return _fill_missing_keypoints([RawPoseFrame(frame.keypoints, frame.confidence, index) for index, frame in enumerate(frames)])
    payload = json.loads(source.read_text(encoding="utf-8"))
    frames = _frames_from_payload(payload, min_confidence)
    return _fill_missing_keypoints([RawPoseFrame(frame.keypoints, frame.confidence, index) for index, frame in enumerate(frames)])


def filter_motion_source_frames(
    frames: list[RawPoseFrame],
    *,
    start_index: int | None = None,
    end_index: int | None = None,
    min_frame_mean_confidence: float | None = None,
    min_ankle_x_separation: float | None = None,
) -> list[RawPoseFrame]:
    source_width = _raw_sequence_width(frames)
    selected: list[RawPoseFrame] = []
    for frame in frames:
        if start_index is not None and frame.source_index < start_index:
            continue
        if end_index is not None and frame.source_index > end_index:
            continue
        if min_frame_mean_confidence is not None and _mean_confidence([frame.confidence]) < min_frame_mean_confidence:
            continue
        if min_ankle_x_separation is not None and _ankle_x_separation(frame, source_width) < min_ankle_x_separation:
            continue
        selected.append(frame)
    return selected


def build_aligned_template(
    raw_frames: list[RawPoseFrame],
    *,
    action: str,
    variant: str,
    frame_count: int,
    target_frame: dict[str, Any],
    min_confidence: float = 0.05,
) -> list[PoseFrame]:
    aligned = _align_sequence(raw_frames, target_frame, min_confidence=min_confidence)
    return [
        _interpolate_pose_frame(aligned, index, frame_count, action=action, variant=variant)
        for index in range(frame_count)
    ]


def _alignment_report_for_raw_frames(
    raw_frames: list[RawPoseFrame],
    target_frame: dict[str, Any],
    *,
    action: str,
    variant: str,
    min_confidence: float,
) -> dict[str, Any]:
    pre_frames = [
        PoseFrame(
            action=action,
            variant=variant,
            frame_index=index,
            phase="source",
            keypoints={name: [point[0], point[1]] for name, point in frame.keypoints.items()},
            confidence=frame.confidence,
            notes="pre_alignment",
        )
        for index, frame in enumerate(raw_frames)
    ]
    aligned = _align_sequence(raw_frames, target_frame, min_confidence=min_confidence)
    post_frames = [
        PoseFrame(
            action=action,
            variant=variant,
            frame_index=index,
            phase="source",
            keypoints={name: [point[0], point[1]] for name, point in frame.keypoints.items()},
            confidence=frame.confidence,
            notes="post_alignment",
        )
        for index, frame in enumerate(aligned)
    ]
    return {
        "pre_alignment": pose_alignment_report(pre_frames, target_frame).to_dict(),
        "post_alignment": pose_alignment_report(post_frames, target_frame).to_dict(),
    }


def _frames_from_payload(payload: Any, min_confidence: float) -> list[RawPoseFrame]:
    if isinstance(payload, list):
        return [_frame_from_any(item, index, min_confidence) for index, item in enumerate(payload)]
    if not isinstance(payload, dict):
        raise ValueError("Motion source JSON must be an object or list.")
    if isinstance(payload.get("frames"), list):
        return [_frame_from_any(item, index, min_confidence) for index, item in enumerate(payload["frames"])]
    return [_frame_from_any(payload, 0, min_confidence)]


def _frame_from_any(data: dict[str, Any], index: int, min_confidence: float) -> RawPoseFrame:
    if "keypoints" in data:
        return _frame_from_named_keypoints(data, index, min_confidence)
    if isinstance(data.get("people"), list) and data["people"]:
        person = max(data["people"], key=_person_confidence)
        if "pose_keypoints_2d" in person:
            return _frame_from_flat_keypoints(person["pose_keypoints_2d"], OPENPOSE_BODY25_INDEX, index, min_confidence)
    if "pose_keypoints_2d" in data:
        return _frame_from_flat_keypoints(data["pose_keypoints_2d"], OPENPOSE_BODY25_INDEX, index, min_confidence)
    if "coco_keypoints" in data:
        return _frame_from_flat_keypoints(data["coco_keypoints"], COCO17_INDEX, index, min_confidence, infer_neck=True)
    if "keypoints_2d" in data:
        return _frame_from_flat_keypoints(data["keypoints_2d"], COCO17_INDEX, index, min_confidence, infer_neck=True)
    raise ValueError(f"Unsupported motion source frame at index {index}.")


def _frame_from_named_keypoints(data: dict[str, Any], index: int, min_confidence: float) -> RawPoseFrame:
    keypoints: dict[str, tuple[float, float]] = {}
    confidence: dict[str, float] = {}
    explicit_confidence = data.get("confidence") if isinstance(data.get("confidence"), dict) else {}
    for name in KEYPOINTS:
        point = data["keypoints"].get(name)
        if not isinstance(point, list | tuple) or len(point) < 2:
            continue
        value = float(explicit_confidence.get(name, point[2] if len(point) > 2 else 1.0))
        if value < min_confidence:
            continue
        keypoints[name] = (float(point[0]), float(point[1]))
        confidence[name] = max(0.0, min(1.0, value))
    return _complete_frame(keypoints, confidence, index)


def _frame_from_flat_keypoints(
    values: list[int | float],
    mapping: dict[str, int],
    index: int,
    min_confidence: float,
    *,
    infer_neck: bool = False,
) -> RawPoseFrame:
    keypoints: dict[str, tuple[float, float]] = {}
    confidence: dict[str, float] = {}
    for name, source_index in mapping.items():
        offset = source_index * 3
        if offset + 2 >= len(values):
            continue
        x, y, conf = float(values[offset]), float(values[offset + 1]), float(values[offset + 2])
        if conf < min_confidence or (x == 0.0 and y == 0.0):
            continue
        keypoints[name] = (x, y)
        confidence[name] = max(0.0, min(1.0, conf))
    if infer_neck and "neck" not in keypoints and {"left_shoulder", "right_shoulder"} <= keypoints.keys():
        left = keypoints["left_shoulder"]
        right = keypoints["right_shoulder"]
        keypoints["neck"] = ((left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0)
        confidence["neck"] = min(confidence["left_shoulder"], confidence["right_shoulder"])
    return _complete_frame(keypoints, confidence, index)


def _complete_frame(
    keypoints: dict[str, tuple[float, float]],
    confidence: dict[str, float],
    index: int,
) -> RawPoseFrame:
    if "neck" not in keypoints and {"left_shoulder", "right_shoulder"} <= keypoints.keys():
        left = keypoints["left_shoulder"]
        right = keypoints["right_shoulder"]
        keypoints["neck"] = ((left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0)
        confidence["neck"] = min(confidence.get("left_shoulder", 1.0), confidence.get("right_shoulder", 1.0))
    return RawPoseFrame(keypoints=keypoints, confidence=confidence, source_index=index)


def _fill_missing_keypoints(frames: list[RawPoseFrame]) -> list[RawPoseFrame]:
    repaired: list[RawPoseFrame] = []
    for index, frame in enumerate(frames):
        keypoints = dict(frame.keypoints)
        confidence = dict(frame.confidence)
        for name in KEYPOINTS:
            if name in keypoints:
                continue
            replacement = _nearest_keypoint(frames, index, name)
            if replacement is None:
                raise ValueError(f"Motion source is missing keypoint in every frame: {name}")
            point, value = replacement
            keypoints[name] = point
            confidence[name] = round(value * 0.5, 6)
        repaired.append(RawPoseFrame(keypoints, confidence, frame.source_index))
    return repaired


def _nearest_keypoint(
    frames: list[RawPoseFrame],
    index: int,
    name: str,
) -> tuple[tuple[float, float], float] | None:
    for distance in range(1, len(frames) + 1):
        for candidate_index in (index - distance, index + distance):
            if 0 <= candidate_index < len(frames) and name in frames[candidate_index].keypoints:
                frame = frames[candidate_index]
                return frame.keypoints[name], frame.confidence.get(name, 0.0)
    return None


def _align_sequence(
    raw_frames: list[RawPoseFrame],
    target_frame: dict[str, Any],
    *,
    min_confidence: float,
) -> list[RawPoseFrame]:
    source_box = _sequence_box(raw_frames, min_confidence=min_confidence)
    target_box = _point_box(
        {
            name: (float(point[0]), float(point[1]))
            for name, point in target_frame["keypoints"].items()
            if name in KEYPOINTS
        }
    )
    source_width = max(1e-6, source_box[2] - source_box[0])
    source_height = max(1e-6, source_box[3] - source_box[1])
    target_width = max(1e-6, target_box[2] - target_box[0])
    target_height = max(1e-6, target_box[3] - target_box[1])
    scale = min(target_width / source_width, target_height / source_height)
    source_bottom_center = ((source_box[0] + source_box[2]) / 2.0, source_box[3])
    target_bottom_center = ((target_box[0] + target_box[2]) / 2.0, target_box[3])
    aligned: list[RawPoseFrame] = []
    for frame in raw_frames:
        points: dict[str, tuple[float, float]] = {}
        for name, point in frame.keypoints.items():
            x = target_bottom_center[0] + (point[0] - source_bottom_center[0]) * scale
            y = target_bottom_center[1] + (point[1] - source_bottom_center[1]) * scale
            points[name] = (_clamp01(x), _clamp01(y))
        aligned.append(RawPoseFrame(points, frame.confidence, frame.source_index))
    return aligned


def _interpolate_pose_frame(
    frames: list[RawPoseFrame],
    index: int,
    frame_count: int,
    *,
    action: str,
    variant: str,
) -> PoseFrame:
    if frame_count <= 1 or len(frames) == 1:
        source_position = 0.0
    else:
        source_position = index * (len(frames) - 1) / (frame_count - 1)
    left_index = int(source_position)
    right_index = min(len(frames) - 1, left_index + 1)
    amount = source_position - left_index
    left = frames[left_index]
    right = frames[right_index]
    keypoints: dict[str, list[float]] = {}
    confidence: dict[str, float] = {}
    for name in KEYPOINTS:
        lx, ly = left.keypoints[name]
        rx, ry = right.keypoints[name]
        keypoints[name] = [
            round(lx * (1.0 - amount) + rx * amount, 6),
            round(ly * (1.0 - amount) + ry * amount, 6),
        ]
        confidence[name] = round(
            left.confidence.get(name, 1.0) * (1.0 - amount) + right.confidence.get(name, 1.0) * amount,
            6,
        )
    phase = _phase_name(action, index / max(1, frame_count - 1))
    return PoseFrame(
        action=action,
        variant=variant,
        frame_index=index,
        phase=phase,
        keypoints=keypoints,
        confidence=confidence,
        notes=f"motion_source {phase}",
    )


def _load_target_frame(target_root: Path | None, template_name: str) -> dict[str, Any]:
    if target_root is not None and (target_root / template_name).exists():
        return load_pose_sequence(target_root, template_name)[0]
    return {
        "keypoints": {
            "nose": [0.50, 0.20],
            "neck": [0.50, 0.31],
            "right_shoulder": [0.58, 0.35],
            "right_elbow": [0.64, 0.48],
            "right_wrist": [0.68, 0.60],
            "left_shoulder": [0.42, 0.35],
            "left_elbow": [0.36, 0.48],
            "left_wrist": [0.32, 0.60],
            "right_hip": [0.55, 0.57],
            "right_knee": [0.60, 0.74],
            "right_ankle": [0.63, 0.89],
            "left_hip": [0.45, 0.57],
            "left_knee": [0.40, 0.74],
            "left_ankle": [0.37, 0.89],
        }
    }


def _sequence_box(frames: list[RawPoseFrame], *, min_confidence: float) -> tuple[float, float, float, float]:
    points = [
        point
        for frame in frames
        for name, point in frame.keypoints.items()
        if frame.confidence.get(name, 1.0) >= min_confidence
    ]
    return _point_box(dict(enumerate(points)))


def _point_box(points: dict[Any, tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points.values()]
    ys = [point[1] for point in points.values()]
    return (min(xs), min(ys), max(xs), max(ys))


def _raw_sequence_width(frames: list[RawPoseFrame]) -> float:
    if not frames:
        return 1.0
    xs = [point[0] for frame in frames for point in frame.keypoints.values()]
    return max(1e-6, max(xs) - min(xs))


def _ankle_x_separation(frame: RawPoseFrame, source_width: float) -> float:
    left = frame.keypoints.get("left_ankle")
    right = frame.keypoints.get("right_ankle")
    if left is None or right is None:
        return 0.0
    return abs(left[0] - right[0]) / max(1e-6, source_width)


def _phase_name(action: str, t: float) -> str:
    if action == "run":
        return ["contact", "drive", "flight", "recover"][min(3, int(t * 4))]
    if action == "walk":
        return ["contact", "down", "passing", "up"][min(3, int(t * 4))]
    return ["motion_0", "motion_1", "motion_2", "motion_3"][min(3, int(t * 4))]


def _mean_confidence(values: Iterable[dict[str, float]]) -> float:
    flattened = [value for item in values for value in item.values()]
    return sum(flattened) / len(flattened) if flattened else 0.0


def _person_confidence(person: dict[str, Any]) -> float:
    values = person.get("pose_keypoints_2d", [])
    if not isinstance(values, list):
        return 0.0
    confidences = [float(values[index]) for index in range(2, len(values), 3)]
    return sum(confidences) / len(confidences) if confidences else 0.0


def _numeric_path_key(path: Path) -> tuple[int, str]:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return (int(digits[-1]) if digits else -1, path.name)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def write_debug_contact_sheet(frame_paths: list[Path], output: Path) -> Path:
    images = [Image.open(path).convert("RGB") for path in frame_paths]
    if not images:
        raise ValueError("No frames for debug contact sheet.")
    return make_contact_sheet(frame_paths, output)
