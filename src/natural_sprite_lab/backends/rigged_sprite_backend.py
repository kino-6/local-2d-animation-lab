from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from natural_sprite_lab.backends.base import AnimationBackend
from natural_sprite_lab.models import Action, AnimationSpec, GeneratedFrames
from natural_sprite_lab.utils.paths import frame_filename


class RiggedSpriteBackend(AnimationBackend):
    """Generate coherent 2D puppet animation frames from a local procedural rig."""

    name = "rigged-sprite"

    def __init__(self, width: int = 512, height: int = 512) -> None:
        self.width = width
        self.height = height

    def generate_frames(
        self,
        source_image: Path,
        spec: AnimationSpec,
        frames_dir: Path,
        retake: int = 1,
    ) -> GeneratedFrames:
        frames_dir.mkdir(parents=True, exist_ok=True)
        palette = _palette_from_reference(source_image)
        rig_frames = _motion_frames(spec)
        frame_paths: list[Path] = []
        for index, rig in enumerate(rig_frames):
            image = _draw_frame(self.width, self.height, palette, rig)
            path = frames_dir / frame_filename(spec.character_id, spec.action.value, index, retake)
            image.save(path)
            frame_paths.append(path)

        return GeneratedFrames(
            frame_paths=frame_paths,
            backend_name=self.name,
            backend_metadata={
                "description": "Procedural 2D puppet rig. Uses a stable part hierarchy for animation-valid frames.",
                "source_image": str(source_image),
                "frame_width": self.width,
                "frame_height": self.height,
                "palette": palette,
                "rig_frames": rig_frames,
                "validation_intent": (
                    "This backend is intended as a practical animation baseline: temporal coherence, "
                    "loop closure, and stable character parts are prioritized over model-rendered image polish."
                ),
            },
        )


def _palette_from_reference(source_image: Path) -> dict[str, tuple[int, int, int, int]]:
    image = Image.open(source_image).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    visible = image.crop(bbox) if bbox else image
    stat = ImageStat.Stat(visible.convert("RGB"))
    mean = tuple(max(0, min(255, int(value))) for value in stat.mean)
    hair = _darken(mean, 0.55)
    outfit = _darken(mean, 0.28)
    accent = (208, 44, 52, 255)
    skin = (241, 198, 170, 255)
    white = (246, 250, 253, 255)
    return {
        "hair": (*hair, 255),
        "skin": skin,
        "shirt": white,
        "skirt": (*outfit, 255),
        "accent": accent,
        "sock": (23, 43, 70, 255),
        "shoe": (102, 62, 32, 255),
        "line": (43, 35, 32, 255),
        "effect": (88, 220, 255, 210),
    }


def _motion_frames(spec: AnimationSpec) -> list[dict[str, Any]]:
    count = spec.frame_count
    if spec.action == Action.IDLE:
        return [_idle_pose(index, count) for index in range(count)]
    if spec.action == Action.ATTACK:
        return [_attack_pose(index, count, _variant(spec)) for index in range(count)]
    if spec.action == Action.HIT:
        return [_hit_pose(index, count, _variant(spec)) for index in range(count)]
    return [_walk_pose(index, count) for index in range(count)]


def _variant(spec: AnimationSpec) -> str:
    if spec.frame_plan:
        return str(spec.frame_plan[0].get("action_variant", spec.action.value))
    return spec.action.value


def _walk_pose(index: int, count: int) -> dict[str, Any]:
    phase = index / max(1, count - 1) * math.tau
    left_swing = max(0.0, math.sin(phase))
    right_swing = max(0.0, math.sin(phase + math.pi))
    return {
        "label": "walk",
        "root": [0.0, math.sin(phase * 2) * 3],
        "torso": math.sin(phase) * 3,
        "head": -math.sin(phase) * 2,
        "left_foot": [math.sin(phase) * 48 - 20, -left_swing * 34],
        "right_foot": [math.sin(phase + math.pi) * 48 + 20, -right_swing * 34],
        "left_hand": [math.sin(phase + math.pi) * 34 - 34, 92],
        "right_hand": [math.sin(phase) * 34 + 34, 92],
        "effect": "none",
        "prop": "none",
    }


def _idle_pose(index: int, count: int) -> dict[str, Any]:
    phase = index / count * math.tau
    return {
        "label": "idle",
        "root": [0.0, math.sin(phase) * 3],
        "torso": math.sin(phase) * 1.5,
        "head": math.sin(phase) * 1.0,
        "left_foot": [-18, 0],
        "right_foot": [20, 0],
        "left_hand": [-40 + math.sin(phase) * 3, 95],
        "right_hand": [40 - math.sin(phase) * 3, 95],
        "effect": "none",
        "prop": "none",
    }


def _attack_pose(index: int, count: int, variant: str) -> dict[str, Any]:
    t = index / max(1, count - 1)
    windup = math.sin(min(t, 0.34) / 0.34 * math.pi) if t < 0.34 else 0.0
    strike = math.sin(max(0.0, min(1.0, (t - 0.24) / 0.30)) * math.pi)
    recover = max(0.0, (t - 0.56) / 0.44)
    heavy = 1.35 if variant == "axe" else 1.0
    bow = variant == "bow"
    bow_draw = min(1.0, max(0.0, t / 0.42))
    bow_release = max(0.0, min(1.0, (t - 0.42) / 0.18))
    return {
        "label": f"attack_{variant}",
        "root": [strike * 24 * heavy - recover * 10, strike * 2],
        "torso": -windup * 16 + strike * 22 * heavy,
        "head": -strike * 5,
        "left_foot": [-42 - windup * 14 + strike * 36, 0],
        "right_foot": [38 + strike * 18, 0],
        "left_hand": ([-86, 54] if bow else [-62 - windup * 34 + strike * 80 * heavy, 50 - windup * 58 + strike * 6]),
        "right_hand": ([88 - bow_draw * 72 + bow_release * 86, 58 + bow_draw * 4] if bow else [48 - windup * 48 + strike * 112 * heavy, 52 + strike * 12]),
        "effect": "arrow" if bow and 0.28 <= t <= 0.62 else ("slash" if 0.30 <= t <= 0.68 else "none"),
        "prop": variant,
    }


def _hit_pose(index: int, count: int, variant: str) -> dict[str, Any]:
    t = index / max(1, count - 1)
    impact = math.sin(min(1.0, t / 0.38) * math.pi)
    recover = max(0.0, (t - 0.45) / 0.55)
    strength = {"light": 0.55, "heavy": 1.05, "knockback": 1.65}.get(variant, 0.75)
    airborne = -42 * strength if variant == "knockback" and 0.22 <= t <= 0.58 else 0.0
    recoil = impact * strength * (1.0 - recover * 0.55)
    slide = 48 * strength if variant == "knockback" else 24 * strength
    return {
        "label": f"hit_{variant}",
        "root": [recoil * slide, airborne + recoil * 8],
        "torso": -recoil * 25,
        "head": -recoil * 20,
        "left_foot": [-32 - recoil * 32, 0 if airborne == 0 else airborne * 0.25],
        "right_foot": [34 - recoil * 20, 0 if airborne == 0 else airborne * 0.25],
        "left_hand": [-58 - recoil * 48, 68 - recoil * 24],
        "right_hand": [46 - recoil * 42, 76 - recoil * 18],
        "effect": "hit" if 0.08 <= t <= 0.58 else "none",
        "prop": "none",
    }


def _draw_frame(width: int, height: int, palette: dict[str, tuple[int, int, int, int]], pose: dict[str, Any]) -> Image.Image:
    scale = 3
    canvas = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    cx = width * scale // 2 + int(float(pose["root"][0]) * scale)
    ground = int(height * 0.86) * scale + int(float(pose["root"][1]) * scale)
    hip = (cx, ground - int(height * 0.31 * scale))
    neck = (cx + int(float(pose["torso"]) * scale), ground - int(height * 0.55 * scale))
    head = (neck[0] + int(float(pose["head"]) * scale), neck[1] - int(height * 0.105 * scale))

    left_foot = _target_from(hip, ground, pose, "left_foot", scale, default_angle=float(pose.get("left_leg", 0)), default_side=-1)
    right_foot = _target_from(hip, ground, pose, "right_foot", scale, default_angle=float(pose.get("right_leg", 0)), default_side=1)
    left_hand = _target_from(neck, neck[1], pose, "left_hand", scale, default_angle=float(pose.get("left_arm", 0)), default_side=-1, arm=True)
    right_hand = _target_from(neck, neck[1], pose, "right_hand", scale, default_angle=float(pose.get("right_arm", 0)), default_side=1, arm=True)

    _shadow(draw, cx, ground, width, scale)
    _draw_effect(draw, pose, palette, cx, neck, right_hand, width, height, scale)
    _draw_prop(draw, pose, palette, left_hand, right_hand, neck, scale)
    _limb(draw, hip, left_foot, palette["skin"], palette["line"], scale, width=12)
    _limb(draw, hip, right_foot, palette["skin"], palette["line"], scale, width=12)
    _shoe(draw, left_foot, palette, scale)
    _shoe(draw, right_foot, palette, scale)
    _body(draw, hip, neck, palette, scale)
    draw.line([(neck[0], neck[1] - 4 * scale), (head[0], head[1] + 36 * scale)], fill=palette["skin"], width=12 * scale)
    _limb(draw, neck, left_hand, palette["shirt"], palette["line"], scale, width=11)
    _limb(draw, neck, right_hand, palette["shirt"], palette["line"], scale, width=11)
    _hand(draw, left_hand, palette, scale)
    _hand(draw, right_hand, palette, scale)
    _head(draw, head, palette, scale)

    return canvas.resize((width, height), Image.Resampling.LANCZOS).filter(ImageFilter.UnsharpMask(radius=0.6, percent=80))


def _limb_end(origin: tuple[int, int], angle_degrees: float, length: int, side: int) -> tuple[int, int]:
    angle = math.radians(90 + angle_degrees)
    return (
        origin[0] + int(math.cos(angle) * length * 0.62) + side * 10,
        origin[1] + int(math.sin(angle) * length),
    )


def _target_from(
    origin: tuple[int, int],
    ground_or_origin_y: int,
    pose: dict[str, Any],
    key: str,
    scale: int,
    default_angle: float,
    default_side: int,
    arm: bool = False,
) -> tuple[int, int]:
    value = pose.get(key)
    if isinstance(value, list | tuple) and len(value) == 2:
        if arm:
            return origin[0] + int(float(value[0]) * scale), origin[1] + int(float(value[1]) * scale)
        return origin[0] + int(float(value[0]) * scale), ground_or_origin_y + int(float(value[1]) * scale)
    length = 96 * scale if arm else 132 * scale
    return _limb_end(origin, default_angle, length, default_side)


def _limb(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: tuple[int, int, int, int],
    line: tuple[int, int, int, int],
    scale: int,
    width: int,
) -> None:
    draw.line([start, end], fill=line, width=width * scale + 4 * scale)
    draw.line([start, end], fill=fill, width=width * scale)


def _body(draw: ImageDraw.ImageDraw, hip: tuple[int, int], neck: tuple[int, int], palette: dict[str, tuple[int, int, int, int]], scale: int) -> None:
    torso = [(neck[0] - 34 * scale, neck[1]), (neck[0] + 34 * scale, neck[1]), (hip[0] + 40 * scale, hip[1]), (hip[0] - 40 * scale, hip[1])]
    draw.polygon(torso, fill=palette["line"])
    inset = [(x + (3 * scale if x < hip[0] else -3 * scale), y + 3 * scale) for x, y in torso]
    draw.polygon(inset, fill=palette["shirt"])
    skirt = [(hip[0] - 50 * scale, hip[1] - 5 * scale), (hip[0] + 50 * scale, hip[1] - 5 * scale), (hip[0] + 68 * scale, hip[1] + 58 * scale), (hip[0] - 68 * scale, hip[1] + 58 * scale)]
    draw.polygon(skirt, fill=palette["line"])
    draw.polygon([(x, y + 3 * scale) for x, y in skirt], fill=palette["skirt"])
    draw.line([(neck[0], neck[1] + 10 * scale), (hip[0], hip[1] - 8 * scale)], fill=palette["accent"], width=8 * scale)


def _head(draw: ImageDraw.ImageDraw, head: tuple[int, int], palette: dict[str, tuple[int, int, int, int]], scale: int) -> None:
    r = 38 * scale
    draw.ellipse((head[0] - r, head[1] - r, head[0] + r, head[1] + r), fill=palette["line"])
    draw.ellipse((head[0] - r + 4 * scale, head[1] - r + 4 * scale, head[0] + r - 4 * scale, head[1] + r - 4 * scale), fill=palette["skin"])
    hair = [(head[0] - r, head[1] - r // 2), (head[0] - r // 2, head[1] - r), (head[0] + r, head[1] - r // 2), (head[0] + r // 2, head[1] + r // 3), (head[0] - r, head[1] + r // 4)]
    draw.polygon(hair, fill=palette["hair"])
    draw.ellipse((head[0] + 12 * scale, head[1] - 6 * scale, head[0] + 20 * scale, head[1] + 4 * scale), fill=(240, 180, 70, 255))
    draw.line([(head[0] + 18 * scale, head[1] + 18 * scale), (head[0] + 32 * scale, head[1] + 18 * scale)], fill=palette["line"], width=2 * scale)


def _hand(draw: ImageDraw.ImageDraw, hand: tuple[int, int], palette: dict[str, tuple[int, int, int, int]], scale: int) -> None:
    r = 7 * scale
    draw.ellipse((hand[0] - r, hand[1] - r, hand[0] + r, hand[1] + r), fill=palette["skin"])


def _shoe(draw: ImageDraw.ImageDraw, foot: tuple[int, int], palette: dict[str, tuple[int, int, int, int]], scale: int) -> None:
    draw.ellipse((foot[0] - 20 * scale, foot[1] - 6 * scale, foot[0] + 22 * scale, foot[1] + 8 * scale), fill=palette["shoe"])


def _shadow(draw: ImageDraw.ImageDraw, cx: int, ground: int, width: int, scale: int) -> None:
    draw.ellipse((cx - width // 7 * scale, ground - 8 * scale, cx + width // 7 * scale, ground + 12 * scale), fill=(0, 0, 0, 35))


def _draw_effect(
    draw: ImageDraw.ImageDraw,
    pose: dict[str, Any],
    palette: dict[str, tuple[int, int, int, int]],
    cx: int,
    neck: tuple[int, int],
    right_hand: tuple[int, int],
    width: int,
    height: int,
    scale: int,
) -> None:
    effect = pose.get("effect")
    if effect == "slash":
        box = (cx - 30 * scale, neck[1] - 90 * scale, cx + 165 * scale, neck[1] + 135 * scale)
        draw.arc(box, 215, 330, fill=palette["effect"], width=10 * scale)
    elif effect == "arrow":
        end = (right_hand[0] + int(width * 0.28 * scale), right_hand[1] - 8 * scale)
        draw.line([right_hand, end], fill=(255, 255, 255, 230), width=4 * scale)
        draw.polygon([(end[0], end[1]), (end[0] - 18 * scale, end[1] - 8 * scale), (end[0] - 14 * scale, end[1] + 8 * scale)], fill=(255, 255, 255, 230))
    elif effect == "hit":
        center = (cx - int(width * 0.16 * scale), int(height * 0.45 * scale))
        for i in range(8):
            angle = i / 8 * math.tau
            end = (center[0] + int(math.cos(angle) * 42 * scale), center[1] + int(math.sin(angle) * 30 * scale))
            draw.line([center, end], fill=(255, 220, 80, 210), width=4 * scale)
        draw.ellipse((center[0] - 18 * scale, center[1] - 18 * scale, center[0] + 18 * scale, center[1] + 18 * scale), fill=(255, 90, 80, 150))


def _draw_prop(
    draw: ImageDraw.ImageDraw,
    pose: dict[str, Any],
    palette: dict[str, tuple[int, int, int, int]],
    left_hand: tuple[int, int],
    right_hand: tuple[int, int],
    neck: tuple[int, int],
    scale: int,
) -> None:
    prop = pose.get("prop")
    line = palette["line"]
    if prop == "sword":
        tip = (right_hand[0] + 64 * scale, right_hand[1] - 42 * scale)
        draw.line([right_hand, tip], fill=line, width=8 * scale)
        draw.line([right_hand, tip], fill=(210, 230, 245, 255), width=4 * scale)
        draw.line([(right_hand[0] - 12 * scale, right_hand[1] + 8 * scale), (right_hand[0] + 12 * scale, right_hand[1] - 8 * scale)], fill=line, width=4 * scale)
    elif prop == "axe":
        haft_end = (right_hand[0] + 40 * scale, right_hand[1] - 80 * scale)
        draw.line([right_hand, haft_end], fill=(118, 78, 38, 255), width=7 * scale)
        blade = [
            (haft_end[0] - 12 * scale, haft_end[1] - 20 * scale),
            (haft_end[0] + 38 * scale, haft_end[1] - 10 * scale),
            (haft_end[0] + 30 * scale, haft_end[1] + 32 * scale),
            (haft_end[0] - 8 * scale, haft_end[1] + 18 * scale),
        ]
        draw.polygon(blade, fill=line)
        draw.polygon([(x - 3 * scale, y + 2 * scale) for x, y in blade], fill=(205, 215, 220, 255))
    elif prop == "bow":
        bow_top = (left_hand[0] - 24 * scale, left_hand[1] - 78 * scale)
        bow_bottom = (left_hand[0] - 24 * scale, left_hand[1] + 78 * scale)
        draw.arc((bow_top[0] - 35 * scale, bow_top[1], bow_bottom[0] + 45 * scale, bow_bottom[1]), -82, 82, fill=line, width=7 * scale)
        draw.line([bow_top, right_hand, bow_bottom], fill=(235, 235, 235, 210), width=2 * scale)
        draw.line([(right_hand[0], right_hand[1]), (right_hand[0] + 80 * scale, right_hand[1])], fill=(245, 245, 245, 230), width=3 * scale)


def _darken(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel * factor))) for channel in rgb)
