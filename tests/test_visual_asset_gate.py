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


def test_visual_asset_gate_detects_upper_body_hand_cue_dropout_for_walk(tmp_path: Path) -> None:
    pack = tmp_path / "hand_dropout_pack"
    frames = pack / "actions" / "walk" / "frames"
    frames.mkdir(parents=True)
    for index in range(5):
        _make_hand_cue_frame(frames / f"walk_{index:03d}.png", hands_visible=index != 2)

    manifest = {
            "route": "character_sprite_asset_pack",
            "actions": {
                "walk": {
                    "frame_count": 5,
                    "frames": [f"actions/walk/frames/walk_{index:03d}.png" for index in range(5)],
                    "runtime": {"fps": 8, "loop": True},
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
    walk = report["actions"]["walk"]
    assert walk["metrics"]["upper_body_hand_cue_low_frames"] == [2]
    assert "upper_body_hand_cue_dropout" in walk["findings"]


def test_visual_asset_gate_detects_and_fixes_green_edge_fringe(tmp_path: Path) -> None:
    pack = tmp_path / "green_fringe_pack"
    frames = pack / "actions" / "jump" / "frames"
    frames.mkdir(parents=True)
    for index in range(4):
        _make_green_fringe_frame(frames / f"jump_{index:03d}.png")

    manifest = {
        "route": "character_sprite_asset_pack",
        "actions": {
            "jump": {
                "frame_count": 4,
                "frames": [f"actions/jump/frames/jump_{index:03d}.png" for index in range(4)],
                "runtime": {"fps": 8, "loop": False},
            }
        },
    }
    (pack / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    report_path = pack / "pack_review" / "visual_gate_report.json"
    fixed_dir = tmp_path / "fixed_green_fringe_pack"
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
    assert "green_cyan_alpha_edge_fringe" in report["actions"]["jump"]["findings"]
    fixed_report = json.loads(fixed_dir.joinpath("visual_gate_report.json").read_text(encoding="utf-8"))
    assert fixed_report["actions"]["jump"]["metrics"]["border_green_cyan_fringe_frames"] == []


def test_visual_asset_gate_detects_weak_weapon_readability(tmp_path: Path) -> None:
    pack = tmp_path / "weak_weapon_pack"
    frames = pack / "actions" / "attack_sword_light" / "frames"
    frames.mkdir(parents=True)
    for index in range(4):
        _make_attack_frame(frames / f"attack_sword_light_{index:03d}.png", sword_visible=False)

    manifest = {
        "route": "character_sprite_asset_pack",
        "actions": {
            "attack_sword_light": {
                "frame_count": 4,
                "frames": [
                    f"actions/attack_sword_light/frames/attack_sword_light_{index:03d}.png"
                    for index in range(4)
                ],
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
    attack = report["actions"]["attack_sword_light"]
    assert attack["metrics"]["weapon_cue_pixels_min"] < 650
    assert "weak_weapon_readability" in attack["findings"]


def test_visual_asset_gate_detects_hurt_side_panel_outlier(tmp_path: Path) -> None:
    pack = tmp_path / "hurt_side_panel_pack"
    frames = pack / "actions" / "hurt" / "frames"
    frames.mkdir(parents=True)
    for index in range(4):
        _make_hurt_frame(frames / f"hurt_{index:03d}.png", side_panel=index == 1)

    manifest = {
        "route": "character_sprite_asset_pack",
        "actions": {
            "hurt": {
                "frame_count": 4,
                "frames": [f"actions/hurt/frames/hurt_{index:03d}.png" for index in range(4)],
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
    hurt = report["actions"]["hurt"]
    assert hurt["metrics"]["silhouette_width_outlier_frames"] == [1]
    assert hurt["metrics"]["right_edge_silhouette_outlier_frames"] == [1]
    assert "side_panel_or_silhouette_width_outlier" in hurt["findings"]


def test_visual_asset_gate_detects_hard_vertical_alpha_cut(tmp_path: Path) -> None:
    pack = tmp_path / "hurt_cut_pack"
    frames = pack / "actions" / "hurt" / "frames"
    frames.mkdir(parents=True)
    for index in range(4):
        _make_hurt_frame(frames / f"hurt_{index:03d}.png", side_panel=False, hard_cut=index == 1)

    manifest = {
        "route": "character_sprite_asset_pack",
        "actions": {
            "hurt": {
                "frame_count": 4,
                "frames": [f"actions/hurt/frames/hurt_{index:03d}.png" for index in range(4)],
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
    hurt = report["actions"]["hurt"]
    assert hurt["metrics"]["hard_vertical_alpha_cut_frames"] == [1]
    assert "hard_vertical_alpha_cut" in hurt["findings"]


def test_visual_asset_gate_detects_abrupt_frame_delta_outlier(tmp_path: Path) -> None:
    pack = tmp_path / "abrupt_motion_pack"
    frames = pack / "actions" / "walk" / "frames"
    frames.mkdir(parents=True)
    for index in range(5):
        _make_motion_frame(frames / f"walk_{index:03d}.png", x_offset=0 if index != 2 else 42)

    manifest = {
        "route": "character_sprite_asset_pack",
        "actions": {
            "walk": {
                "frame_count": 5,
                "frames": [f"actions/walk/frames/walk_{index:03d}.png" for index in range(5)],
                "runtime": {"fps": 8, "loop": True},
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
    walk = report["actions"]["walk"]
    assert 2 in walk["metrics"]["step_delta_outlier_frames"]
    assert "abrupt_frame_delta_outlier" in walk["findings"]


def test_visual_asset_gate_detects_poor_recovery_to_idle_pose(tmp_path: Path) -> None:
    pack = tmp_path / "poor_recovery_pack"
    idle_frames = pack / "actions" / "idle" / "frames"
    hurt_frames = pack / "actions" / "hurt" / "frames"
    idle_frames.mkdir(parents=True)
    hurt_frames.mkdir(parents=True)
    for index in range(4):
        _make_motion_frame(idle_frames / f"idle_{index:03d}.png", x_offset=0)
    for index in range(4):
        _make_motion_frame(hurt_frames / f"hurt_{index:03d}.png", x_offset=80 if index == 3 else index * 4)

    manifest = {
        "route": "character_sprite_asset_pack",
        "actions": {
            "idle": {
                "frame_count": 4,
                "frames": [f"actions/idle/frames/idle_{index:03d}.png" for index in range(4)],
                "runtime": {"fps": 6, "loop": True},
            },
            "hurt": {
                "frame_count": 4,
                "frames": [f"actions/hurt/frames/hurt_{index:03d}.png" for index in range(4)],
                "runtime": {"fps": 8, "loop": False},
            },
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
    hurt = report["actions"]["hurt"]
    assert hurt["metrics"]["idle_bbox_pose_delta_last"] > 58
    assert "poor_recovery_to_idle_pose" in hurt["findings"]


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


def _make_green_fringe_frame(path: Path) -> None:
    image = Image.new("RGBA", (96, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((28, 20, 68, 118), fill=(35, 35, 42, 255))
    draw.rectangle((24, 18, 72, 120), outline=(0, 210, 80, 255), width=3)
    draw.ellipse((40, 8, 58, 28), fill=(238, 220, 210, 255))
    image.save(path)


def _make_attack_frame(path: Path, sword_visible: bool) -> None:
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((54, 12, 74, 32), fill=(238, 220, 210, 255))
    draw.rectangle((44, 34, 82, 86), fill=(34, 34, 42, 255))
    draw.rectangle((48, 86, 58, 120), fill=(32, 30, 35, 255))
    draw.rectangle((68, 86, 78, 120), fill=(32, 30, 35, 255))
    if sword_visible:
        draw.line((80, 70, 118, 38), fill=(235, 235, 245, 255), width=3)
    image.save(path)


def _make_hurt_frame(path: Path, side_panel: bool, hard_cut: bool = False) -> None:
    image = Image.new("RGBA", (160, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((66, 12, 86, 32), fill=(238, 220, 210, 255))
    draw.rectangle((52, 34, 92, 84), fill=(34, 34, 42, 255))
    draw.rectangle((56, 84, 66, 122), fill=(32, 30, 35, 255))
    draw.rectangle((78, 84, 88, 122), fill=(32, 30, 35, 255))
    if side_panel:
        draw.rectangle((118, 16, 152, 122), outline=(65, 70, 76, 255), width=2)
        draw.line((135, 18, 135, 120), fill=(65, 70, 76, 255), width=2)
        draw.line((91, 52, 118, 58), fill=(65, 70, 76, 255), width=2)
    if hard_cut:
        draw.rectangle((92, 18, 92, 122), fill=(36, 36, 44, 255))
    image.save(path)


def _make_motion_frame(path: Path, x_offset: int) -> None:
    image = Image.new("RGBA", (160, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    x = 52 + x_offset
    draw.ellipse((x + 14, 12, x + 34, 32), fill=(238, 220, 210, 255))
    draw.rectangle((x, 34, x + 44, 84), fill=(34, 34, 42, 255))
    draw.rectangle((x + 6, 84, x + 16, 122), fill=(32, 30, 35, 255))
    draw.rectangle((x + 28, 84, x + 38, 122), fill=(32, 30, 35, 255))
    image.save(path)
