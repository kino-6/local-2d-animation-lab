from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_imagegen_action_pack.py"


def test_build_imagegen_action_pack_outputs_godot_loadable_layout(tmp_path: Path) -> None:
    sheets_dir = tmp_path / "sheets"
    output_dir = tmp_path / "nun_pack"
    design_source = tmp_path / "design_source.png"
    sheets_dir.mkdir()
    _make_design_source(design_source)

    for action, frame_count in {
        "walk": 8,
        "run": 8,
        "jump": 12,
        "hurt": 8,
        "attack_sword_light": 11,
    }.items():
        _make_sheet(sheets_dir / f"{action}_sheet.png", frame_count)

    subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--sheets-dir",
            str(sheets_dir),
            "--design-source",
            str(design_source),
            "--output-dir",
            str(output_dir),
            "--frame-width",
            "128",
            "--frame-height",
            "160",
            "--target-height",
            "132",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["route"] == "character_sprite_asset_pack"
    assert manifest["production_ready"] is True
    assert manifest["backend_usage"] == {
        "uses_builtin_image_generation": True,
        "uses_comfyui": False,
        "uses_wan_video": False,
        "uses_controlnet": False,
        "uses_120_frame_generation": False,
    }
    assert set(manifest["actions"]) == {"idle", "walk", "run", "jump", "hurt", "attack_sword_light"}
    assert manifest["actions"]["attack_sword_light"]["frame_count"] == 11

    for action, expected_count in {
        "idle": 4,
        "walk": 8,
        "run": 8,
        "jump": 12,
        "hurt": 8,
        "attack_sword_light": 11,
    }.items():
        action_dir = output_dir / "actions" / action
        frames = sorted((action_dir / "frames").glob(f"{action}_*.png"))
        assert len(frames) == expected_count
        assert (action_dir / "spritesheet.png").exists()
        assert (action_dir / "preview.gif").exists()
        assert (action_dir / "contact_sheet.png").exists()
        assert (action_dir / "production_ready_report.json").exists()
        assert {Image.open(path).size for path in frames} == {(128, 160)}
        assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in frames)

    assert (output_dir / "runtime_manifest.json").exists()
    assert (output_dir / "production_gate.json").exists()
    assert (output_dir / "pack_review" / "all_actions_contact_sheet.png").exists()
    assert (output_dir / "pack_review" / "quality_report.json").exists()
    assert (output_dir / "pack_review" / "godot_import_manifest.json").exists()


def _make_design_source(path: Path) -> None:
    image = Image.new("RGBA", (128, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((48, 12, 82, 46), fill=(245, 225, 205, 255))
    draw.rectangle((44, 44, 86, 110), fill=(22, 22, 28, 255))
    draw.rectangle((54, 110, 65, 150), fill=(25, 25, 35, 255))
    draw.rectangle((68, 110, 79, 150), fill=(25, 25, 35, 255))
    image.save(path)


def _make_sheet(path: Path, frame_count: int) -> None:
    cell_w = 96
    height = 144
    image = Image.new("RGBA", (cell_w * frame_count, height), (0, 255, 0, 255))
    draw = ImageDraw.Draw(image)
    for index in range(frame_count):
        cx = index * cell_w + cell_w // 2
        bob = -4 if index % 4 == 2 else 0
        leg = 10 if index % 2 == 0 else -10
        draw.ellipse((cx - 11, 14 + bob, cx + 11, 36 + bob), fill=(245, 225, 205, 255))
        draw.rectangle((cx - 15, 36 + bob, cx + 15, 84 + bob), fill=(20, 20, 28, 255))
        draw.polygon([(cx - 22, 84 + bob), (cx + 22, 84 + bob), (cx + 15, 106 + bob), (cx - 15, 106 + bob)], fill=(18, 18, 26, 255))
        draw.line((cx - 7, 104 + bob, cx - 18 - leg, 130), fill=(32, 28, 30, 255), width=7)
        draw.line((cx + 7, 104 + bob, cx + 18 + leg, 130), fill=(32, 28, 30, 255), width=7)
        draw.line((cx - 14, 46 + bob, cx - 26, 76 + bob), fill=(32, 28, 30, 255), width=5)
        draw.line((cx + 14, 46 + bob, cx + 26, 76 + bob), fill=(32, 28, 30, 255), width=5)
        if frame_count == 11:
            draw.line((cx + 10, 66 + bob, cx + 36, 92 + bob), fill=(210, 210, 220, 255), width=3)
    image.save(path)
