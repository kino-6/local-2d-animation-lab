from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from natural_sprite_lab.pose_alignment import align_pose_frames_to_target, pose_alignment_report
from natural_sprite_lab.pose_templates import PoseFrame, render_pose_frame, validate_pose_frame
from natural_sprite_lab.pose_templates import load_pose_sequence
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a clean synthetic side-view walk/run pose source.")
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--template-name", default="run_synthetic_sideview_walk_v1")
    parser.add_argument("--action", default="run")
    parser.add_argument("--variant", default="synthetic_sideview_walk_v1")
    parser.add_argument("--frame-count", default=120, type=int)
    parser.add_argument("--render-width", default=512, type=int)
    parser.add_argument("--render-height", default=512, type=int)
    parser.add_argument(
        "--render-style",
        default="wan_confidence_lower",
        choices=(
            "controlnet",
            "controlnet_thin",
            "wan_line",
            "wan_lower",
            "wan_confidence_lower",
            "wan_balanced",
            "vace_walk_silhouette",
            "vace_walk_lower_hint",
            "vace_walk_confidence_hint",
        ),
    )
    parser.add_argument("--stride", default=0.105, type=float)
    parser.add_argument("--lift", default=0.055, type=float)
    parser.add_argument("--body-bob", default=0.018, type=float)
    parser.add_argument("--align-to-template-root", default=None, type=Path)
    parser.add_argument("--align-to-template-name", default=None)
    args = parser.parse_args()

    report = build_synthetic_sideview_motion_source(
        output_root=build_timestamped_run_dir(args.output_root, "motion_source_video_pdca", "motion_sources"),
        template_name=args.template_name,
        action=args.action,
        variant=args.variant,
        frame_count=args.frame_count,
        render_width=args.render_width,
        render_height=args.render_height,
        render_style=args.render_style,
        stride=args.stride,
        lift=args.lift,
        body_bob=args.body_bob,
        align_to_template_root=args.align_to_template_root,
        align_to_template_name=args.align_to_template_name,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


def build_synthetic_sideview_motion_source(
    *,
    output_root: Path,
    template_name: str,
    action: str = "run",
    variant: str = "synthetic_sideview_walk_v1",
    frame_count: int = 120,
    render_width: int = 512,
    render_height: int = 512,
    render_style: str = "wan_confidence_lower",
    stride: float = 0.105,
    lift: float = 0.055,
    body_bob: float = 0.018,
    align_to_template_root: Path | None = None,
    align_to_template_name: str | None = None,
) -> dict[str, Any]:
    if frame_count < 8:
        raise ValueError("frame_count must be at least 8")
    write_run_profile(
        output_root,
        category="motion_source_video_pdca",
        label=template_name,
        extra={"action": action, "variant": variant, "frame_count": frame_count},
    )
    output_dir = output_root / template_name
    render_dir = output_dir / "controlnet"
    output_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)

    frames = [
        synthetic_sideview_frame(
            index,
            frame_count,
            action=action,
            variant=variant,
            stride=stride,
            lift=lift,
            body_bob=body_bob,
        )
        for index in range(frame_count)
    ]
    alignment: dict[str, Any] | None = None
    if align_to_template_root and align_to_template_name:
        target_frame = load_pose_sequence(align_to_template_root, align_to_template_name)[0]
        pre_alignment = pose_alignment_report([frame.to_dict() for frame in frames], target_frame)
        frames = align_pose_frames_to_target(frames, target_frame)
        post_alignment = pose_alignment_report([frame.to_dict() for frame in frames], target_frame)
        alignment = {
            "target_template_root": str(align_to_template_root),
            "target_template_name": align_to_template_name,
            "pre_alignment": pre_alignment.to_dict(),
            "post_alignment": post_alignment.to_dict(),
        }
    image_paths: list[Path] = []
    for frame in frames:
        data = frame.to_dict()
        issues = validate_pose_frame(data)
        if issues:
            raise ValueError(f"Invalid synthetic frame {frame.frame_index}: {issues}")
        json_path = output_dir / f"frame_{frame.frame_index:03d}.json"
        image_path = render_dir / f"frame_{frame.frame_index:03d}.png"
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        render_pose_frame(data, render_width, render_height, style=render_style).save(image_path)
        image_paths.append(image_path)

    contact_sheet = make_contact_sheet(image_paths, output_dir / "contact_sheet.png")
    report = {
        "status": "completed",
        "source": "synthetic_sideview_motion",
        "output_template": str(output_dir),
        "template_name": template_name,
        "source_frames": frame_count,
        "frame_count": frame_count,
        "target_template": "synthetic_sideview",
        "render_style": render_style,
        "contact_sheet": str(contact_sheet),
        "mean_confidence": round(_mean_confidence(frames), 5),
        "settings": {
            "stride": stride,
            "lift": lift,
            "body_bob": body_bob,
        },
        "source_filter": {
            "start_index": 0,
            "end_index": frame_count - 1,
            "min_frame_mean_confidence": None,
            "min_ankle_x_separation": None,
            "retained_source_indices": list(range(frame_count)),
        },
    }
    if alignment:
        report["alignment"] = alignment
    (output_dir / "motion_source_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def synthetic_sideview_frame(
    index: int,
    frame_count: int,
    *,
    action: str,
    variant: str,
    stride: float,
    lift: float,
    body_bob: float,
) -> PoseFrame:
    phase = (index / frame_count) * math.tau
    bob = body_bob * (0.5 + 0.5 * math.cos(phase * 2.0))
    cx = 0.52
    neck_y = 0.335 + bob
    hip_y = 0.555 + bob
    head_y = 0.255 + bob
    shoulder_dx = 0.032
    hip_dx = 0.028

    right_leg = _leg_points(cx - hip_dx, hip_y, phase, stride=stride, lift=lift, side=-1.0)
    left_leg = _leg_points(cx + hip_dx, hip_y, phase + math.pi, stride=stride, lift=lift, side=1.0)
    right_arm = _arm_points(cx - shoulder_dx, neck_y + 0.035, phase + math.pi, side=-1.0)
    left_arm = _arm_points(cx + shoulder_dx, neck_y + 0.035, phase, side=1.0)

    keypoints = {
        "nose": [cx + 0.01, head_y],
        "neck": [cx, neck_y],
        "right_shoulder": [cx - shoulder_dx, neck_y + 0.025],
        "right_elbow": list(right_arm["elbow"]),
        "right_wrist": list(right_arm["wrist"]),
        "left_shoulder": [cx + shoulder_dx, neck_y + 0.025],
        "left_elbow": list(left_arm["elbow"]),
        "left_wrist": list(left_arm["wrist"]),
        "right_hip": [cx - hip_dx, hip_y],
        "right_knee": list(right_leg["knee"]),
        "right_ankle": list(right_leg["ankle"]),
        "left_hip": [cx + hip_dx, hip_y],
        "left_knee": list(left_leg["knee"]),
        "left_ankle": list(left_leg["ankle"]),
    }
    confidence = {
        "nose": 0.55,
        "neck": 0.65,
        "right_shoulder": 0.55,
        "right_elbow": 0.45,
        "right_wrist": 0.35,
        "left_shoulder": 0.55,
        "left_elbow": 0.45,
        "left_wrist": 0.35,
        "right_hip": 0.95,
        "right_knee": 0.95,
        "right_ankle": 0.98,
        "left_hip": 0.95,
        "left_knee": 0.95,
        "left_ankle": 0.98,
    }
    return PoseFrame(
        action=action,
        variant=variant,
        frame_index=index,
        phase=_phase_name(phase),
        keypoints={name: [_clamp(point[0]), _clamp(point[1])] for name, point in keypoints.items()},
        confidence=confidence,
        notes="synthetic side-view motion source with clean lower-body contacts",
    )


def _leg_points(
    hip_x: float,
    hip_y: float,
    phase: float,
    *,
    stride: float,
    lift: float,
    side: float,
) -> dict[str, tuple[float, float]]:
    swing = math.sin(phase)
    lift_amount = lift * max(0.0, math.cos(phase))
    foot_x = hip_x + (stride * 0.55) * swing + 0.055 * side
    foot_y = 0.86 - lift_amount
    knee_x = hip_x + 0.38 * stride * swing + 0.015 * side
    knee_y = (hip_y + foot_y) * 0.54 + 0.05 * (1.0 - abs(swing))
    return {"knee": (knee_x, knee_y), "ankle": (foot_x, foot_y)}


def _arm_points(shoulder_x: float, shoulder_y: float, phase: float, *, side: float) -> dict[str, tuple[float, float]]:
    swing = math.sin(phase)
    elbow = (shoulder_x + 0.045 * swing + 0.015 * side, shoulder_y + 0.12)
    wrist = (shoulder_x + 0.075 * swing + 0.02 * side, shoulder_y + 0.215)
    return {"elbow": elbow, "wrist": wrist}


def _phase_name(phase: float) -> str:
    normalized = (phase % math.tau) / math.tau
    if normalized < 0.25:
        return "contact"
    if normalized < 0.5:
        return "passing"
    if normalized < 0.75:
        return "opposite_contact"
    return "recover"


def _mean_confidence(frames: list[PoseFrame]) -> float:
    values = [value for frame in frames for value in (frame.confidence or {}).values()]
    return sum(values) / max(1, len(values))


def _clamp(value: float) -> float:
    return round(max(0.02, min(0.98, value)), 6)


if __name__ == "__main__":
    main()
