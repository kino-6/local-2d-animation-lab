from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_design_sheet_side_view.py"
_SPEC = importlib.util.spec_from_file_location("extract_design_sheet_side_view", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_remove_connected_light_background_preserves_bright_hair_inside_subject() -> None:
    image = Image.new("RGBA", (96, 96), (238, 238, 238, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((38, 18, 58, 80), fill=(15, 18, 24, 255))
    draw.rectangle((33, 21, 63, 45), fill=(24, 28, 36, 255))
    draw.rectangle((35, 23, 61, 43), fill=(232, 240, 248, 255))

    rgba = _MODULE._remove_connected_light_background(image, threshold=42)

    assert rgba.getpixel((0, 0))[3] == 0
    assert rgba.getpixel((48, 30))[3] == 255
    assert rgba.getpixel((48, 70))[3] == 255


def test_extract_design_sheet_side_view_cli_writes_manifest(tmp_path: Path) -> None:
    sheet = Image.new("RGBA", (300, 120), (238, 238, 238, 255))
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((132, 20, 168, 110), fill=(10, 12, 18, 255))
    draw.rectangle((126, 16, 174, 42), fill=(232, 240, 248, 255))
    sheet_path = tmp_path / "sheet.png"
    sheet.save(sheet_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--sheet",
            str(sheet_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--left",
            "0.30",
            "--right",
            "0.70",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    out_dir = Path(payload["output_dir"])
    side = Image.open(out_dir / "side_view.png").convert("RGBA")

    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "notes.md").exists()
    assert (out_dir / "side_view_review.png").exists()
    assert side.getchannel("A").getbbox() is not None
