from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from natural_sprite_lab.pose_templates import KEYPOINTS, PoseFrame


@dataclass(frozen=True)
class PoseFrameMetrics:
    bbox: tuple[float, float, float, float]
    body_height: float
    body_width: float
    hip_y: float
    shoulder_width: float
    ankle_baseline_y: float
    ankle_separation: float
    facing: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bbox"] = list(self.bbox)
        return data


@dataclass(frozen=True)
class PoseAlignmentReport:
    target: PoseFrameMetrics
    mean: PoseFrameMetrics
    max_body_scale_drift: float
    max_hip_y_drift: float
    max_ankle_baseline_drift: float
    max_ankle_separation_drift: float
    facing_mismatch_frames: int
    status: str
    issue_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target.to_dict(),
            "mean": self.mean.to_dict(),
            "max_body_scale_drift": self.max_body_scale_drift,
            "max_hip_y_drift": self.max_hip_y_drift,
            "max_ankle_baseline_drift": self.max_ankle_baseline_drift,
            "max_ankle_separation_drift": self.max_ankle_separation_drift,
            "facing_mismatch_frames": self.facing_mismatch_frames,
            "status": self.status,
            "issue_codes": list(self.issue_codes),
        }


def align_pose_frames_to_target(frames: list[PoseFrame], target_frame: dict[str, Any]) -> list[PoseFrame]:
    if not frames:
        return []
    target_metrics = pose_frame_metrics(target_frame)
    sequence_box = _sequence_bbox([frame.to_dict() for frame in frames])
    source_width = max(1e-6, sequence_box[2] - sequence_box[0])
    source_height = max(1e-6, sequence_box[3] - sequence_box[1])
    scale = min(target_metrics.body_width / source_width, target_metrics.body_height / source_height)
    source_bottom_center = ((sequence_box[0] + sequence_box[2]) / 2.0, sequence_box[3])
    target_bottom_center = (
        (target_metrics.bbox[0] + target_metrics.bbox[2]) / 2.0,
        target_metrics.bbox[3],
    )
    aligned: list[PoseFrame] = []
    for frame in frames:
        keypoints: dict[str, list[float]] = {}
        for name, point in frame.keypoints.items():
            x = target_bottom_center[0] + (float(point[0]) - source_bottom_center[0]) * scale
            y = target_bottom_center[1] + (float(point[1]) - source_bottom_center[1]) * scale
            keypoints[name] = [_clamp01(x), _clamp01(y)]
        aligned.append(
            PoseFrame(
                action=frame.action,
                variant=frame.variant,
                frame_index=frame.frame_index,
                phase=frame.phase,
                keypoints=keypoints,
                confidence=frame.confidence,
                notes=f"{frame.notes}; aligned_to_target".strip("; "),
            )
        )
    return aligned


def pose_alignment_report(
    frames: list[dict[str, Any] | PoseFrame],
    target_frame: dict[str, Any],
    *,
    max_body_scale_drift: float = 0.16,
    max_ankle_baseline_drift: float = 0.055,
) -> PoseAlignmentReport:
    frame_dicts = [frame.to_dict() if isinstance(frame, PoseFrame) else frame for frame in frames]
    target = pose_frame_metrics(target_frame)
    metrics = [pose_frame_metrics(frame) for frame in frame_dicts]
    mean_metrics = _mean_metrics(metrics)
    sequence_box = _sequence_bbox(frame_dicts)
    sequence_body_height = sequence_box[3] - sequence_box[1]
    body_scale_drift = abs(sequence_body_height - target.body_height) / max(1e-6, target.body_height)
    hip_drifts = [abs(metric.hip_y - target.hip_y) for metric in metrics]
    ankle_baseline_drifts = [
        abs(metric.ankle_baseline_y - target.ankle_baseline_y)
        for metric in metrics
    ]
    ankle_separation_drifts = [
        abs(metric.ankle_separation - target.ankle_separation)
        for metric in metrics
    ]
    facing_mismatch_frames = sum(1 for metric in metrics if metric.facing != target.facing)
    issue_codes: list[str] = []
    max_scale = round(body_scale_drift, 5)
    max_baseline = round(max(ankle_baseline_drifts, default=0.0), 5)
    if max_scale > max_body_scale_drift:
        issue_codes.append("body_scale_alignment_drift_high")
    if max_baseline > max_ankle_baseline_drift:
        issue_codes.append("ankle_baseline_alignment_drift_high")
    if facing_mismatch_frames:
        issue_codes.append("facing_direction_mismatch")
    return PoseAlignmentReport(
        target=target,
        mean=mean_metrics,
        max_body_scale_drift=max_scale,
        max_hip_y_drift=round(max(hip_drifts, default=0.0), 5),
        max_ankle_baseline_drift=max_baseline,
        max_ankle_separation_drift=round(max(ankle_separation_drifts, default=0.0), 5),
        facing_mismatch_frames=facing_mismatch_frames,
        status="needs_realign_or_reject" if issue_codes else "aligned",
        issue_codes=tuple(issue_codes),
    )


def pose_frame_metrics(frame: dict[str, Any]) -> PoseFrameMetrics:
    points = {
        name: (float(point[0]), float(point[1]))
        for name, point in frame["keypoints"].items()
        if name in KEYPOINTS
    }
    bbox = _point_bbox(points)
    body_height = bbox[3] - bbox[1]
    body_width = bbox[2] - bbox[0]
    hip_y = _point_mean(points, "left_hip", "right_hip", axis=1)
    shoulder_width = abs(points["left_shoulder"][0] - points["right_shoulder"][0])
    ankle_baseline_y = max(points["left_ankle"][1], points["right_ankle"][1])
    ankle_separation = abs(points["left_ankle"][0] - points["right_ankle"][0])
    facing = "right" if points["nose"][0] >= points["neck"][0] else "left"
    return PoseFrameMetrics(
        bbox=tuple(round(value, 6) for value in bbox),
        body_height=round(body_height, 6),
        body_width=round(body_width, 6),
        hip_y=round(hip_y, 6),
        shoulder_width=round(shoulder_width, 6),
        ankle_baseline_y=round(ankle_baseline_y, 6),
        ankle_separation=round(ankle_separation, 6),
        facing=facing,
    )


def _mean_metrics(metrics: list[PoseFrameMetrics]) -> PoseFrameMetrics:
    if not metrics:
        raise ValueError("metrics must not be empty")
    return PoseFrameMetrics(
        bbox=tuple(round(mean(values), 6) for values in zip(*(metric.bbox for metric in metrics))),
        body_height=round(mean(metric.body_height for metric in metrics), 6),
        body_width=round(mean(metric.body_width for metric in metrics), 6),
        hip_y=round(mean(metric.hip_y for metric in metrics), 6),
        shoulder_width=round(mean(metric.shoulder_width for metric in metrics), 6),
        ankle_baseline_y=round(mean(metric.ankle_baseline_y for metric in metrics), 6),
        ankle_separation=round(mean(metric.ankle_separation for metric in metrics), 6),
        facing=max(("left", "right"), key=lambda value: sum(metric.facing == value for metric in metrics)),
    )


def _sequence_bbox(frames: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    points = {
        f"{index}:{name}": (float(point[0]), float(point[1]))
        for index, frame in enumerate(frames)
        for name, point in frame["keypoints"].items()
        if name in KEYPOINTS
    }
    return _point_bbox(points)


def _point_bbox(points: dict[str, tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points.values()]
    ys = [point[1] for point in points.values()]
    return (min(xs), min(ys), max(xs), max(ys))


def _point_mean(points: dict[str, tuple[float, float]], left: str, right: str, *, axis: int) -> float:
    return (points[left][axis] + points[right][axis]) / 2.0


def _clamp01(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)
