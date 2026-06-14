from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_character_sprite_asset_pack.py"


def test_build_character_sprite_asset_pack(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    walk_ready = tmp_path / "walk_ready"
    run_rough = tmp_path / "run_rough"
    output_dir = tmp_path / "character_sprite_asset_pack"
    _make_reference(reference)
    _make_walk_ready_package(walk_ready)
    _make_run_rough_frames(run_rough)

    subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--reference-image",
            str(reference),
            "--walk-production-ready-dir",
            str(walk_ready),
            "--run-rough-frames-dir",
            str(run_rough),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "identity_report.json").exists()
    assert (output_dir / "production_gate.json").exists()
    assert (output_dir / "notes.md").exists()

    walk_frames = sorted((output_dir / "actions" / "walk" / "frames").glob("walk_*.png"))
    idle_frames = sorted((output_dir / "actions" / "idle" / "frames").glob("idle_*.png"))
    assert len(walk_frames) == 8
    assert len(idle_frames) == 4
    assert (output_dir / "actions" / "walk" / "preview.gif").exists()
    assert (output_dir / "actions" / "idle" / "preview.gif").exists()
    assert (output_dir / "actions" / "idle" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "idle" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "idle" / "game_previews" / "height_128" / "preview.gif").exists()
    assert (output_dir / "actions" / "run" / "preview.gif").exists()
    assert (output_dir / "actions" / "run" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "run" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "run" / "production_ready_report.json").exists()
    assert (output_dir / "actions" / "run" / "game_previews" / "height_128" / "contact_sheet.png").exists()

    assert {Image.open(path).size for path in idle_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in idle_frames)
    idle_gif = Image.open(output_dir / "actions" / "idle" / "preview.gif")
    assert getattr(idle_gif, "n_frames", 1) == 4
    run_frames = sorted((output_dir / "actions" / "run" / "frames").glob("run_*.png"))
    assert len(run_frames) == 8
    assert {Image.open(path).size for path in run_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in run_frames)
    run_gif = Image.open(output_dir / "actions" / "run" / "preview.gif")
    assert getattr(run_gif, "n_frames", 1) >= 4

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["route"] == "character_sprite_asset_pack"
    assert manifest["production_ready"] is True
    assert manifest["actions"]["walk"]["frame_count"] == 8
    assert manifest["actions"]["walk"]["production_ready"] is True
    assert manifest["actions"]["idle"]["frame_count"] == 4
    assert manifest["actions"]["idle"]["production_ready"] is True
    assert manifest["actions"]["run"]["frame_count"] == 8
    assert manifest["actions"]["run"]["production_ready"] is True
    assert manifest["actions"]["run"]["phase_names"] == [
        "right_contact",
        "right_down",
        "flight_forward",
        "left_reach",
        "left_contact",
        "left_down",
        "flight_backward",
        "right_reach",
    ]
    assert manifest["backend_usage"] == {
        "uses_comfyui": False,
        "uses_wan_video": False,
        "uses_controlnet": False,
        "uses_new_model_backend": False,
        "uses_120_frame_generation": False,
    }

    identity = json.loads((output_dir / "identity_report.json").read_text(encoding="utf-8"))
    assert identity["all_required_cues_pass"] is True
    assert set(identity["cue_reports"]) == {
        "pink_bob_hair",
        "side_profile_anime_girl",
        "sailor_white_top",
        "red_tie",
        "navy_skirt",
        "dark_socks",
        "brown_shoes",
    }

    gate = json.loads((output_dir / "production_gate.json").read_text(encoding="utf-8"))
    assert gate["decision"] == "production_ready"
    assert gate["production_ready"] is True
    assert gate["checks"]["run_production_ready"] is True
    assert gate["blocking_issues"] == []

    run_report = json.loads(
        (output_dir / "actions" / "run" / "production_ready_report.json").read_text(encoding="utf-8")
    )
    assert run_report["production_ready"] is True
    assert run_report["source"] == "imagegen_run_8frame_20260614_rough"
    assert run_report["airborne_lift_detected"] is True


def _make_reference(path: Path) -> None:
    image = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((30, 8, 58, 35), fill=(235, 120, 155, 255))
    draw.rectangle((35, 35, 58, 56), fill=(245, 245, 245, 255))
    draw.polygon([(43, 40), (51, 40), (47, 55)], fill=(170, 40, 45, 255))
    draw.polygon([(30, 56), (63, 56), (57, 68), (36, 68)], fill=(25, 35, 80, 255))
    draw.rectangle((37, 68, 43, 85), fill=(15, 25, 65, 255))
    draw.rectangle((52, 68, 58, 85), fill=(15, 25, 65, 255))
    draw.rectangle((33, 84, 47, 90), fill=(120, 65, 35, 255))
    draw.rectangle((49, 84, 64, 90), fill=(120, 65, 35, 255))
    image.save(path)


def _make_walk_ready_package(path: Path) -> None:
    frames_dir = path / "frames"
    frames_dir.mkdir(parents=True)
    for index in range(8):
        _make_sprite_frame(frames_dir / f"walk_{index:03d}.png", index)
    Image.new("RGBA", (96 * 8, 96), (0, 0, 0, 0)).save(path / "spritesheet.png")
    Image.new("RGBA", (96 * 4, 120 * 2), (245, 245, 245, 255)).save(path / "contact_sheet.png")
    Image.new("P", (96, 96)).save(path / "preview.gif")
    report = {
        "status": "production_ready",
        "source": "test",
        "frame_count": 8,
        "frame_size": {"width": 96, "height": 96},
        "estimated_ground_y_range": 0,
        "alpha_edge_touch_frames": [],
        "production_ready": True,
    }
    (path / "production_ready_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


def _make_sprite_frame(path: Path, index: int) -> None:
    image = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    x = 44 + (index % 2)
    draw.ellipse((x - 12, 6, x + 16, 35), fill=(235, 120, 155, 255))
    draw.rectangle((x - 10, 34, x + 14, 56), fill=(245, 245, 245, 255))
    draw.polygon([(x - 2, 38), (x + 8, 38), (x + 3, 55)], fill=(170, 40, 45, 255))
    draw.polygon([(x - 16, 56), (x + 22, 56), (x + 16, 70), (x - 10, 70)], fill=(25, 35, 80, 255))
    draw.rectangle((x - 11, 70, x - 4, 88), fill=(15, 25, 65, 255))
    draw.rectangle((x + 10, 70, x + 17, 88), fill=(15, 25, 65, 255))
    draw.rectangle((x - 15, 87, x + 1, 92), fill=(120, 65, 35, 255))
    draw.rectangle((x + 6, 87, x + 23, 92), fill=(120, 65, 35, 255))
    image.save(path)


def _make_run_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    for index in range(8):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 42
        airborne = index in {2, 3, 6, 7}
        y_offset = -12 if airborne else 0
        stride = 20 if index in {0, 4} else 10
        draw.ellipse((x - 12, 6 + y_offset, x + 16, 35 + y_offset), fill=(235, 120, 155, 255))
        draw.rectangle((x - 8, 34 + y_offset, x + 18, 56 + y_offset), fill=(245, 245, 245, 255))
        draw.polygon([(x + 2, 38 + y_offset), (x + 12, 38 + y_offset), (x + 6, 55 + y_offset)], fill=(170, 40, 45, 255))
        draw.polygon([(x - 16, 56 + y_offset), (x + 24, 56 + y_offset), (x + 16, 70 + y_offset), (x - 12, 70 + y_offset)], fill=(25, 35, 80, 255))
        if index < 4:
            front, rear = stride, -stride
        else:
            front, rear = -stride, stride
        knee_y = 75 + y_offset
        foot_y = 91 + y_offset
        draw.line((x, 68 + y_offset, x + front, foot_y), fill=(15, 25, 65, 255), width=6)
        draw.line((x + 8, 68 + y_offset, x + rear, knee_y, x + rear // 2, foot_y), fill=(15, 25, 65, 255), width=6)
        draw.rectangle((x + front - 7, foot_y - 4, x + front + 10, foot_y + 1), fill=(120, 65, 35, 255))
        draw.rectangle((x + rear // 2 - 7, foot_y - 4, x + rear // 2 + 10, foot_y + 1), fill=(120, 65, 35, 255))
        image.save(path / f"run_{index:03d}.png")
