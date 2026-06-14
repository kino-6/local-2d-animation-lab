from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "package_artist_authored_walk_cleanup.py"


def test_artist_authored_walk_cleanup_contract(tmp_path: Path) -> None:
    rough = tmp_path / "rough"
    rough.mkdir()
    for index in range(8):
        _make_rough_frame(rough / f"walk_{index:03d}.png", index)

    output_dir = tmp_path / "artist_authored_8frame_walk_cleanup"
    subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--rough-frames-dir",
            str(rough),
            "--output-dir",
            str(output_dir),
            "--fps",
            "8",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    frames_dir = output_dir / "frames"
    frame_paths = sorted(frames_dir.glob("walk_*.png"))
    assert [path.name for path in frame_paths] == [f"walk_{index:03d}.png" for index in range(8)]
    assert (output_dir / "spritesheet.png").exists()
    assert (output_dir / "preview.gif").exists()
    assert (output_dir / "contact_sheet.png").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "cleanup_report.json").exists()
    assert (output_dir / "notes.md").exists()

    assert [Image.open(path).size for path in frame_paths] == [(96, 96)] * 8
    assert all(Image.open(path).mode == "RGBA" for path in frame_paths)
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in frame_paths)

    preview = Image.open(output_dir / "preview.gif")
    assert getattr(preview, "n_frames", 1) == 8

    spritesheet = Image.open(output_dir / "spritesheet.png")
    assert spritesheet.size == (96 * 8, 96)

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["route"] == "artist_authored_8frame_walk_cleanup"
    assert manifest["route_status"] == "requires_artist_authored_rough"
    assert manifest["source_kind"] == "artist_authored_rough"
    assert manifest["frame_count"] == 8
    assert manifest["phase_names"] == [
        "contact",
        "down",
        "passing",
        "up",
        "opposite_contact",
        "opposite_down",
        "opposite_passing",
        "opposite_up",
    ]
    assert manifest["manual_art_required"] is True
    assert manifest["ai_scope"] == "cleanup_only_no_pose_or_silhouette_generation"
    assert manifest["backend_usage"] == {
        "uses_comfyui": False,
        "uses_wan_video": False,
        "uses_controlnet": False,
        "uses_new_model_backend": False,
        "uses_120_frame_generation": False,
    }


def test_artist_authored_walk_cleanup_rejects_wrong_frame_count(tmp_path: Path) -> None:
    rough = tmp_path / "rough"
    rough.mkdir()
    for index in range(7):
        _make_rough_frame(rough / f"walk_{index:03d}.png", index)

    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--rough-frames-dir",
            str(rough),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "requires exactly 8 PNG rough frames" in completed.stderr


def _make_rough_frame(path: Path, index: int) -> None:
    image = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    cx = 48
    ground = 86
    phase = index / 8
    front = round(16 * math.sin(phase * 6.28318))
    rear = -front
    draw.ellipse((cx - 8, 12, cx + 8, 28), fill=(230, 160, 140, 255))
    draw.rectangle((cx - 10, 28, cx + 10, 54), fill=(245, 245, 250, 255))
    draw.polygon([(cx - 16, 54), (cx + 16, 54), (cx + 22, 67), (cx - 22, 67)], fill=(235, 240, 245, 255))
    draw.line((cx - 6, 67, cx + front, ground - 4), fill=(35, 35, 50, 255), width=5)
    draw.line((cx + 6, 67, cx + rear, ground - 4), fill=(35, 35, 50, 255), width=5)
    draw.rectangle((cx + front - 7, ground - 5, cx + front + 10, ground), fill=(110, 45, 30, 255))
    draw.rectangle((cx + rear - 7, ground - 5, cx + rear + 10, ground), fill=(110, 45, 30, 255))
    image.save(path)
