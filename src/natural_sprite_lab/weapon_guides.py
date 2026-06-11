from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet


@dataclass(frozen=True)
class WeaponGuideFrame:
    weapon: str
    frame_index: int
    phase: str
    anchors: dict[str, list[float]]
    lines: list[dict[str, Any]]
    arcs: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_default_weapon_guides(
    root: Path,
    frame_count: int = 120,
    width: int = 512,
    height: int = 512,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    written: dict[str, Any] = {}
    for weapon in ("sword", "axe", "bow"):
        weapon_dir = root / weapon
        render_dir = weapon_dir / "control"
        weapon_dir.mkdir(parents=True, exist_ok=True)
        render_dir.mkdir(parents=True, exist_ok=True)
        frame_paths = []
        for index in range(frame_count):
            frame = weapon_guide_for(weapon, index, frame_count)
            json_path = weapon_dir / f"frame_{index:03d}.json"
            image_path = render_dir / f"frame_{index:03d}.png"
            json_path.write_text(json.dumps(frame.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            render_weapon_guide(frame, width, height).save(image_path)
            frame_paths.append(image_path)
        contact_sheet = make_contact_sheet(frame_paths, weapon_dir / "contact_sheet.png")
        written[weapon] = {"frames": [str(path) for path in frame_paths], "contact_sheet": str(contact_sheet)}
    index_path = root / "index.json"
    index_path.write_text(json.dumps(written, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return written


def weapon_guide_for(weapon: str, index: int, count: int) -> WeaponGuideFrame:
    t = index / max(1, count - 1)
    if weapon == "sword":
        return _sword_frame(index, t)
    if weapon == "axe":
        return _axe_frame(index, t)
    if weapon == "bow":
        return _bow_frame(index, t)
    raise ValueError(f"Unknown weapon guide: {weapon}")


def render_weapon_guide(frame: WeaponGuideFrame, width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    for line in frame.lines:
        start = _scale(frame.anchors[str(line["start"])], width, height)
        end = _scale(frame.anchors[str(line["end"])], width, height)
        draw.line([start, end], fill=tuple(line.get("color", (0, 220, 255))), width=int(line.get("width", 6)))
    for arc in frame.arcs:
        center = _scale(arc["center"], width, height)
        radius = arc["radius"]
        rx = int(float(radius[0]) * width)
        ry = int(float(radius[1]) * height)
        bbox = (center[0] - rx, center[1] - ry, center[0] + rx, center[1] + ry)
        draw.arc(
            bbox,
            start=float(arc["start_degrees"]),
            end=float(arc["end_degrees"]),
            fill=tuple(arc.get("color", (0, 180, 255))),
            width=int(arc.get("width", 5)),
        )
    for point in frame.anchors.values():
        x, y = _scale(point, width, height)
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 255, 255))
    return image


def _sword_frame(index: int, t: float) -> WeaponGuideFrame:
    phase = _attack_phase(t)
    angle = math.radians(-125 + 250 * min(1.0, max(0.0, (t - 0.20) / 0.55)))
    hand = [0.50 + 0.09 * math.sin(t * math.tau), 0.48 + 0.04 * math.cos(t * math.tau)]
    tip = [hand[0] + math.cos(angle) * 0.34, hand[1] + math.sin(angle) * 0.34]
    pommel = [hand[0] - math.cos(angle) * 0.06, hand[1] - math.sin(angle) * 0.06]
    return WeaponGuideFrame(
        weapon="sword",
        frame_index=index,
        phase=phase,
        anchors={"main_hand": hand, "blade_tip": tip, "pommel": pommel},
        lines=[{"start": "pommel", "end": "blade_tip", "width": 7, "color": [0, 240, 255]}],
        arcs=[
            {
                "center": [0.52, 0.48],
                "radius": [0.26, 0.24],
                "start_degrees": -130,
                "end_degrees": 90,
                "width": 5,
                "color": [0, 150, 255],
            }
        ]
        if phase in {"active", "follow_through"}
        else [],
    )


def _axe_frame(index: int, t: float) -> WeaponGuideFrame:
    phase = _attack_phase(t)
    angle = math.radians(-95 + 210 * min(1.0, max(0.0, (t - 0.16) / 0.62)))
    hand = [0.49 + 0.07 * math.sin(t * math.tau), 0.50]
    head = [hand[0] + math.cos(angle) * 0.30, hand[1] + math.sin(angle) * 0.30]
    butt = [hand[0] - math.cos(angle) * 0.12, hand[1] - math.sin(angle) * 0.12]
    return WeaponGuideFrame(
        weapon="axe",
        frame_index=index,
        phase=phase,
        anchors={"grip": hand, "head": head, "butt": butt},
        lines=[
            {"start": "butt", "end": "head", "width": 7, "color": [180, 120, 40]},
            {"start": "head", "end": "grip", "width": 11, "color": [190, 220, 230]},
        ],
        arcs=[
            {
                "center": [0.54, 0.54],
                "radius": [0.24, 0.30],
                "start_degrees": -115,
                "end_degrees": 80,
                "width": 6,
                "color": [255, 230, 120],
            }
        ]
        if phase in {"active", "follow_through"}
        else [],
    )


def _bow_frame(index: int, t: float) -> WeaponGuideFrame:
    phase = "draw" if t < 0.42 else "release" if t < 0.56 else "recover"
    bow_center = [0.43, 0.43]
    top = [bow_center[0], bow_center[1] - 0.20]
    bottom = [bow_center[0], bow_center[1] + 0.20]
    draw_hand = [0.67 - min(1.0, t / 0.42) * 0.25 + max(0.0, t - 0.56) * 0.18, 0.43]
    arrow_tip = [0.82, 0.43]
    return WeaponGuideFrame(
        weapon="bow",
        frame_index=index,
        phase=phase,
        anchors={"bow_top": top, "bow_bottom": bottom, "draw_hand": draw_hand, "arrow_tip": arrow_tip},
        lines=[
            {"start": "bow_top", "end": "draw_hand", "width": 3, "color": [230, 230, 230]},
            {"start": "bow_bottom", "end": "draw_hand", "width": 3, "color": [230, 230, 230]},
            {"start": "draw_hand", "end": "arrow_tip", "width": 4, "color": [255, 255, 120]},
        ],
        arcs=[
            {
                "center": bow_center,
                "radius": [0.08, 0.22],
                "start_degrees": -95,
                "end_degrees": 95,
                "width": 7,
                "color": [160, 90, 40],
            }
        ],
    )


def _attack_phase(t: float) -> str:
    if t < 0.20:
        return "ready"
    if t < 0.38:
        return "anticipation"
    if t < 0.58:
        return "active"
    if t < 0.78:
        return "follow_through"
    return "recover"


def _scale(point: list[float], width: int, height: int) -> tuple[int, int]:
    return int(point[0] * width), int(point[1] * height)
