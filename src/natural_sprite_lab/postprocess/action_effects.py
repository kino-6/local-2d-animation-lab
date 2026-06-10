from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from natural_sprite_lab.models import Action


def make_action_effect_layers(
    frame_paths: list[Path],
    frame_plan: list[dict[str, Any]],
    action: Action,
    effects_dir: Path,
    composited_dir: Path,
) -> tuple[list[Path], list[Path]]:
    """Create transparent action cue layers and preview composites for game export."""

    if action not in {Action.ATTACK, Action.HIT}:
        return [], []
    effects_dir.mkdir(parents=True, exist_ok=True)
    composited_dir.mkdir(parents=True, exist_ok=True)

    effect_paths: list[Path] = []
    composited_paths: list[Path] = []
    for index, frame_path in enumerate(frame_paths):
        frame = Image.open(frame_path).convert("RGBA")
        plan = frame_plan[index % len(frame_plan)] if frame_plan else {}
        label = str(plan.get("label", ""))
        effect = _effect_for_label(label, frame.size)
        effect_path = effects_dir / f"{frame_path.stem}_effect.png"
        effect.save(effect_path)

        composite = Image.alpha_composite(frame, effect)
        composite_path = composited_dir / f"{frame_path.stem}_with_effect.png"
        composite.save(composite_path)
        effect_paths.append(effect_path)
        composited_paths.append(composite_path)

    return effect_paths, composited_paths


def _effect_for_label(label: str, size: tuple[int, int]) -> Image.Image:
    effect = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(effect, "RGBA")
    width, height = size
    cx = width // 2
    cy = int(height * 0.48)

    if label.startswith("attack_sword"):
        _draw_sword_slash(draw, width, height, label)
    elif label.startswith("attack_axe"):
        _draw_axe_impact(draw, width, height, label)
    elif label.startswith("attack_bow"):
        _draw_bow_arrow(draw, width, height, label)
    elif label.startswith("hit_knockback"):
        if any(token in label for token in ("impact", "airborne", "peak", "fall", "land")):
            _draw_hit_burst(draw, cx - int(width * 0.18), cy, width, height, intensity=1.0)
        if any(token in label for token in ("airborne", "peak", "fall")):
            _draw_motion_streaks(draw, width, height, strong=True)
    elif label.startswith("hit_heavy"):
        if any(token in label for token in ("impact", "recoil", "peak", "collapse")):
            _draw_hit_burst(draw, cx - int(width * 0.14), cy, width, height, intensity=0.82)
        if any(token in label for token in ("recoil", "peak")):
            _draw_motion_streaks(draw, width, height, strong=False)
    elif label.startswith("hit_light"):
        if any(token in label for token in ("impact", "recoil", "peak")):
            _draw_hit_burst(draw, cx - int(width * 0.10), cy, width, height, intensity=0.55)

    return effect.filter(ImageFilter.GaussianBlur(radius=0.15))


def _draw_sword_slash(draw: ImageDraw.ImageDraw, width: int, height: int, label: str) -> None:
    if not any(token in label for token in ("start", "impact", "follow")):
        return
    box = (
        int(width * 0.33),
        int(height * 0.20),
        int(width * 0.78),
        int(height * 0.72),
    )
    draw.arc(box, start=225, end=318, fill=(88, 220, 255, 210), width=max(8, width // 60))
    draw.arc(box, start=230, end=312, fill=(255, 255, 255, 190), width=max(3, width // 130))


def _draw_axe_impact(draw: ImageDraw.ImageDraw, width: int, height: int, label: str) -> None:
    if not any(token in label for token in ("overhead", "impact", "follow")):
        return
    x = int(width * 0.61)
    top = int(height * 0.18)
    bottom = int(height * 0.72)
    draw.line([(x, top), (x - int(width * 0.08), bottom)], fill=(255, 255, 255, 170), width=max(6, width // 80))
    draw.line([(x + 18, top + 20), (x - int(width * 0.08) + 18, bottom)], fill=(255, 190, 80, 190), width=max(4, width // 120))
    if "impact" in label or "follow" in label:
        y = int(height * 0.74)
        draw.line([(x - 70, y), (x + 80, y - 24)], fill=(255, 210, 80, 190), width=max(5, width // 110))
        draw.line([(x - 40, y + 12), (x + 54, y + 8)], fill=(255, 255, 255, 150), width=max(3, width // 150))


def _draw_bow_arrow(draw: ImageDraw.ImageDraw, width: int, height: int, label: str) -> None:
    y = int(height * 0.34)
    start_x = int(width * 0.48)
    end_x = int(width * 0.82)
    if any(token in label for token in ("aim", "release", "follow")):
        draw.line([(start_x, y), (end_x, y - 12)], fill=(255, 255, 255, 220), width=max(3, width // 180))
        draw.polygon(
            [(end_x, y - 12), (end_x - 20, y - 22), (end_x - 15, y - 4)],
            fill=(255, 255, 255, 220),
        )
    if "release" in label or "follow" in label:
        for offset in (18, 38, 58):
            draw.line(
                [(start_x - offset, y + offset // 8), (start_x - offset + 34, y - 8 + offset // 8)],
                fill=(130, 220, 255, 120),
                width=2,
            )


def _draw_hit_burst(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    width: int,
    height: int,
    intensity: float,
) -> None:
    radius = int(min(width, height) * 0.10 * intensity)
    for index in range(10):
        angle = index / 10
        dx = int(radius * (1.0 + angle) * (1 if index % 2 == 0 else -1))
        dy = int(radius * (0.35 + angle) * (1 if index < 5 else -1))
        draw.line([(cx, cy), (cx + dx, cy + dy)], fill=(255, 225, 80, 210), width=max(3, width // 150))
    draw.ellipse((cx - radius // 2, cy - radius // 2, cx + radius // 2, cy + radius // 2), fill=(255, 90, 80, 150))


def _draw_motion_streaks(draw: ImageDraw.ImageDraw, width: int, height: int, strong: bool) -> None:
    count = 5 if strong else 3
    alpha = 150 if strong else 105
    for index in range(count):
        y = int(height * (0.30 + index * 0.08))
        draw.line(
            [(int(width * 0.08), y), (int(width * 0.35), y + int(height * 0.05))],
            fill=(130, 210, 255, alpha),
            width=max(3, width // 140),
        )
