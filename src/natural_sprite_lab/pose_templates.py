from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet


KEYPOINTS = (
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

BONES = (
    ("nose", "neck", (255, 255, 255)),
    ("neck", "right_shoulder", (255, 255, 0)),
    ("right_shoulder", "right_elbow", (0, 255, 0)),
    ("right_elbow", "right_wrist", (0, 255, 128)),
    ("neck", "left_shoulder", (255, 255, 0)),
    ("left_shoulder", "left_elbow", (255, 0, 0)),
    ("left_elbow", "left_wrist", (255, 128, 0)),
    ("neck", "right_hip", (0, 255, 255)),
    ("right_hip", "right_knee", (255, 0, 255)),
    ("right_knee", "right_ankle", (255, 0, 128)),
    ("neck", "left_hip", (0, 128, 255)),
    ("left_hip", "left_knee", (0, 0, 255)),
    ("left_knee", "left_ankle", (128, 0, 255)),
)


@dataclass(frozen=True)
class PoseFrame:
    action: str
    variant: str
    frame_index: int
    phase: str
    keypoints: dict[str, list[float]]
    confidence: dict[str, float] | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "action": self.action,
            "variant": self.variant,
            "frame_index": self.frame_index,
            "phase": self.phase,
            "keypoints": self.keypoints,
            "notes": self.notes,
        }
        if self.confidence is not None:
            data["confidence"] = self.confidence
        return data


def template_name(action: str, variant: str | None = None) -> str:
    if action == "attack":
        return f"attack_{variant or 'sword'}"
    if action == "hit":
        return f"hit_{variant or 'light'}"
    return action


def infer_template_name(spec: Any) -> str:
    action = getattr(getattr(spec, "action", ""), "value", getattr(spec, "action", ""))
    variant = action
    frame_plan = list(getattr(spec, "frame_plan", []) or [])
    if frame_plan:
        variant = str(frame_plan[0].get("action_variant", variant))
    return template_name(str(action), variant)


def validate_pose_frame(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in ("action", "variant", "frame_index", "phase", "keypoints"):
        if field not in data:
            issues.append(f"missing field: {field}")
    keypoints = data.get("keypoints", {})
    if not isinstance(keypoints, dict):
        issues.append("keypoints must be an object")
        return issues
    for name in KEYPOINTS:
        point = keypoints.get(name)
        if not isinstance(point, list) or len(point) != 2:
            issues.append(f"missing or invalid keypoint: {name}")
            continue
        x, y = point
        if not isinstance(x, int | float) or not isinstance(y, int | float):
            issues.append(f"non-numeric keypoint: {name}")
        elif not 0.0 <= float(x) <= 1.0 or not 0.0 <= float(y) <= 1.0:
            issues.append(f"out-of-range keypoint: {name}")
    confidence = data.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, dict):
            issues.append("confidence must be an object")
        else:
            for name, value in confidence.items():
                if name not in KEYPOINTS:
                    issues.append(f"unknown confidence keypoint: {name}")
                elif not isinstance(value, int | float):
                    issues.append(f"non-numeric confidence: {name}")
                elif not 0.0 <= float(value) <= 1.0:
                    issues.append(f"out-of-range confidence: {name}")
    return issues


def load_pose_sequence(template_root: Path, name: str) -> list[dict[str, Any]]:
    action_dir = template_root / name
    frames = []
    for path in sorted(action_dir.glob("frame_*.json"), key=_frame_path_index):
        data = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_pose_frame(data)
        if issues:
            raise ValueError(f"Invalid pose template {path}: {issues}")
        data["path"] = str(path)
        frames.append(data)
    if not frames:
        raise FileNotFoundError(f"No pose templates found for {name}: {action_dir}")
    return frames


def _frame_path_index(path: Path) -> int:
    try:
        return int(path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return -1


def render_pose_frame(frame: dict[str, Any], width: int, height: int, style: str = "controlnet") -> Image.Image:
    if style == "controlnet":
        background = (0, 0, 0)
        line_width = 6
        radius = 5
        colors = {bone: color for bone, _, color in BONES}
    elif style == "controlnet_thin":
        background = (0, 0, 0)
        line_width = 3
        radius = 3
        colors = {bone: color for bone, _, color in BONES}
    elif style == "wan_line":
        background = (255, 255, 255)
        line_width = 4
        radius = 4
        colors = {
            "nose": (70, 70, 70),
            "neck": (70, 70, 70),
            "right_shoulder": (80, 110, 180),
            "right_elbow": (80, 110, 180),
            "left_shoulder": (170, 90, 80),
            "left_elbow": (170, 90, 80),
            "right_hip": (55, 95, 190),
            "right_knee": (55, 95, 190),
            "left_hip": (185, 90, 45),
            "left_knee": (185, 90, 45),
        }
    elif style in {"wan_lower", "wan_confidence_lower", "wan_balanced", "wan_walk_lower"}:
        background = (255, 255, 255)
        line_width = 4 if style in {"wan_balanced", "wan_walk_lower"} else 5
        radius = 3 if style in {"wan_balanced", "wan_walk_lower"} else 4
        colors = {
            "nose": (130, 130, 130) if style == "wan_balanced" else (160, 160, 160),
            "neck": (130, 130, 130) if style == "wan_balanced" else (160, 160, 160),
            "right_shoulder": (125, 125, 125) if style == "wan_balanced" else (150, 150, 150),
            "right_elbow": (125, 125, 125) if style == "wan_balanced" else (150, 150, 150),
            "left_shoulder": (125, 125, 125) if style == "wan_balanced" else (150, 150, 150),
            "left_elbow": (125, 125, 125) if style == "wan_balanced" else (150, 150, 150),
            "right_hip": (40, 80, 210),
            "right_knee": (40, 80, 210),
            "left_hip": (210, 85, 35),
            "left_knee": (210, 85, 35),
        }
    elif style in {
        "vace_depth_proxy",
        "vace_side_proxy",
        "vace_walk_silhouette",
        "vace_walk_lower_hint",
        "vace_walk_confidence_hint",
    }:
        background = (255, 255, 255)
        line_width = 4
        radius = 3
        colors = {}
    else:
        raise ValueError(f"Unknown pose render style: {style}")
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    points = {
        name: (int(float(point[0]) * width), int(float(point[1]) * height))
        for name, point in frame["keypoints"].items()
    }
    confidence = {
        name: max(0.0, min(1.0, float(value)))
        for name, value in (frame.get("confidence") or {}).items()
    }
    if style == "vace_depth_proxy":
        _draw_vace_depth_proxy(draw, points, width, height)
        return image
    if style == "vace_side_proxy":
        _draw_vace_side_proxy(draw, points, width, height)
        return image
    if style == "vace_walk_silhouette":
        _draw_vace_walk_silhouette(draw, points, width, height)
        return image
    if style == "vace_walk_lower_hint":
        _draw_vace_walk_lower_hint(draw, points, width, height)
        return image
    if style == "vace_walk_confidence_hint":
        _draw_vace_walk_confidence_hint(draw, points, confidence, width, height)
        return image
    for start, end, default_color in BONES:
        color = default_color if style == "controlnet" else colors.get(start, (110, 110, 110))
        confidence_weight = min(confidence.get(start, 1.0), confidence.get(end, 1.0))
        if style == "wan_walk_lower" and not _is_walk_lower_control_bone(start, end):
            confidence_weight = min(confidence_weight, 0.08)
            color = (248, 248, 248)
            bone_width = 1
            bone_radius = 1
        elif style in {"wan_confidence_lower", "wan_balanced", "wan_walk_lower"}:
            blend_weight = confidence_weight
            if style == "wan_balanced":
                blend_weight = 0.5 + confidence_weight * 0.5
            if style == "wan_walk_lower":
                blend_weight = 0.75 + confidence_weight * 0.25
            color = _blend_color((245, 245, 245), color, blend_weight)
            bone_width = max(1, round(line_width * (0.35 + confidence_weight * 0.65)))
            bone_radius = max(1, round(radius * (0.45 + confidence_weight * 0.55)))
        else:
            bone_width = line_width
            bone_radius = radius
        _draw_bone(draw, points[start], points[end], color, width=bone_width, radius=bone_radius)
    return image


def _is_walk_lower_control_bone(start: str, end: str) -> bool:
    return start in {"neck", "right_hip", "right_knee", "left_hip", "left_knee"} and end in {
        "right_hip",
        "right_knee",
        "right_ankle",
        "left_hip",
        "left_knee",
        "left_ankle",
    }


def _draw_vace_depth_proxy(
    draw: ImageDraw.ImageDraw,
    points: dict[str, tuple[int, int]],
    width: int,
    height: int,
) -> None:
    scale = min(width, height)
    body = (120, 120, 120)
    near = (72, 72, 72)
    far = (172, 172, 172)
    soft = (210, 210, 210)

    left_shoulder = points["left_shoulder"]
    right_shoulder = points["right_shoulder"]
    left_hip = points["left_hip"]
    right_hip = points["right_hip"]
    draw.polygon([left_shoulder, right_shoulder, right_hip, left_hip], fill=body)

    head_radius = max(4, round(scale * 0.035))
    nose = points["nose"]
    draw.ellipse(
        (
            nose[0] - head_radius,
            nose[1] - head_radius,
            nose[0] + head_radius,
            nose[1] + head_radius,
        ),
        fill=(140, 140, 140),
    )

    limb_width = max(5, round(scale * 0.035))
    arm_width = max(3, round(scale * 0.022))
    for start, mid, end, color, line_width in (
        ("right_hip", "right_knee", "right_ankle", near, limb_width),
        ("left_hip", "left_knee", "left_ankle", far, limb_width),
        ("right_shoulder", "right_elbow", "right_wrist", soft, arm_width),
        ("left_shoulder", "left_elbow", "left_wrist", soft, arm_width),
    ):
        _draw_depth_limb(draw, points[start], points[mid], points[end], color, line_width)


def _draw_vace_side_proxy(
    draw: ImageDraw.ImageDraw,
    points: dict[str, tuple[int, int]],
    width: int,
    height: int,
) -> None:
    scale = min(width, height)
    center_x = round(
        (
            points["neck"][0]
            + points["left_hip"][0]
            + points["right_hip"][0]
            + points["left_shoulder"][0]
            + points["right_shoulder"][0]
        )
        / 5
    )
    neck_y = points["neck"][1]
    hip_y = round((points["left_hip"][1] + points["right_hip"][1]) / 2)
    shoulder_y = round((points["left_shoulder"][1] + points["right_shoulder"][1]) / 2)
    body_width = max(8, round(scale * 0.045))
    head_radius = max(5, round(scale * 0.036))

    draw.rounded_rectangle(
        (
            center_x - body_width,
            shoulder_y,
            center_x + body_width,
            hip_y + round(scale * 0.035),
        ),
        radius=max(3, round(body_width * 0.6)),
        fill=(118, 118, 118),
    )
    head_center = (center_x + round(scale * 0.012), points["nose"][1])
    draw.ellipse(
        (
            head_center[0] - head_radius,
            head_center[1] - head_radius,
            head_center[0] + head_radius,
            head_center[1] + head_radius,
        ),
        fill=(138, 138, 138),
    )
    draw.rectangle(
        (
            center_x - round(body_width * 0.55),
            neck_y - round(scale * 0.01),
            center_x + round(body_width * 0.55),
            shoulder_y + round(scale * 0.025),
        ),
        fill=(146, 146, 146),
    )

    limb_width = max(5, round(scale * 0.028))
    arm_width = max(3, round(scale * 0.018))
    right_forward = points["right_ankle"][0] >= points["left_ankle"][0]
    leg_specs = (
        ("right_hip", "right_knee", "right_ankle", (74, 74, 74) if right_forward else (168, 168, 168)),
        ("left_hip", "left_knee", "left_ankle", (168, 168, 168) if right_forward else (74, 74, 74)),
    )
    for hip, knee, ankle, color in leg_specs:
        start = (center_x, points[hip][1])
        mid = (points[knee][0], points[knee][1])
        end = (points[ankle][0], points[ankle][1])
        _draw_depth_limb(draw, start, mid, end, color, limb_width)
        foot = round(scale * 0.035)
        direction = 1 if end[0] >= center_x else -1
        draw.line((end[0], end[1], end[0] + direction * foot, end[1] + round(scale * 0.008)), fill=color, width=limb_width)

    for shoulder, elbow, wrist in (
        ("right_shoulder", "right_elbow", "right_wrist"),
        ("left_shoulder", "left_elbow", "left_wrist"),
    ):
        start = (center_x, points[shoulder][1])
        _draw_depth_limb(draw, start, points[elbow], points[wrist], (196, 196, 196), arm_width)


def _draw_vace_walk_silhouette(
    draw: ImageDraw.ImageDraw,
    points: dict[str, tuple[int, int]],
    width: int,
    height: int,
) -> None:
    scale = min(width, height)
    center_x = round(
        (
            points["neck"][0]
            + points["left_hip"][0]
            + points["right_hip"][0]
            + points["left_shoulder"][0]
            + points["right_shoulder"][0]
        )
        / 5
    )
    shoulder_y = round((points["left_shoulder"][1] + points["right_shoulder"][1]) / 2)
    hip_y = round((points["left_hip"][1] + points["right_hip"][1]) / 2)
    torso_width = max(9, round(scale * 0.052))
    head_radius = max(6, round(scale * 0.040))
    right_forward = points["right_ankle"][0] >= points["left_ankle"][0]

    head_center = (center_x + round(scale * 0.015), points["nose"][1])
    draw.ellipse(
        (
            head_center[0] - head_radius,
            head_center[1] - head_radius,
            head_center[0] + head_radius,
            head_center[1] + head_radius,
        ),
        fill=(174, 174, 174),
    )
    draw.rounded_rectangle(
        (
            center_x - torso_width,
            shoulder_y,
            center_x + torso_width,
            hip_y + round(scale * 0.042),
        ),
        radius=max(4, round(torso_width * 0.7)),
        fill=(150, 150, 150),
    )

    limb_width = max(6, round(scale * 0.032))
    far_width = max(4, round(limb_width * 0.74))
    leg_specs = (
        ("right_hip", "right_knee", "right_ankle", right_forward),
        ("left_hip", "left_knee", "left_ankle", not right_forward),
    )
    for hip, knee, ankle, is_near in leg_specs:
        color = (82, 82, 82) if is_near else (190, 190, 190)
        leg_width = limb_width if is_near else far_width
        start = (center_x, points[hip][1])
        end = points[ankle]
        _draw_depth_limb(draw, start, points[knee], end, color, leg_width)
        foot_len = round(scale * (0.052 if is_near else 0.042))
        foot_height = max(2, round(scale * 0.010))
        direction = 1 if end[0] >= center_x else -1
        draw.rounded_rectangle(
            (
                min(end[0], end[0] + direction * foot_len),
                end[1] - foot_height,
                max(end[0], end[0] + direction * foot_len),
                end[1] + foot_height,
            ),
            radius=foot_height,
            fill=color,
        )
        contact_y = min(height - 1, end[1] + round(scale * 0.020))
        contact_color = (128, 128, 128) if is_near else (220, 220, 220)
        draw.line(
            (
                end[0] - round(foot_len * 0.55),
                contact_y,
                end[0] + round(foot_len * 0.85),
                contact_y,
            ),
            fill=contact_color,
            width=max(1, round(scale * 0.006)),
        )

    arm_width = max(3, round(scale * 0.016))
    for shoulder, elbow, wrist in (
        ("right_shoulder", "right_elbow", "right_wrist"),
        ("left_shoulder", "left_elbow", "left_wrist"),
    ):
        start = (center_x, points[shoulder][1])
        _draw_depth_limb(draw, start, points[elbow], points[wrist], (214, 214, 214), arm_width)


def _draw_vace_walk_lower_hint(
    draw: ImageDraw.ImageDraw,
    points: dict[str, tuple[int, int]],
    width: int,
    height: int,
) -> None:
    scale = min(width, height)
    center_x = round((points["left_hip"][0] + points["right_hip"][0] + points["neck"][0]) / 3)
    hip_y = round((points["left_hip"][1] + points["right_hip"][1]) / 2)
    right_forward = points["right_ankle"][0] >= points["left_ankle"][0]
    limb_width = max(4, round(scale * 0.020))
    pelvis_width = max(5, round(scale * 0.030))
    draw.rounded_rectangle(
        (
            center_x - pelvis_width,
            hip_y - round(scale * 0.012),
            center_x + pelvis_width,
            hip_y + round(scale * 0.018),
        ),
        radius=max(2, round(scale * 0.010)),
        fill=(232, 232, 232),
    )
    for hip, knee, ankle, is_near in (
        ("right_hip", "right_knee", "right_ankle", right_forward),
        ("left_hip", "left_knee", "left_ankle", not right_forward),
    ):
        color = (206, 206, 206) if is_near else (236, 236, 236)
        width_px = limb_width if is_near else max(2, round(limb_width * 0.65))
        start = (center_x, points[hip][1])
        end = points[ankle]
        _draw_depth_limb(draw, start, points[knee], end, color, width_px)
        foot_len = round(scale * (0.046 if is_near else 0.034))
        direction = 1 if end[0] >= center_x else -1
        contact_y = min(height - 1, end[1] + round(scale * 0.016))
        draw.line(
            (
                end[0] - round(foot_len * 0.35),
                contact_y,
                end[0] + direction * foot_len,
                contact_y,
            ),
            fill=(222, 222, 222) if is_near else (242, 242, 242),
            width=max(1, round(scale * 0.004)),
        )


def _draw_vace_walk_confidence_hint(
    draw: ImageDraw.ImageDraw,
    points: dict[str, tuple[int, int]],
    confidence: dict[str, float],
    width: int,
    height: int,
) -> None:
    scale = min(width, height)
    center_x = round((points["left_hip"][0] + points["right_hip"][0] + points["neck"][0]) / 3)
    hip_y = round((points["left_hip"][1] + points["right_hip"][1]) / 2)
    right_forward = points["right_ankle"][0] >= points["left_ankle"][0]
    pelvis_confidence = _joint_confidence(confidence, "left_hip", "right_hip")
    pelvis_width = max(4, round(scale * (0.022 + pelvis_confidence * 0.020)))
    pelvis_value = _confidence_gray(238, 210, pelvis_confidence)
    draw.rounded_rectangle(
        (
            center_x - pelvis_width,
            hip_y - round(scale * 0.010),
            center_x + pelvis_width,
            hip_y + round(scale * 0.018),
        ),
        radius=max(2, round(scale * 0.010)),
        fill=(pelvis_value, pelvis_value, pelvis_value),
    )
    for hip, knee, ankle, is_near in (
        ("right_hip", "right_knee", "right_ankle", right_forward),
        ("left_hip", "left_knee", "left_ankle", not right_forward),
    ):
        leg_confidence = _joint_confidence(confidence, hip, knee, ankle)
        near_boost = 1.0 if is_near else 0.78
        width_px = max(2, round(scale * (0.010 + leg_confidence * 0.018) * near_boost))
        value = _confidence_gray(244 if is_near else 248, 184 if is_near else 214, leg_confidence)
        start = (center_x, points[hip][1])
        end = points[ankle]
        _draw_depth_limb(draw, start, points[knee], end, (value, value, value), width_px)
        foot_confidence = min(confidence.get(ankle, leg_confidence), leg_confidence)
        foot_len = round(scale * (0.036 + foot_confidence * 0.026) * near_boost)
        direction = 1 if end[0] >= center_x else -1
        contact_y = min(height - 1, end[1] + round(scale * 0.014))
        contact_value = _confidence_gray(248 if is_near else 252, 205 if is_near else 230, foot_confidence)
        contact_width = max(1, round(scale * (0.003 + foot_confidence * 0.004)))
        draw.line(
            (
                end[0] - round(foot_len * 0.45),
                contact_y,
                end[0] + direction * foot_len,
                contact_y,
            ),
            fill=(contact_value, contact_value, contact_value),
            width=contact_width,
        )


def _joint_confidence(confidence: dict[str, float], *names: str) -> float:
    if not names:
        return 1.0
    return min(max(0.0, min(1.0, confidence.get(name, 1.0))) for name in names)


def _confidence_gray(low_confidence_gray: int, high_confidence_gray: int, confidence: float) -> int:
    confidence = max(0.0, min(1.0, confidence))
    return round(low_confidence_gray * (1.0 - confidence) + high_confidence_gray * confidence)


def _draw_depth_limb(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    mid: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    width: int,
) -> None:
    draw.line([start, mid, end], fill=color, width=width, joint="curve")
    radius = max(2, round(width * 0.48))
    for x, y in (start, mid, end):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def _blend_color(
    background: tuple[int, int, int],
    foreground: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(round(background[index] * (1.0 - amount) + foreground[index] * amount) for index in range(3))


def write_default_templates(root: Path, frame_count: int = 120, width: int = 512, height: int = 512) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    written: dict[str, Any] = {}
    for name in ("walk", "run", "idle", "attack_sword", "attack_axe", "attack_bow", "hit_light", "hit_heavy", "hit_knockback"):
        action_dir = root / name
        render_dir = action_dir / "controlnet"
        action_dir.mkdir(parents=True, exist_ok=True)
        render_dir.mkdir(parents=True, exist_ok=True)
        frame_paths: list[Path] = []
        for index, frame in enumerate(_default_sequence(name, frame_count)):
            json_path = action_dir / f"frame_{index:03d}.json"
            image_path = render_dir / f"frame_{index:03d}.png"
            json_path.write_text(json.dumps(frame.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            render_pose_frame(frame.to_dict(), width, height).save(image_path)
            frame_paths.append(image_path)
        contact_sheet = make_contact_sheet(frame_paths, action_dir / "contact_sheet.png")
        written[name] = {
            "frames": [str(path) for path in frame_paths],
            "contact_sheet": str(contact_sheet),
        }
    index_path = root / "index.json"
    index_path.write_text(json.dumps(written, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return written


def _default_sequence(name: str, frame_count: int) -> list[PoseFrame]:
    return [_pose_for(name, index, frame_count) for index in range(frame_count)]


def _pose_for(name: str, index: int, count: int) -> PoseFrame:
    phase_t = index / max(1, count - 1)
    action, variant = _split_name(name)
    phase = _phase_for(name, phase_t)
    base = _base_points()
    if name == "walk":
        _walk_points(base, phase_t)
    elif name == "run":
        _run_points(base, phase_t)
    elif name == "idle":
        _idle_points(base, phase_t)
    elif name.startswith("attack_"):
        _attack_points(base, phase_t, variant)
    elif name.startswith("hit_"):
        _hit_points(base, phase_t, variant)
    return PoseFrame(action=action, variant=variant, frame_index=index, phase=phase, keypoints=base, notes=f"{name} {phase}")


def _split_name(name: str) -> tuple[str, str]:
    if name.startswith("attack_"):
        return "attack", name.removeprefix("attack_")
    if name.startswith("hit_"):
        return "hit", name.removeprefix("hit_")
    return name, name


def _phase_for(name: str, t: float) -> str:
    if name == "run":
        return ["contact", "drive", "flight", "recover"][min(3, int(t * 4))]
    if name in {"walk", "idle"}:
        return ["contact", "down", "passing", "up"][min(3, int(t * 4))]
    if name.startswith("attack_"):
        if t < 0.2:
            return "ready"
        if t < 0.38:
            return "anticipation"
        if t < 0.56:
            return "active"
        if t < 0.78:
            return "follow_through"
        return "recover"
    if t < 0.18:
        return "neutral"
    if t < 0.38:
        return "impact"
    if t < 0.62:
        return "recoil"
    if t < 0.82:
        return "peak"
    return "recover"


def _base_points() -> dict[str, list[float]]:
    return {
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


def _walk_points(points: dict[str, list[float]], t: float) -> None:
    import math

    phase = math.sin(t * math.tau)
    counter = math.sin(t * math.tau + math.pi)
    points["left_knee"][0] += phase * 0.07
    points["left_ankle"][0] += phase * 0.12
    points["left_ankle"][1] -= max(0.0, phase) * 0.05
    points["right_knee"][0] += counter * 0.07
    points["right_ankle"][0] += counter * 0.12
    points["right_ankle"][1] -= max(0.0, counter) * 0.05
    points["left_wrist"][0] -= phase * 0.08
    points["right_wrist"][0] -= counter * 0.08


def _run_points(points: dict[str, list[float]], t: float) -> None:
    import math

    phase = math.sin(t * math.tau)
    counter = math.sin(t * math.tau + math.pi)
    lift = max(0.0, math.sin(t * math.tau * 2.0)) * 0.035
    lean = 0.045
    for name in ("nose", "neck", "right_shoulder", "left_shoulder", "right_hip", "left_hip"):
        points[name][0] += lean
        points[name][1] -= lift
    points["left_knee"][0] += phase * 0.12
    points["left_knee"][1] -= max(0.0, phase) * 0.045
    points["left_ankle"][0] += phase * 0.20
    points["left_ankle"][1] -= max(0.0, phase) * 0.10 + lift
    points["right_knee"][0] += counter * 0.12
    points["right_knee"][1] -= max(0.0, counter) * 0.045
    points["right_ankle"][0] += counter * 0.20
    points["right_ankle"][1] -= max(0.0, counter) * 0.10 + lift
    points["left_elbow"][0] -= phase * 0.10
    points["left_wrist"][0] -= phase * 0.16
    points["left_wrist"][1] += phase * 0.04
    points["right_elbow"][0] -= counter * 0.10
    points["right_wrist"][0] -= counter * 0.16
    points["right_wrist"][1] += counter * 0.04


def _idle_points(points: dict[str, list[float]], t: float) -> None:
    import math

    breath = math.sin(t * math.tau) * 0.015
    for name in ("nose", "neck", "right_shoulder", "left_shoulder"):
        points[name][1] += breath


def _attack_points(points: dict[str, list[float]], t: float, variant: str) -> None:
    windup = min(1.0, max(0.0, t / 0.34))
    strike = min(1.0, max(0.0, (t - 0.30) / 0.22))
    recover = min(1.0, max(0.0, (t - 0.62) / 0.38))
    if variant == "bow":
        draw = min(1.0, max(0.0, t / 0.45))
        points["left_wrist"] = [0.31, 0.45]
        points["right_wrist"] = [0.70 - draw * 0.28 + strike * 0.24, 0.45]
        points["left_elbow"] = [0.36, 0.42]
        points["right_elbow"] = [0.60 - draw * 0.08 + strike * 0.10, 0.43]
    else:
        heavy = 1.25 if variant == "axe" else 1.0
        points["right_wrist"] = [0.67 - windup * 0.28 + strike * 0.34 * heavy - recover * 0.08, 0.54 - windup * 0.18 + strike * 0.05]
        points["right_elbow"] = [0.62 - windup * 0.16 + strike * 0.18 * heavy, 0.46 - windup * 0.10]
        points["left_wrist"] = [0.34 - windup * 0.08 + strike * 0.12, 0.58 - windup * 0.08]
    points["neck"][0] += strike * 0.04
    points["nose"][0] += strike * 0.04


def _hit_points(points: dict[str, list[float]], t: float, variant: str) -> None:
    strength = {"light": 0.04, "heavy": 0.09, "knockback": 0.16}.get(variant, 0.06)
    impact = min(1.0, max(0.0, (t - 0.12) / 0.30))
    recover = min(1.0, max(0.0, (t - 0.58) / 0.42))
    offset = impact * strength * (1.0 - recover)
    lift = 0.06 if variant == "knockback" and 0.25 < t < 0.60 else 0.0
    for point in points.values():
        point[0] += offset
        point[1] -= lift
    points["nose"][0] += offset * 0.6
    points["left_wrist"][0] -= offset * 1.4
    points["right_wrist"][0] -= offset * 1.2


def _draw_bone(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    *,
    width: int = 6,
    radius: int = 5,
) -> None:
    draw.line([start, end], fill=color, width=width)
    draw.ellipse((start[0] - radius, start[1] - radius, start[0] + radius, start[1] + radius), fill=color)
    draw.ellipse((end[0] - radius, end[1] - radius, end[0] + radius, end[1] + radius), fill=color)
