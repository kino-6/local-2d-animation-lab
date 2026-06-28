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
    assert (output_dir / "production_review.json").exists()
    assert (output_dir / "production_review.md").exists()
    assert (output_dir / "notes.md").exists()
    assert (output_dir / "game_previews" / "height_128" / "preview.gif").exists()
    assert (output_dir / "game_previews" / "height_192" / "spritesheet.png").exists()
    assert (output_dir / "game_previews" / "height_256" / "contact_sheet.png").exists()
    assert (output_dir / "production_polish" / "preview.gif").exists()
    assert (output_dir / "production_polish" / "contact_sheet.png").exists()
    assert (output_dir / "production_polish" / "polish_report.json").exists()
    assert (output_dir / "production_polish" / "polish_review.md").exists()
    assert (output_dir / "production_polish" / "game_previews" / "height_128" / "preview.gif").exists()
    assert (output_dir / "production_candidate" / "preview.gif").exists()
    assert (output_dir / "production_candidate" / "spritesheet.png").exists()
    assert (output_dir / "production_candidate" / "candidate_report.json").exists()
    assert (output_dir / "production_candidate" / "candidate_review.md").exists()

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
    assert manifest["outputs"]["game_previews"]["height_128"]["frame_size"] == {"width": 128, "height": 128}
    assert manifest["outputs"]["game_previews"]["height_192"]["frame_size"] == {"width": 192, "height": 192}
    assert manifest["outputs"]["game_previews"]["height_256"]["frame_size"] == {"width": 256, "height": 256}
    assert manifest["game_readiness"]["fixed_best_rough"] is True
    assert manifest["game_readiness"]["generated_new_motion"] is False
    assert manifest["game_readiness"]["decision"] == "reviewable_rough_candidate_not_production"
    assert manifest["outputs"]["production_review"] == "production_review.json"
    assert manifest["outputs"]["production_review_md"] == "production_review.md"
    assert manifest["production_gate"]["target"] == "production_walk_8frame_sideview"
    assert manifest["production_gate"]["decision"] == "candidate_ready_for_manual_polish"
    assert manifest["production_gate"]["production_ready"] is False
    assert manifest["production_gate"]["manual_polish_required"] is False
    assert (output_dir / "production_review.md").read_text(encoding="utf-8").startswith("# Production Review")
    assert manifest["outputs"]["production_polish"]["preview_gif"] == "production_polish/preview.gif"
    assert manifest["outputs"]["production_polish"]["game_previews"]["height_128"]["preview_gif"] == (
        "production_polish/game_previews/height_128/preview.gif"
    )
    assert manifest["outputs"]["production_polish"]["polish_review"] == "production_polish/polish_review.md"
    assert manifest["production_polish"]["status"] == "auto_polished_candidate_not_final"
    assert manifest["production_polish"]["estimated_ground_y_range_after"] == 0
    candidate = manifest["production_polish"]["production_candidate"]
    assert candidate["status"] == "production_candidate_for_human_review"
    assert candidate["source"] == "production_polish"
    assert candidate["manual_review_required"] is True
    assert manifest["outputs"]["production_polish"]["production_candidate"]["preview_gif"] == (
        "production_candidate/preview.gif"
    )


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


def test_artist_authored_walk_cleanup_can_mark_production_ready(tmp_path: Path) -> None:
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
            "--mark-production-ready",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["review"]["production_ready"] is True
    assert manifest["production_gate"]["decision"] == "production_ready"
    assert manifest["production_gate"]["production_ready"] is True
    assert manifest["production_gate"]["manual_polish_required"] is False
    assert manifest["production_gate"]["do_not_claim_production_until"] == []
    assert manifest["production_polish"]["production_ready"]["status"] == "production_ready"
    assert manifest["outputs"]["production_polish"]["production_ready"]["preview_gif"] == (
        "production_ready/preview.gif"
    )
    production_review = (output_dir / "production_review.md").read_text(encoding="utf-8")
    assert "explicitly finalized with `--mark-production-ready`" in production_review
    assert "Do not mark this asset production-ready" not in production_review
    assert (output_dir / "production_ready" / "preview.gif").exists()
    assert (output_dir / "production_ready" / "production_ready_report.json").exists()
    assert (output_dir / "production_ready" / "production_ready_review.md").exists()


def test_artist_authored_walk_cleanup_removes_green_dominant_background(tmp_path: Path) -> None:
    rough = tmp_path / "rough"
    rough.mkdir()
    for index in range(8):
        _make_green_key_rough_frame(rough / f"walk_{index:03d}.png")

    output_dir = tmp_path / "artist_authored_8frame_walk_cleanup"
    subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--rough-frames-dir",
            str(rough),
            "--output-dir",
            str(output_dir),
            "--background-min-channel",
            "0",
            "--background-threshold",
            "120",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    frame = Image.open(output_dir / "frames" / "walk_000.png").convert("RGBA")
    assert frame.getpixel((0, 0))[3] == 0
    assert frame.getpixel((48, 48))[3] == 255
    assert frame.getpixel((48, 48))[:3] == (20, 30, 70)

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    report = manifest["frames"][0]["bbox"]
    assert report == [32, 10, 65, 73]


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


def _make_green_key_rough_frame(path: Path) -> None:
    image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            pixels[x, y] = (0, max(120, 255 - y // 3), x % 12, 255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((32, 24, 64, 72), fill=(20, 30, 70, 255))
    draw.ellipse((38, 10, 58, 30), fill=(246, 174, 154, 255))
    image.save(path)
