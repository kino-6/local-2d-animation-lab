from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "recolor_gold_armor_to_dark_cloth.py"
_SPEC = importlib.util.spec_from_file_location("recolor_gold_armor_to_dark_cloth", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_recolor_frame_reduces_gold_without_touching_skin_or_hair() -> None:
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((4, 4, 14, 14), fill=(198, 161, 82, 255))
    draw.rectangle((18, 4, 26, 14), fill=(236, 188, 172, 255))
    draw.rectangle((4, 20, 16, 28), fill=(42, 36, 48, 255))

    recolored, report = _MODULE._recolor_frame(image)

    assert report["recolored_pixels"] > 0
    assert report["gold_pixels_after"] < report["gold_pixels_before"]
    gold_pixel = recolored.getpixel((8, 8))
    skin_pixel = recolored.getpixel((20, 8))
    assert gold_pixel[0] < 90 and gold_pixel[1] < 90 and gold_pixel[2] < 100
    assert skin_pixel[:3] == (236, 188, 172)


def test_recolor_gold_armor_cli_writes_review_assets(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(2):
        image = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((18 + index, 6, 30 + index, 42), fill=(30, 28, 36, 255))
        draw.rectangle((16 + index, 12, 24 + index, 22), fill=(202, 168, 88, 255))
        image.save(frames / f"frame_{index:03d}.png")

    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--frames-dir",
            str(frames),
            "--output-root",
            str(tmp_path / "outputs"),
            "--run-label",
            "test_gold_to_cloth",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    run_dir = Path(payload["run_dir"])
    report = json.loads((run_dir / "recolor_report.json").read_text(encoding="utf-8"))

    assert (run_dir / "frames" / "frame_000.png").exists()
    assert (run_dir / "spritesheet.png").exists()
    assert (run_dir / "preview.gif").exists()
    assert (run_dir / "contact_sheet.png").exists()
    assert report["summary"]["recolored_pixels"] > 0
    assert report["summary"]["gold_pixels_after"] < report["summary"]["gold_pixels_before"]
