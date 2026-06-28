from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def test_clean_lower_body_walk_artifacts_cli(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(3):
        image = Image.new("RGBA", (96, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((42, 16, 58, 108), fill=(10, 12, 14, 255))
        draw.rectangle((36 + index, 104, 62 + index, 120), fill=(8, 8, 8, 255))
        draw.rectangle((62, 88, 78, 120), fill=(120, 135, 126, 255))
        image.save(frames / f"frame_{index:03d}.png")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/clean_lower_body_walk_artifacts.py",
            "--frames-dir",
            str(frames),
            "--output-root",
            str(tmp_path / "outputs"),
            "--run-label",
            "unit_clean",
            "--lower-start-ratio",
            "0.50",
            "--pale-luma-min",
            "44",
            "--pale-saturation-max",
            "128",
            "--green-cast-margin",
            "0",
            "--protect-grow",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    run_dir = Path(payload["run_dir"])

    assert len(list((run_dir / "frames").glob("*.png"))) == 3
    assert (run_dir / "spritesheet.png").exists()
    assert (run_dir / "contact_sheet.png").exists()
    assert (run_dir / "preview.gif").exists()
    assert (run_dir / "lower_body_cleanup_report.json").exists()
    assert payload["removed_pixels"] > 0
