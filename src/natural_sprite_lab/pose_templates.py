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
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "variant": self.variant,
            "frame_index": self.frame_index,
            "phase": self.phase,
            "keypoints": self.keypoints,
            "notes": self.notes,
        }


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


def render_pose_frame(frame: dict[str, Any], width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    points = {
        name: (int(float(point[0]) * width), int(float(point[1]) * height))
        for name, point in frame["keypoints"].items()
    }
    for start, end, color in BONES:
        _draw_bone(draw, points[start], points[end], color)
    return image


def write_default_templates(root: Path, frame_count: int = 120, width: int = 512, height: int = 512) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    written: dict[str, Any] = {}
    for name in ("walk", "idle", "attack_sword", "attack_axe", "attack_bow", "hit_light", "hit_heavy", "hit_knockback"):
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


def _draw_bone(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]) -> None:
    draw.line([start, end], fill=color, width=6)
    radius = 5
    draw.ellipse((start[0] - radius, start[1] - radius, start[0] + radius, start[1] + radius), fill=color)
    draw.ellipse((end[0] - radius, end[1] - radius, end[0] + radius, end[1] + radius), fill=color)
