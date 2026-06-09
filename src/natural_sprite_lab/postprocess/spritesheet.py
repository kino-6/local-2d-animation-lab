from __future__ import annotations

from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw


def make_sprite_sheet(frame_paths: list[Path], output_path: Path, columns: int | None = None) -> Path:
    frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    if not frames:
        raise ValueError("Cannot create sprite sheet without frames.")
    columns = columns or len(frames)
    rows = ceil(len(frames) / columns)
    width, height = frames[0].size
    sheet = Image.new("RGBA", (columns * width, rows * height), (0, 0, 0, 0))

    for index, frame in enumerate(frames):
        x = (index % columns) * width
        y = (index // columns) * height
        sheet.alpha_composite(frame, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path


def make_contact_sheet(frame_paths: list[Path], output_path: Path, columns: int = 4) -> Path:
    frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    if not frames:
        raise ValueError("Cannot create contact sheet without frames.")

    width, height = frames[0].size
    label_height = 24
    rows = ceil(len(frames) / columns)
    sheet = Image.new("RGBA", (columns * width, rows * (height + label_height)), (245, 245, 245, 255))
    draw = ImageDraw.Draw(sheet)

    for index, frame in enumerate(frames):
        x = (index % columns) * width
        y = (index // columns) * (height + label_height)
        sheet.alpha_composite(frame, (x, y))
        draw.text((x + 8, y + height + 4), f"frame {index:02d}", fill=(30, 30, 30, 255))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path
