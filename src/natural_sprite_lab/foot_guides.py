from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet


@dataclass(frozen=True)
class FootGuideFrame:
    action: str
    frame_index: int
    phase: str
    ground_y: float
    left_foot: dict[str, Any]
    right_foot: dict[str, Any]
    stride_envelope: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_default_foot_guides(
    root: Path,
    *,
    frame_count: int = 120,
    width: int = 512,
    height: int = 512,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    guide_dir = root / "walk"
    render_dir = guide_dir / "control"
    guide_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    frame_paths: list[Path] = []
    for index in range(frame_count):
        frame = walk_foot_guide_for(index, frame_count)
        json_path = guide_dir / f"frame_{index:03d}.json"
        image_path = render_dir / f"frame_{index:03d}.png"
        json_path.write_text(json.dumps(frame.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        render_foot_guide(frame, width, height).save(image_path)
        frame_paths.append(image_path)
    contact_sheet = make_contact_sheet(frame_paths, guide_dir / "contact_sheet.png", columns=12)
    written = {"walk": {"frames": [str(path) for path in frame_paths], "contact_sheet": str(contact_sheet)}}
    (root / "index.json").write_text(json.dumps(written, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return written


def walk_foot_guide_for(index: int, count: int) -> FootGuideFrame:
    t = index / max(1, count)
    phase = ["contact", "down", "passing", "up"][int((t * 4) % 4)]
    stride = 0.105
    lift = 0.045
    center_x = 0.50
    ground_y = 0.83
    left_phase = math.sin(math.tau * t)
    right_phase = math.sin(math.tau * (t + 0.5))
    left_x = center_x + stride * left_phase
    right_x = center_x + stride * right_phase
    left_y = ground_y - lift * max(0.0, -left_phase)
    right_y = ground_y - lift * max(0.0, -right_phase)
    return FootGuideFrame(
        action="walk",
        frame_index=index,
        phase=phase,
        ground_y=ground_y,
        left_foot=_foot_box(left_x, left_y, contact=left_y >= ground_y - 0.004),
        right_foot=_foot_box(right_x, right_y, contact=right_y >= ground_y - 0.004),
        stride_envelope={
            "left": round(center_x - stride - 0.045, 5),
            "right": round(center_x + stride + 0.045, 5),
            "top": round(ground_y - lift - 0.055, 5),
            "bottom": round(ground_y + 0.035, 5),
        },
    )


def render_foot_guide(frame: FootGuideFrame, width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    envelope = frame.stride_envelope
    draw.rectangle(
        (
            round(float(envelope["left"]) * width),
            round(float(envelope["top"]) * height),
            round(float(envelope["right"]) * width),
            round(float(envelope["bottom"]) * height),
        ),
        outline=(60, 90, 130),
        width=max(1, round(width * 0.006)),
    )
    ground = round(frame.ground_y * height)
    draw.line((0, ground, width, ground), fill=(80, 80, 80), width=max(1, round(width * 0.004)))
    _draw_foot(draw, frame.left_foot, width, height, color=(0, 210, 255))
    _draw_foot(draw, frame.right_foot, width, height, color=(255, 210, 0))
    return image


def _foot_box(x: float, y: float, *, contact: bool) -> dict[str, Any]:
    return {
        "center": [round(x, 5), round(y, 5)],
        "size": [0.075, 0.030],
        "contact": contact,
    }


def _draw_foot(draw: ImageDraw.ImageDraw, foot: dict[str, Any], width: int, height: int, *, color: tuple[int, int, int]) -> None:
    center_x, center_y = foot["center"]
    size_x, size_y = foot["size"]
    x0 = round((float(center_x) - float(size_x) / 2.0) * width)
    y0 = round((float(center_y) - float(size_y) / 2.0) * height)
    x1 = round((float(center_x) + float(size_x) / 2.0) * width)
    y1 = round((float(center_y) + float(size_y) / 2.0) * height)
    draw.ellipse((x0, y0, x1, y1), outline=color, width=max(2, round(width * 0.008)))
    if foot.get("contact"):
        draw.line((x0, y1 + 4, x1, y1 + 4), fill=color, width=max(1, round(width * 0.006)))
