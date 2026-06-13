from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apply_mask_cleanup.py"
_SPEC = importlib.util.spec_from_file_location("apply_mask_cleanup", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

_cleanup_frame = _MODULE._cleanup_frame
_flatten_on_white = _MODULE._flatten_on_white
_select_indexed_frames = _MODULE._select_indexed_frames


def test_cleanup_frame_whitens_only_masked_pixels(tmp_path: Path) -> None:
    frame_path = tmp_path / "frame.png"
    mask_path = tmp_path / "mask.png"
    output_path = tmp_path / "out.png"
    image = Image.new("RGB", (8, 8), (10, 20, 30))
    image.save(frame_path)
    mask = Image.new("L", (8, 8), 0)
    mask.putpixel((2, 3), 255)
    mask.save(mask_path)

    report = _cleanup_frame(frame_path, mask_path, output_path, threshold=128, erode=0, max_coverage=0.5)

    output = Image.open(output_path).convert("RGB")
    assert report["mode"] == "white_mask_cleanup"
    assert output.getpixel((2, 3)) == (255, 255, 255)
    assert output.getpixel((0, 0)) == (10, 20, 30)


def test_cleanup_frame_copies_when_mask_too_large(tmp_path: Path) -> None:
    frame_path = tmp_path / "frame.png"
    mask_path = tmp_path / "mask.png"
    output_path = tmp_path / "out.png"
    Image.new("RGB", (8, 8), (10, 20, 30)).save(frame_path)
    Image.new("L", (8, 8), 255).save(mask_path)

    report = _cleanup_frame(frame_path, mask_path, output_path, threshold=128, erode=0, max_coverage=0.5)

    assert report["mode"] == "copied_mask_too_large"
    assert Image.open(output_path).convert("RGB").getpixel((2, 3)) == (10, 20, 30)


def test_flatten_on_white_preserves_transparent_background_as_white() -> None:
    image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    image.putpixel((1, 1), (10, 20, 30, 255))

    flattened = _flatten_on_white(image)

    assert flattened.getpixel((0, 0)) == (255, 255, 255)
    assert flattened.getpixel((1, 1)) == (10, 20, 30)


def test_select_indexed_frames_limits_to_plan_action(tmp_path: Path) -> None:
    frames = [tmp_path / f"frame_{index:03d}.png" for index in range(4)]
    selected = _select_indexed_frames(
        frames,
        {0: "local_inpaint_candidate", 2: "retake_required", 3: "local_inpaint_candidate"},
        "local_inpaint_candidate",
    )

    assert selected == [(0, frames[0]), (3, frames[3])]
