from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stabilize_sprite_sequence.py"
_SPEC = importlib.util.spec_from_file_location("stabilize_sprite_sequence", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_stabilize_sequence_reduces_anchor_and_luma_variance(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    specs = [
        (0, 0, 0.72),
        (7, -5, 1.18),
        (-6, 4, 0.84),
    ]
    for index, (dx, dy, brightness) in enumerate(specs):
        _frame(frames / f"frame_{index:03d}.png", dx=dx, dy=dy, brightness=brightness)

    output_root = tmp_path / "out"
    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--frames-dir",
            str(frames),
            "--output-root",
            str(output_root),
            "--run-label",
            "stabilize_test",
            "--brightness-strength",
            "1.0",
            "--saturation-strength",
            "0.0",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["after_summary"]["anchor_x_stdev"] < payload["before_summary"]["anchor_x_stdev"]
    assert payload["after_summary"]["anchor_y_stdev"] < payload["before_summary"]["anchor_y_stdev"]
    assert payload["after_summary"]["foreground_luma_stdev"] < payload["before_summary"]["foreground_luma_stdev"]
    assert (Path(payload["run_dir"]) / "frames" / "frame_000.png").exists()
    assert (Path(payload["run_dir"]) / "spritesheet.png").exists()


def test_frame_metrics_reads_rgba_foreground() -> None:
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 4, 20, 28), fill=(120, 80, 40, 255))

    metrics = _MODULE._frame_metrics(image, alpha_threshold=24)

    assert metrics["has_foreground"] is True
    assert metrics["bbox"] == [10, 4, 21, 29]
    assert metrics["anchor_bottom_center"] == [15.5, 29.0]


def _frame(path: Path, *, dx: int, dy: int, brightness: float) -> None:
    image = Image.new("RGBA", (96, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = tuple(max(0, min(255, round(channel * brightness))) for channel in (80, 120, 180))
    x0 = 38 + dx
    y0 = 16 + dy
    draw.ellipse((x0 + 8, y0, x0 + 24, y0 + 16), fill=(*color, 255))
    draw.rectangle((x0 + 4, y0 + 16, x0 + 28, y0 + 72), fill=(*color, 255))
    draw.line((x0 + 10, y0 + 72, x0 + 2, y0 + 108), fill=(*color, 255), width=5)
    draw.line((x0 + 22, y0 + 72, x0 + 32, y0 + 108), fill=(*color, 255), width=5)
    image.save(path)
