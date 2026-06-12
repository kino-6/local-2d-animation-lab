from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_action_keyframe_candidates.py"
_SPEC = importlib.util.spec_from_file_location("generate_action_keyframe_candidates", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_action_candidate_prompt_templates_cover_run_and_hit() -> None:
    run = _MODULE.ACTION_CANDIDATES["run"][0].positive_template.format(identity_traits="black yellow armor")
    hit = _MODULE.ACTION_CANDIDATES["hit_heavy"][0].positive_template.format(identity_traits="black yellow armor")

    assert "running pose" in run
    assert "heavy damage recoil" in hit
    assert "black yellow armor" in run
    assert "black yellow armor" in hit


def test_action_pose_images_are_distinct() -> None:
    run = _MODULE._pose_image("run_peak", 256, 256)
    hit = _MODULE._pose_image("hit_heavy_recoil", 256, 256)

    assert run.size == (256, 256)
    assert hit.size == (256, 256)
    assert run.tobytes() != hit.tobytes()
