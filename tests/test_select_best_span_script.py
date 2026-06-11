from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "select_best_span.py"
_SPEC = importlib.util.spec_from_file_location("select_best_span_script", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_analysis_resize_keeps_original_selected_frame_resolution(tmp_path: Path, monkeypatch) -> None:
    frames_dir = tmp_path / "frames"
    masks_dir = tmp_path / "masks"
    output_root = tmp_path / "out"
    frames_dir.mkdir()
    masks_dir.mkdir()
    for index in range(3):
        _draw_frame(frames_dir / f"frame_{index:03d}.png", offset=index * 8)
        Image.new("L", (768, 768), 255).save(masks_dir / f"foreground_mask_{index:03d}.png")

    monkeypatch.setattr(
        "sys.argv",
        [
            "select_best_span.py",
            "--frames-dir",
            str(frames_dir),
            "--foreground-mask-dir",
            str(masks_dir),
            "--output-root",
            str(output_root),
            "--run-label",
            "resize_keeps_original",
            "--span-length",
            "2",
            "--analysis-max-size",
            "64",
        ],
    )

    _MODULE.main()

    selected = sorted(output_root.glob("resize_keeps_original_*/selected_frames/frame_*.png"))
    assert selected
    assert Image.open(selected[0]).size == (768, 768)


def test_report_labels_low_motion_selection_for_review(tmp_path: Path, monkeypatch) -> None:
    frames_dir = tmp_path / "frames"
    output_root = tmp_path / "out"
    frames_dir.mkdir()
    for index in range(3):
        _draw_frame(frames_dir / f"frame_{index:03d}.png", offset=index)

    monkeypatch.setattr(
        "sys.argv",
        [
            "select_best_span.py",
            "--frames-dir",
            str(frames_dir),
            "--output-root",
            str(output_root),
            "--run-label",
            "low_motion_label",
            "--span-length",
            "2",
            "--min-mean-motion-delta",
            "100",
            "--analysis-max-size",
            "64",
        ],
    )

    _MODULE.main()

    report_path = next(output_root.glob("low_motion_label_*/span_selection_report.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["selection_review_labels"] == ["weak_motion_or_foot_sliding_review"]


def _draw_frame(path: Path, offset: int) -> None:
    image = Image.new("RGB", (768, 768), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    x = 340 + offset
    draw.ellipse((x, 120, x + 56, 176), fill=(80, 48, 32))
    draw.rectangle((x - 8, 176, x + 64, 390), fill=(18, 38, 85))
    draw.rectangle((x + 8, 390, x + 24, 590), fill=(248, 207, 194))
    draw.rectangle((x + 40, 390, x + 56, 590), fill=(248, 207, 194))
    draw.ellipse((x - 10, 580, x + 34, 612), fill=(28, 24, 28))
    draw.ellipse((x + 34, 580, x + 78, 612), fill=(28, 24, 28))
    image.save(path)
