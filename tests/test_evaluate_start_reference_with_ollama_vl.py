from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_start_reference_with_ollama_vl.py"
_SPEC = importlib.util.spec_from_file_location("evaluate_start_reference_with_ollama_vl", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_start_reference_consistency_blocks_front_view_and_bad_shoes() -> None:
    payload = {
        "full_body_0_5": 4,
        "side_view_profile_0_5": 1,
        "walk_contact_pose_0_5": 2,
        "shoe_readability_0_5": 1,
        "is_full_body": True,
        "is_right_facing_side_view": False,
        "has_readable_separated_shoes": False,
        "is_model_sheet_or_turnaround": False,
        "has_secondary_character_or_prop": False,
        "is_walk_ready_start_reference": True,
        "visible_issues": [],
    }

    result = _MODULE._apply_start_reference_consistency_rules(payload, None)

    assert result["is_walk_ready_start_reference"] is False
    assert "local_vl_not_right_facing_side_view" in result["blocking_reasons"]
    assert "local_vl_shoes_not_readable" in result["blocking_reasons"]


def test_start_reference_consistency_applies_deterministic_blockers() -> None:
    payload = {
        "full_body_0_5": 5,
        "side_view_profile_0_5": 4,
        "walk_contact_pose_0_5": 4,
        "shoe_readability_0_5": 4,
        "is_full_body": True,
        "is_right_facing_side_view": True,
        "has_readable_separated_shoes": True,
        "is_model_sheet_or_turnaround": False,
        "has_secondary_character_or_prop": False,
        "is_walk_ready_start_reference": True,
        "visible_issues": [],
    }
    deterministic = {
        "selected": {
            "name": "candidate",
            "selection_status": "manual_review_or_retake",
            "issue_codes": ["shoes_unreadable"],
        }
    }

    result = _MODULE._apply_start_reference_consistency_rules(payload, deterministic)

    assert result["is_walk_ready_start_reference"] is False
    assert "deterministic_selection_not_candidate_ok" in result["blocking_reasons"]
    assert "deterministic_shoes_unreadable" in result["blocking_reasons"]


def test_deterministic_start_status_is_nonblocking_for_candidate_ok() -> None:
    status = _MODULE._deterministic_start_status(
        {"selected": {"name": "ok", "selection_status": "candidate_ok", "issue_codes": []}}
    )

    assert status["blocking"] is False
    assert status["selected_name"] == "ok"
