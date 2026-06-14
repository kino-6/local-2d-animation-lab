from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_walk_8frame_baseline.py"


def test_build_walk_8frame_baseline_output_contract(tmp_path: Path) -> None:
    source = tmp_path / "reference.png"
    _make_reference(source)
    output_dir = tmp_path / "walk_8frame_sideview_baseline"

    subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--input",
            str(source),
            "--output-dir",
            str(output_dir),
            "--frame-width",
            "128",
            "--frame-height",
            "128",
            "--target-height",
            "104",
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
    assert not (frames_dir / "walk_008.png").exists()
    assert (output_dir / "spritesheet.png").exists()
    assert (output_dir / "preview.gif").exists()
    assert (output_dir / "contact_sheet.png").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "notes.md").exists()

    sizes = [Image.open(path).size for path in frame_paths]
    modes = [Image.open(path).mode for path in frame_paths]
    assert sizes == [(128, 128)] * 8
    assert modes == ["RGBA"] * 8
    assert all(Image.open(path).getchannel("A").getbbox() is not None for path in frame_paths)

    spritesheet = Image.open(output_dir / "spritesheet.png")
    assert spritesheet.size == (128 * 8, 128)

    preview = Image.open(output_dir / "preview.gif")
    assert getattr(preview, "n_frames", 1) == 8

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["route"] == "walk_8frame_sideview_baseline"
    assert manifest["route_status"] == "baseline_not_production"
    assert manifest["frame_count"] == 8
    assert manifest["action_spec"] == {
        "action": "walk",
        "direction": "right",
        "frame_count": 8,
        "view": "side",
        "loop": True,
        "background": "transparent",
    }
    assert manifest["method"]["uses_wan_video"] is False
    assert manifest["method"]["uses_120_frame_generation"] is False
    assert manifest["method"]["renderer"] == "stylized_sprite_cycle"
    assert manifest["method"]["motion"] == "stylized reference-derived 8-phase sprite walk cycle"
    assert manifest["motion_metrics"]["max_mean_diff_from_first"] > 0.5
    assert manifest["motion_metrics"]["unique_alpha_boxes"] >= 2
    assert manifest["motion_metrics"]["phase_labels"] == [
        "contact",
        "down",
        "passing",
        "up",
        "opposite_contact",
        "opposite_down",
        "opposite_passing",
        "opposite_up",
    ]
    assert manifest["visual_review"]["agent_decision"] == "review_worthy_mvp_not_production"


def _make_reference(path: Path) -> None:
    image = Image.new("RGB", (96, 128), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((34, 8, 58, 32), fill=(235, 205, 170))
    draw.rectangle((38, 32, 58, 78), fill=(40, 90, 180))
    draw.line((40, 42, 24, 70), fill=(30, 40, 60), width=5)
    draw.line((56, 42, 72, 68), fill=(30, 40, 60), width=5)
    draw.line((42, 78, 30, 114), fill=(20, 30, 50), width=6)
    draw.line((56, 78, 68, 114), fill=(20, 30, 50), width=6)
    draw.rectangle((24, 110, 38, 118), fill=(35, 35, 35))
    draw.rectangle((62, 110, 78, 118), fill=(35, 35, 35))
    image.save(path)
