from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_sprite_with_ollama_vl.py"
_SPEC = importlib.util.spec_from_file_location("evaluate_sprite_with_ollama_vl", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_consistency_rules_block_endpoint_when_action_is_not_readable() -> None:
    payload = {
        "action_readability_0_5": 2,
        "is_readable_run_action": False,
        "is_adoptable_as_still_sprite_proof": True,
        "is_adoptable_as_animation_or_run_endpoint": True,
        "visible_issues": [],
    }

    result = _MODULE._apply_consistency_rules(payload, "run")

    assert result["is_readable_run_action"] is False
    assert result["is_adoptable_as_animation_or_run_endpoint"] is False
    assert result["is_adoptable_as_still_sprite_proof"] is True
    assert result["visible_issues"]


def test_consistency_rules_keep_endpoint_when_action_is_readable() -> None:
    payload = {
        "action_readability_0_5": 4,
        "is_readable_run_action": True,
        "is_adoptable_as_still_sprite_proof": True,
        "is_adoptable_as_animation_or_run_endpoint": True,
        "visible_issues": [],
    }

    result = _MODULE._apply_consistency_rules(payload, "run")

    assert result["is_readable_run_action"] is True
    assert result["is_adoptable_as_animation_or_run_endpoint"] is True


def test_consistency_rules_coerce_string_visible_issues() -> None:
    payload = {
        "action_readability_0_5": 1,
        "is_readable_run_action": False,
        "is_adoptable_as_still_sprite_proof": True,
        "is_adoptable_as_animation_or_run_endpoint": True,
        "visible_issues": "Neutral standing pose, no run motion",
    }

    result = _MODULE._apply_consistency_rules(payload, "run")

    assert result["visible_issues"][0] == "Neutral standing pose, no run motion"
    assert all(len(issue) > 1 for issue in result["visible_issues"])


def test_deterministic_gate_rules_downgrade_overaccepted_local_vl() -> None:
    payload = {
        "action_readability_0_5": 5,
        "is_readable_walk_action": True,
        "is_adoptable_as_still_sprite_proof": True,
        "is_adoptable_as_animation_or_walk_endpoint": True,
        "visible_issues": [],
    }
    deterministic = {
        "summary": {
            "candidate_status": "rejected",
            "gate_counts": {"retake_required": 2},
            "review_label_counts": {"lower_body_pale_afterimage_review": 72},
        }
    }

    result = _MODULE._apply_deterministic_gate_rules(payload, "walk", [deterministic])

    assert result["is_adoptable_as_animation_or_walk_endpoint"] is False
    assert result["local_vl_role"] == "secondary_only"
    assert result["deterministic_override_applied"] is True
    assert "deterministic_candidate_status_rejected" in result["visible_issues"]


def test_deterministic_status_reads_region_plan_action_counts() -> None:
    status = _MODULE._deterministic_status(
        {
            "summary": {
                "action_counts": {"retake_required": 3},
                "label_counts": {"silhouette_redraw_jitter_review": 1},
            }
        }
    )

    assert status["blocking"] is True
    assert "masked_plan_retake_required_frames" in status["blocking_reasons"]
