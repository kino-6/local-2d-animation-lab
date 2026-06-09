from __future__ import annotations

from pathlib import Path

from PIL import Image


def make_preview_gif(
    frame_paths: list[Path],
    output_path: Path,
    duration_ms: int = 120,
    loop: bool = True,
) -> Path:
    frames = [_flatten_for_gif(Image.open(path).convert("RGBA")) for path in frame_paths]
    if not frames:
        raise ValueError("Cannot create preview GIF without frames.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0 if loop else 1,
        optimize=False,
    )
    return output_path


def _flatten_for_gif(image: Image.Image) -> Image.Image:
    background = Image.new("RGBA", image.size, (240, 240, 240, 255))
    background.alpha_composite(image)
    return background.convert("P", palette=Image.Palette.ADAPTIVE)
