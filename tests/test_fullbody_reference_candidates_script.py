from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_fullbody_reference_candidates.py"
_SPEC = importlib.util.spec_from_file_location("generate_fullbody_reference_candidates", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

_workflow = _MODULE._workflow
_assess_candidate = _MODULE._assess_candidate
_select_candidate = _MODULE._select_candidate


def test_workflow_routes_controlnet_conditioning_into_sampler() -> None:
    args = SimpleNamespace(
        checkpoint="novaOrangeXL_v120.safetensors",
        width=1024,
        height=1024,
        steps=32,
        cfg=5.6,
        sampler="dpmpp_2m",
        scheduler="karras",
        controlnet="SDXL\\OpenPoseXL2.safetensors",
        controlnet_strength=0.72,
    )

    workflow = _workflow(args, "positive", "negative", 123, "pose.png", "strict_side")

    assert workflow["1"]["inputs"]["ckpt_name"] == "novaOrangeXL_v120.safetensors"
    assert workflow["5"]["inputs"]["positive"] == ["10", 0]
    assert workflow["5"]["inputs"]["negative"] == ["10", 1]
    assert workflow["8"]["inputs"]["image"] == "pose.png"
    assert workflow["10"]["inputs"]["control_net"] == ["9", 0]


def test_candidate_prompt_templates_accept_custom_identity_traits() -> None:
    template = _MODULE.CANDIDATES[0].positive_template

    positive = template.format(identity_traits="blonde character with black and yellow hooded armor")

    assert "blonde character with black and yellow hooded armor" in positive
    assert "brown bob haircut" not in positive


def test_assess_candidate_accepts_full_body_clean_candidate() -> None:
    assessment = _assess_candidate(
        {
            "main_bbox": [360, 90, 620, 940],
            "issue_codes": [],
        },
        {
            "score": 0.9,
            "hard_failure": False,
            "issue_codes": [],
        },
        1024,
        1024,
    )

    assert assessment["status"] == "candidate_ok"
    assert assessment["issue_codes"] == []


def test_assess_candidate_rejects_short_or_cropped_candidate() -> None:
    assessment = _assess_candidate(
        {
            "main_bbox": [380, 260, 660, 740],
            "issue_codes": [],
        },
        {
            "score": 0.9,
            "hard_failure": False,
            "issue_codes": [],
        },
        1024,
        1024,
    )

    assert assessment["status"] == "manual_review_or_retake"
    assert "not_full_body_enough" in assessment["issue_codes"]
    assert "feet_not_near_canvas_bottom" in assessment["issue_codes"]


def test_select_candidate_prefers_ok_status_then_score() -> None:
    rejected = {
        "name": "rejected_high_score",
        "assessment": {
            "status": "manual_review_or_retake",
            "selection_score": 2.0,
            "issue_codes": ["not_full_body_enough"],
        },
    }
    accepted = {
        "name": "accepted_lower_score",
        "assessment": {
            "status": "candidate_ok",
            "selection_score": 1.0,
            "issue_codes": [],
        },
    }

    assert _select_candidate([rejected, accepted]) is accepted


def test_assess_candidate_rejects_too_wide_side_reference() -> None:
    assessment = _assess_candidate(
        {
            "main_bbox": [150, 70, 850, 940],
            "issue_codes": [],
        },
        {
            "score": 0.9,
            "hard_failure": False,
            "issue_codes": [],
        },
        1024,
        1024,
    )

    assert assessment["status"] == "manual_review_or_retake"
    assert "foreground_too_wide_for_side_reference" in assessment["issue_codes"]
