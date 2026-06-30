from __future__ import annotations

from pathlib import Path

from PIL import Image

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif, make_preview_webp


def test_preview_exports_include_gif_and_lossless_webp(tmp_path: Path) -> None:
    frame_paths = []
    for index, color in enumerate([(255, 255, 255, 255), (40, 60, 80, 255)]):
        path = tmp_path / f"frame_{index}.png"
        image = Image.new("RGBA", (12, 16), (0, 0, 0, 0))
        image.paste(color, (2 + index, 3, 8 + index, 12))
        image.save(path)
        frame_paths.append(path)

    gif = make_preview_gif(frame_paths, tmp_path / "preview.gif", duration_ms=80, loop=True)
    webp = make_preview_webp(frame_paths, tmp_path / "preview.webp", duration_ms=80, loop=True)

    with Image.open(gif) as image:
        assert image.n_frames == 2
        assert image.size == (12, 16)
    with Image.open(webp) as image:
        assert image.n_frames == 2
        assert image.size == (12, 16)
        assert image.mode == "RGBA"
