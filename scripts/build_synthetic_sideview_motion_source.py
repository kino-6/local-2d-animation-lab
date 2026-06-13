from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

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
    parser.add_argument(
        "--sidecar-style",
        default="foot_contact_soft",
        choices=("none", "foot_contact_soft", "foot_contact_boxes"),
    )
    parser.add_argument("--stride", default=0.105, type=float)
    parser.add_argument("--lift", default=0.055, type=float)
    parser.add_argument("--body-bob", default=0.018, type=float)
    parser.add_argument("--arm-swing-scale", default=1.0, type=float)
    parser.add_argument("--leg-side-offset", default=0.055, type=float)
    parser.add_argument("--min-ankle-x-separation", default=0.045, type=float)
    parser.add_argument("--min-foot-box-x-gap", default=0.012, type=float)
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
        sidecar_style=args.sidecar_style,
        stride=args.stride,
        lift=args.lift,
        body_bob=args.body_bob,
        arm_swing_scale=args.arm_swing_scale,
        leg_side_offset=args.leg_side_offset,
        min_ankle_x_separation=args.min_ankle_x_separation,
        min_foot_box_x_gap=args.min_foot_box_x_gap,
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
    sidecar_style: str = "foot_contact_soft",
    stride: float = 0.105,
    lift: float = 0.055,
    body_bob: float = 0.018,
    arm_swing_scale: float = 1.0,
    leg_side_offset: float = 0.055,
    min_ankle_x_separation: float = 0.045,
    min_foot_box_x_gap: float = 0.012,
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
    sidecar_dir = output_dir / "lower_body_sidecar"
    output_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    if sidecar_style != "none":
        sidecar_dir.mkdir(parents=True, exist_ok=True)

    frames = [
        synthetic_sideview_frame(
            index,
            frame_count,
            action=action,
            variant=variant,
            stride=stride,
            lift=lift,
            body_bob=body_bob,
            arm_swing_scale=arm_swing_scale,
            leg_side_offset=leg_side_offset,
        )
        for index in range(frame_count)
    ]
    diagnostics = _motion_diagnostics(
        frames,
        min_ankle_x_separation=min_ankle_x_separation,
        min_foot_box_x_gap=min_foot_box_x_gap,
    )
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
    sidecar_paths: list[Path] = []
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
        if sidecar_style != "none":
            sidecar_path = sidecar_dir / f"frame_{frame.frame_index:03d}.png"
            render_lower_body_sidecar(data, render_width, render_height, style=sidecar_style).save(sidecar_path)
            sidecar_paths.append(sidecar_path)

    contact_sheet = make_contact_sheet(image_paths, output_dir / "contact_sheet.png")
    sidecar_contact_sheet = None
    if sidecar_paths:
        sidecar_contact_sheet = make_contact_sheet(sidecar_paths, output_dir / "lower_body_sidecar_contact_sheet.png")
    report = {
        "status": "completed",
        "source": "synthetic_sideview_motion",
        "output_template": str(output_dir),
        "template_name": template_name,
        "source_frames": frame_count,
        "frame_count": frame_count,
        "target_template": "synthetic_sideview",
        "render_style": render_style,
        "sidecar_style": sidecar_style,
        "contact_sheet": str(contact_sheet),
        "lower_body_sidecar_dir": str(sidecar_dir) if sidecar_paths else None,
        "lower_body_sidecar_contact_sheet": str(sidecar_contact_sheet) if sidecar_contact_sheet else None,
        "mean_confidence": round(_mean_confidence(frames), 5),
        "settings": {
            "stride": stride,
            "lift": lift,
            "body_bob": body_bob,
            "arm_swing_scale": arm_swing_scale,
            "leg_side_offset": leg_side_offset,
            "min_ankle_x_separation": min_ankle_x_separation,
            "min_foot_box_x_gap": min_foot_box_x_gap,
        },
        "motion_diagnostics": diagnostics,
        "source_filter": {
            "start_index": 0,
            "end_index": frame_count - 1,
            "min_frame_mean_confidence": None,
            "min_ankle_x_separation": min_ankle_x_separation,
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
    arm_swing_scale: float = 1.0,
    leg_side_offset: float = 0.055,
) -> PoseFrame:
    phase = (index / frame_count) * math.tau
    bob = body_bob * (0.5 + 0.5 * math.cos(phase * 2.0))
    cx = 0.52
    neck_y = 0.335 + bob
    hip_y = 0.555 + bob
    head_y = 0.255 + bob
    shoulder_dx = 0.032
    hip_dx = 0.028

    right_leg = _leg_points(
        cx - hip_dx,
        hip_y,
        phase,
        stride=stride,
        lift=lift,
        side=-1.0,
        side_offset=leg_side_offset,
    )
    left_leg = _leg_points(
        cx + hip_dx,
        hip_y,
        phase + math.pi,
        stride=stride,
        lift=lift,
        side=1.0,
        side_offset=leg_side_offset,
    )
    right_arm = _arm_points(
        cx - shoulder_dx,
        neck_y + 0.035,
        phase + math.pi,
        side=-1.0,
        swing_scale=arm_swing_scale,
    )
    left_arm = _arm_points(
        cx + shoulder_dx,
        neck_y + 0.035,
        phase,
        side=1.0,
        swing_scale=arm_swing_scale,
    )

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
    clamped_keypoints = {name: [_clamp(point[0]), _clamp(point[1])] for name, point in keypoints.items()}
    return PoseFrame(
        action=action,
        variant=variant,
        frame_index=index,
        phase=_phase_name(phase),
        keypoints=clamped_keypoints,
        confidence=confidence,
        foot_contact=_foot_contact_metadata(clamped_keypoints, ground_y=0.86),
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
    side_offset: float,
) -> dict[str, tuple[float, float]]:
    swing = math.sin(phase)
    lift_amount = lift * max(0.0, math.cos(phase))
    foot_x = hip_x + (stride * 0.55) * swing + side_offset * side
    foot_y = 0.86 - lift_amount
    knee_x = hip_x + 0.38 * stride * swing + 0.015 * side
    knee_y = (hip_y + foot_y) * 0.54 + 0.05 * (1.0 - abs(swing))
    return {"knee": (knee_x, knee_y), "ankle": (foot_x, foot_y)}


def _arm_points(
    shoulder_x: float,
    shoulder_y: float,
    phase: float,
    *,
    side: float,
    swing_scale: float,
) -> dict[str, tuple[float, float]]:
    swing = math.sin(phase)
    elbow = (shoulder_x + 0.045 * swing * swing_scale + 0.015 * side, shoulder_y + 0.12)
    wrist = (shoulder_x + 0.075 * swing * swing_scale + 0.02 * side, shoulder_y + 0.215)
    return {"elbow": elbow, "wrist": wrist}


def _motion_diagnostics(
    frames: list[PoseFrame],
    *,
    min_ankle_x_separation: float,
    min_foot_box_x_gap: float,
) -> dict[str, Any]:
    separations = [
        abs(frame.keypoints["left_ankle"][0] - frame.keypoints["right_ankle"][0])
        for frame in frames
    ]
    sampled_indices = _even_sample_indices(len(frames), count=min(8, len(frames)))
    sampled_separations = [separations[index] for index in sampled_indices]
    foot_box_gaps = [
        float((frame.foot_contact or {}).get("foot_box_x_gap", separations[frame_index]))
        for frame_index, frame in enumerate(frames)
    ]
    sampled_foot_box_gaps = [foot_box_gaps[index] for index in sampled_indices]
    phase_counts: dict[str, int] = {}
    stance_counts = {"left": 0, "right": 0, "ambiguous": 0}
    contact_counts = {"left": 0, "right": 0, "both": 0, "none": 0}
    unclear_indices: list[int] = []
    unclear_foot_box_indices: list[int] = []
    stance_slide_deltas: list[float] = []
    previous_stance: tuple[str, float] | None = None
    for frame, separation in zip(frames, separations):
        phase_counts[frame.phase] = phase_counts.get(frame.phase, 0) + 1
        if separation < min_ankle_x_separation:
            unclear_indices.append(frame.frame_index)
        foot_contact = frame.foot_contact or {}
        foot_gap = float(foot_contact.get("foot_box_x_gap", separation))
        if foot_gap < min_foot_box_x_gap:
            unclear_foot_box_indices.append(frame.frame_index)
        contact_state = str(foot_contact.get("contact_state", "none"))
        if contact_state not in contact_counts:
            contact_state = "none"
        contact_counts[contact_state] += 1
        stance_foot = str(foot_contact.get("stance_foot", "ambiguous"))
        if stance_foot in {"left", "right"}:
            stance_counts[stance_foot] += 1
            foot = foot_contact.get(f"{stance_foot}_foot", {})
            center = foot.get("center", [0.0, 0.0]) if isinstance(foot, dict) else [0.0, 0.0]
            stance_x = float(center[0])
            if previous_stance and previous_stance[0] == stance_foot:
                stance_slide_deltas.append(abs(stance_x - previous_stance[1]))
            previous_stance = (stance_foot, stance_x)
        else:
            stance_counts["ambiguous"] += 1
            previous_stance = None

    return {
        "min_ankle_x_separation": round(min(separations), 5),
        "mean_ankle_x_separation": round(sum(separations) / max(1, len(separations)), 5),
        "sampled_indices": sampled_indices,
        "sampled_min_ankle_x_separation": round(min(sampled_separations), 5),
        "min_foot_box_x_gap": round(min(foot_box_gaps), 5),
        "sampled_min_foot_box_x_gap": round(min(sampled_foot_box_gaps), 5),
        "unclear_ankle_separation_count": len(unclear_indices),
        "unclear_ankle_separation_indices": unclear_indices[:24],
        "unclear_foot_box_count": len(unclear_foot_box_indices),
        "unclear_foot_box_indices": unclear_foot_box_indices[:24],
        "phase_counts": phase_counts,
        "stance_counts": stance_counts,
        "contact_counts": contact_counts,
        "max_stance_slide_delta": round(max(stance_slide_deltas or [0.0]), 5),
        "mean_stance_slide_delta": round(sum(stance_slide_deltas) / max(1, len(stance_slide_deltas)), 5),
        "passes_min_ankle_x_separation": len(unclear_indices) == 0,
        "passes_foot_box_separation": len(unclear_foot_box_indices) == 0,
    }


def _even_sample_indices(frame_count: int, *, count: int) -> list[int]:
    if count <= 0:
        return []
    return [min(frame_count - 1, round(index * frame_count / count)) for index in range(count)]


def _phase_name(phase: float) -> str:
    normalized = (phase % math.tau) / math.tau
    if normalized < 0.25:
        return "contact"
    if normalized < 0.5:
        return "passing"
    if normalized < 0.75:
        return "opposite_contact"
    return "recover"


def _foot_contact_metadata(keypoints: dict[str, list[float]], *, ground_y: float) -> dict[str, Any]:
    left = _foot_metadata_for("left", keypoints["left_ankle"], ground_y=ground_y)
    right = _foot_metadata_for("right", keypoints["right_ankle"], ground_y=ground_y)
    left_contact = bool(left["contact"])
    right_contact = bool(right["contact"])
    if left_contact and right_contact:
        contact_state = "both"
        stance_foot = "ambiguous"
        swing_foot = "none"
    elif left_contact:
        contact_state = "left"
        stance_foot = "left"
        swing_foot = "right"
    elif right_contact:
        contact_state = "right"
        stance_foot = "right"
        swing_foot = "left"
    else:
        contact_state = "none"
        stance_foot = "ambiguous"
        swing_foot = "ambiguous"
    return {
        "ground_y": round(ground_y, 5),
        "stance_foot": stance_foot,
        "swing_foot": swing_foot,
        "contact_state": contact_state,
        "left_foot": left,
        "right_foot": right,
        "ankle_x_separation": round(abs(left["ankle"][0] - right["ankle"][0]), 5),
        "toe_x_separation": round(abs(left["toe"][0] - right["toe"][0]), 5),
        "heel_x_separation": round(abs(left["heel"][0] - right["heel"][0]), 5),
        "foot_box_x_gap": round(_foot_box_x_gap(left["box"], right["box"]), 5),
    }


def _foot_metadata_for(side: str, ankle: list[float], *, ground_y: float) -> dict[str, Any]:
    ankle_x = float(ankle[0])
    ankle_y = float(ankle[1])
    foot_len = 0.078
    foot_height = 0.028
    toe_x = _clamp(ankle_x + foot_len * 0.62)
    heel_x = _clamp(ankle_x - foot_len * 0.38)
    sole_y = min(0.98, max(ankle_y + foot_height * 0.45, ground_y if ankle_y >= ground_y - 0.012 else ankle_y))
    box = [
        _clamp(heel_x - foot_len * 0.08),
        _clamp(sole_y - foot_height),
        _clamp(toe_x + foot_len * 0.08),
        _clamp(sole_y + foot_height * 0.36),
    ]
    return {
        "side": side,
        "ankle": [round(ankle_x, 5), round(ankle_y, 5)],
        "toe": [round(toe_x, 5), round(sole_y, 5)],
        "heel": [round(heel_x, 5), round(sole_y, 5)],
        "center": [round((toe_x + heel_x) / 2.0, 5), round(sole_y, 5)],
        "box": [round(value, 5) for value in box],
        "contact": ankle_y >= ground_y - 0.012,
    }


def _foot_box_x_gap(left_box: list[float], right_box: list[float]) -> float:
    left_min, _, left_max, _ = left_box
    right_min, _, right_max, _ = right_box
    if left_max < right_min:
        return right_min - left_max
    if right_max < left_min:
        return left_min - right_max
    return 0.0


def render_lower_body_sidecar(frame: dict[str, Any], width: int, height: int, *, style: str = "foot_contact_soft") -> Image.Image:
    if style not in {"foot_contact_soft", "foot_contact_boxes"}:
        raise ValueError(f"Unknown lower-body sidecar style: {style}")
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    keypoints = frame["keypoints"]
    points = {name: _to_px(point, width, height) for name, point in keypoints.items()}
    foot_contact = frame.get("foot_contact") or _foot_contact_metadata(keypoints, ground_y=0.86)
    ground_y = round(float(foot_contact["ground_y"]) * height)
    base = 214 if style == "foot_contact_soft" else 150
    draw.line((0, ground_y, width, ground_y), fill=(232, 232, 232), width=max(1, round(width * 0.003)))
    pelvis = (
        round((points["left_hip"][0] + points["right_hip"][0]) / 2),
        round((points["left_hip"][1] + points["right_hip"][1]) / 2),
    )
    draw.line(
        (points["left_hip"], pelvis, points["right_hip"]),
        fill=(base, base, base),
        width=max(2, round(width * 0.011)),
        joint="curve",
    )
    for side, shade in (("left", 178), ("right", 116)):
        hip = points[f"{side}_hip"]
        knee = points[f"{side}_knee"]
        ankle = points[f"{side}_ankle"]
        color = (shade, shade, shade)
        draw.line((hip, knee, ankle), fill=color, width=max(3, round(width * 0.014)), joint="curve")
        foot = foot_contact[f"{side}_foot"]
        _draw_sidecar_foot(draw, foot, width, height, color=color, boxes_only=style == "foot_contact_boxes")
    return image


def _draw_sidecar_foot(
    draw: ImageDraw.ImageDraw,
    foot: dict[str, Any],
    width: int,
    height: int,
    *,
    color: tuple[int, int, int],
    boxes_only: bool,
) -> None:
    box = _box_to_px(foot["box"], width, height)
    if boxes_only:
        draw.rectangle(box, outline=color, width=max(1, round(width * 0.004)))
    else:
        draw.rounded_rectangle(box, radius=max(2, round(width * 0.006)), fill=color)
    if foot.get("contact"):
        y = min(height - 1, box[3] + max(1, round(height * 0.005)))
        draw.line((box[0], y, box[2], y), fill=(96, 96, 96), width=max(1, round(width * 0.004)))


def _to_px(point: list[float], width: int, height: int) -> tuple[int, int]:
    return round(float(point[0]) * width), round(float(point[1]) * height)


def _box_to_px(box: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    return (
        round(float(left) * width),
        round(float(top) * height),
        round(float(right) * width),
        round(float(bottom) * height),
    )


def _mean_confidence(frames: list[PoseFrame]) -> float:
    values = [value for frame in frames for value in (frame.confidence or {}).values()]
    return sum(values) / max(1, len(values))


def _clamp(value: float) -> float:
    return round(max(0.02, min(0.98, value)), 6)


if __name__ == "__main__":
    main()
