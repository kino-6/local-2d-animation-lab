from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path

from PIL import Image, ImageDraw

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "repair_frame_artifacts.py"
_SPEC = importlib.util.spec_from_file_location("repair_frame_artifacts", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

_analyze_frame = _MODULE._analyze_frame
_candidate_status = _MODULE._candidate_status
_mask_coverage = _MODULE._mask_coverage
_overlap_pixels = _MODULE._overlap_pixels
_recommendation = _MODULE._recommendation


def _args() -> Namespace:
    return Namespace(
        weak_threshold=34,
        strong_threshold=92,
        protect_grow=19,
        mask_grow=7,
        min_mask_coverage=0.0004,
        max_mask_coverage=0.18,
        analysis_max_size=512,
        weapon="none",
    )


def test_person_mask_protects_main_character_from_repair_mask(tmp_path: Path) -> None:
    frame = tmp_path / "frame.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((96, 38, 160, 220), fill=(30, 60, 110))
    draw.rectangle((185, 156, 204, 220), fill=(180, 190, 205))
    image.save(frame)

    analysis = _analyze_frame(frame, _args())

    person_mask = analysis["person_mask"]
    repair_mask = analysis["repair_mask"]
    assert _mask_coverage(person_mask) > 0.15
    assert _mask_coverage(repair_mask) > 0.0
    assert _overlap_pixels(person_mask, repair_mask) == 0
    assert analysis["gate"] == "repair_candidate"


def test_extra_foreground_component_is_retake_not_inpaint_candidate(tmp_path: Path) -> None:
    frame = tmp_path / "frame.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((72, 34, 136, 222), fill=(35, 55, 120))
    for x in (154, 178, 202, 226):
        draw.rectangle((x, 150, x + 10, 222), fill=(70, 70, 90))
    image.save(frame)

    analysis = _analyze_frame(frame, _args())

    assert analysis["gate"] == "retake_required"
    assert "strong_duplicate_silhouette_risk" in analysis["issue_codes"]


def test_broad_repair_mask_is_retake_required(tmp_path: Path) -> None:
    frame = tmp_path / "frame.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 255, 180), fill=(198, 198, 198))
    draw.rectangle((88, 34, 150, 222), fill=(24, 42, 74))
    image.save(frame)

    analysis = _analyze_frame(frame, _args())

    assert analysis["mask_coverage"] > _args().max_mask_coverage
    assert analysis["gate"] == "retake_required"
    assert "repair_mask_too_large" in analysis["issue_codes"]


def test_normal_skirt_and_two_feet_are_not_double_foot_retake(tmp_path: Path) -> None:
    frame = tmp_path / "normal_walk.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((114, 28, 142, 56), fill=(58, 38, 28))
    draw.rectangle((108, 56, 148, 126), fill=(20, 40, 95))
    draw.polygon(((106, 126), (150, 126), (162, 162), (94, 162)), fill=(20, 40, 95))
    draw.rectangle((110, 162, 122, 212), fill=(245, 205, 190))
    draw.rectangle((136, 162, 148, 212), fill=(245, 205, 190))
    draw.ellipse((96, 204, 126, 224), fill=(28, 24, 28))
    draw.ellipse((132, 204, 162, 224), fill=(28, 24, 28))
    image.save(frame)

    analysis = _analyze_frame(frame, _args())

    assert analysis["lower_body_blob_count"] <= 2
    assert "double_foot_or_duplicate_leg_risk" not in analysis["issue_codes"]
    assert analysis["gate"] != "retake_required"


def test_visual_review_labels_report_guides_and_foot_artifacts(tmp_path: Path) -> None:
    frame = tmp_path / "guide_and_shadow.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((112, 26, 144, 58), fill=(58, 38, 28))
    draw.rectangle((104, 58, 152, 132), fill=(20, 40, 95))
    draw.rectangle((110, 132, 124, 214), fill=(245, 205, 190))
    draw.rectangle((136, 132, 150, 214), fill=(245, 205, 190))
    draw.ellipse((96, 206, 128, 226), fill=(28, 24, 28))
    draw.ellipse((134, 206, 166, 226), fill=(28, 24, 28))
    draw.line((196, 58, 228, 96), fill=(230, 40, 30), width=2)
    draw.ellipse((170, 218, 222, 236), fill=(218, 206, 196))
    image.save(frame)

    analysis = _analyze_frame(frame, _args())

    assert "visible_guide_line_leakage_review" in analysis["review_labels"]
    assert "foot_shadow_or_contact_artifact_review" in analysis["review_labels"]


def test_retake_gate_drives_retake_recommendation() -> None:
    recommendation = _recommendation(
        {"retake_required": 1, "repair_candidate": 7},
        {"repair_mask_too_large": 1},
        repaired=0,
    )

    assert recommendation == "retake_or_retrim_span_before_refine"


def test_candidate_status_stays_selected_proof_when_review_labels_remain() -> None:
    status = _candidate_status(
        {"no_repair_needed": 120},
        {},
        {"foot_shadow_or_contact_artifact_review": 12},
    )

    assert status == "selected_proof_only"
