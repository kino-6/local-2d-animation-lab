from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyze_sprite_regions.py"
_SPEC = importlib.util.spec_from_file_location("analyze_sprite_regions", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_region_diagnostics_flags_lower_body_and_contact_artifacts(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    _frame(frames / "frame_000.png", artifact=False, offset=0)
    _frame(frames / "frame_001.png", artifact=True, offset=8)

    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--frames-dir",
            str(frames),
            "--output-root",
            str(tmp_path / "regions"),
            "--run-label",
            "region_test",
            "--columns",
            "2",
            "--pale-threshold",
            "0.004",
            "--contact-threshold",
            "0.004",
            "--temporal-delta-threshold",
            "0.02",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["frame_count"] == 2
    assert Path(payload["overlay_contact_sheet"]).exists()
    assert Path(payload["artifact_mask_contact_sheet"]).exists()
    assert Path(payload["frame_reports"][1]["artifact_mask"]).exists()
    assert "lower_body_pale_afterimage_review" in payload["summary"]["issue_label_counts"]
    assert "foot_shadow_or_contact_artifact_review" in payload["summary"]["issue_label_counts"]
    assert payload["summary"]["decision_counts"]["retake_required"] >= 1


def test_region_boxes_are_bbox_relative() -> None:
    boxes = _MODULE._region_boxes((20, 10, 80, 110), (128, 128))

    assert boxes["lower_body"][1] > 10
    assert boxes["feet_contact"][1] > boxes["lower_body"][1]
    assert boxes["cloak_or_hair_trail"][0] < 20


def test_foreground_mask_for_opaque_rgb_uses_background_distance() -> None:
    image = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 8, 20, 26), fill=(20, 30, 40, 255))

    mask = _MODULE._foreground_mask(image, 24)

    assert mask.getbbox() == (12, 8, 21, 27)


def test_empty_foreground_is_retake_label() -> None:
    args = type(
        "Args",
        (),
        {
            "pale_threshold": 0.018,
            "contact_threshold": 0.012,
            "temporal_delta_threshold": 0.115,
            "trail_threshold": 0.018,
        },
    )()

    labels = _MODULE._issue_labels({}, args)
    decision = _MODULE._frame_decision(labels, {})

    assert labels == ["foreground_missing_or_unreadable_sprite"]
    assert decision == "retake_required"


def _frame(path: Path, *, artifact: bool, offset: int) -> None:
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    x = 48 + offset
    draw.ellipse((x, 10, x + 20, 30), fill=(230, 190, 150, 255))
    draw.rectangle((x - 4, 30, x + 24, 78), fill=(20, 30, 70, 255))
    draw.line((x + 2, 78, x - 10, 118), fill=(18, 18, 24, 255), width=6)
    draw.line((x + 18, 78, x + 34, 118), fill=(18, 18, 24, 255), width=6)
    draw.ellipse((x - 18, 112, x + 4, 124), fill=(30, 30, 35, 255))
    draw.ellipse((x + 22, 112, x + 48, 124), fill=(30, 30, 35, 255))
    if artifact:
        draw.rectangle((x + 30, 76, x + 46, 120), fill=(170, 176, 184, 180))
        draw.ellipse((x - 4, 112, x + 24, 126), fill=(172, 172, 172, 180))
    image.save(path)
