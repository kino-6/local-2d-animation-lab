from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "visual_asset_gate.py"


def test_visual_asset_gate_detects_fragments_and_writes_fixed_pack(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    frames = pack / "actions" / "walk" / "frames"
    frames.mkdir(parents=True)
    for index in range(4):
        _make_frame(frames / f"walk_{index:03d}.png", dark=index == 2, fragment=index == 1)

    manifest = {
        "route": "character_sprite_asset_pack",
        "actions": {
            "walk": {
                "frame_count": 4,
                "frames": [f"actions/walk/frames/walk_{index:03d}.png" for index in range(4)],
                "runtime": {"fps": 8, "loop": True},
            }
        },
    }
    (pack / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    report_path = pack / "pack_review" / "visual_gate_report.json"
    fixed_dir = tmp_path / "fixed_pack"
    subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--manifest",
            str(pack / "manifest.json"),
            "--report",
            str(report_path),
            "--auto-fix-output",
            str(fixed_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["decision"] == "needs_retake_or_manual_review"
    assert "extra_foreground_component_or_sprite_fragment" in report["actions"]["walk"]["findings"]
    assert fixed_dir.joinpath("visual_gate_report.json").exists()
    assert fixed_dir.joinpath("actions/walk/preview.gif").exists()
    assert fixed_dir.joinpath("actions/walk/spritesheet.png").exists()
    assert fixed_dir.joinpath("pack_review/all_actions_contact_sheet.png").exists()
    fixed_report = json.loads(fixed_dir.joinpath("visual_gate_report.json").read_text(encoding="utf-8"))
    assert not fixed_report["actions"]["walk"]["metrics"]["extra_component_frames"]


def test_visual_asset_gate_detects_upper_body_hand_cue_dropout(tmp_path: Path) -> None:
    pack = tmp_path / "hand_dropout_pack"
    frames = pack / "actions" / "jump" / "frames"
    frames.mkdir(parents=True)
    for index in range(5):
        _make_hand_cue_frame(frames / f"jump_{index:03d}.png", hands_visible=index != 2)

    manifest = {
        "route": "character_sprite_asset_pack",
        "actions": {
            "jump": {
                "frame_count": 5,
                "frames": [f"actions/jump/frames/jump_{index:03d}.png" for index in range(5)],
                "runtime": {"fps": 8, "loop": False},
            }
        },
    }
    (pack / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    report_path = pack / "pack_review" / "visual_gate_report.json"
    subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--manifest",
            str(pack / "manifest.json"),
            "--report",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    jump = report["actions"]["jump"]
    assert jump["metrics"]["upper_body_hand_cue_low_frames"] == [2]
    assert "upper_body_hand_cue_dropout" in jump["findings"]


def _make_frame(path: Path, dark: bool, fragment: bool) -> None:
    image = Image.new("RGBA", (96, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    tone = 80 if dark else 180
    draw.ellipse((38, 12, 58, 32), fill=(240, 220, 210, 255))
    draw.rectangle((34, 34, 62, 84), fill=(tone, tone, tone + 20, 255))
    draw.rectangle((38, 84, 48, 118), fill=(40, 40, 45, 255))
    draw.rectangle((52, 84, 62, 118), fill=(40, 40, 45, 255))
    if fragment:
        draw.rectangle((82, 108, 94, 122), fill=(40, 35, 35, 255))
    image.save(path)


def _make_hand_cue_frame(path: Path, hands_visible: bool) -> None:
    image = Image.new("RGBA", (96, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((58, 12, 78, 32), fill=(240, 220, 210, 255))
    draw.rectangle((35, 34, 67, 86), fill=(35, 35, 44, 255))
    draw.rectangle((41, 86, 51, 120), fill=(35, 35, 44, 255))
    draw.rectangle((55, 86, 65, 120), fill=(35, 35, 44, 255))
    if hands_visible:
        draw.ellipse((25, 56, 36, 67), fill=(240, 220, 210, 255))
        draw.ellipse((66, 58, 77, 69), fill=(240, 220, 210, 255))
    image.save(path)
