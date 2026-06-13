from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan_masked_corrections.py"
_SPEC = importlib.util.spec_from_file_location("plan_masked_corrections", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_build_plan_classifies_local_inpaint_and_retake() -> None:
    region = {
        "frame_reports": [
            _frame(0, [], 0.05, 0.01),
            _frame(1, ["lower_body_pale_afterimage_review"], 0.08, 0.02),
            _frame(2, ["silhouette_redraw_jitter_review"], 0.08, 0.22),
        ]
    }

    plan = _MODULE.build_plan(
        region,
        None,
        max_local_mask_coverage=0.18,
        max_local_temporal_delta=0.18,
    )

    assert plan["frame_plans"][0]["action"] == "postprocess_only"
    assert plan["frame_plans"][1]["action"] == "local_inpaint_candidate"
    assert plan["frame_plans"][1]["target_regions"] == ["lower_body"]
    assert plan["frame_plans"][2]["action"] == "retake_required"


def test_cli_writes_plan_and_merges_artifact_gate(tmp_path: Path) -> None:
    region = tmp_path / "region.json"
    region.write_text(json.dumps({"frame_reports": [_frame(0, [], 0.04, 0.01)]}), encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text(
        json.dumps({"frame_reports": [{"index": 0, "gate": "retake_required", "issue_codes": ["repair_mask_too_large"]}]}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--region-report",
            str(region),
            "--artifact-report",
            str(artifact),
            "--output-root",
            str(tmp_path / "plans"),
            "--run-label",
            "plan_test",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    plan = json.loads(Path(payload["plan"]).read_text(encoding="utf-8"))

    assert plan["frame_plans"][0]["action"] == "retake_required"
    assert "artifact_gate_retake_required" in plan["frame_plans"][0]["reasons"]


def _frame(index: int, labels: list[str], coverage: float, temporal: float) -> dict:
    return {
        "index": index,
        "issue_labels": labels,
        "regions": {
            "lower_body": {"coverage": coverage, "temporal_delta": temporal},
            "feet_contact": {"coverage": coverage / 2, "temporal_delta": temporal / 2},
        },
    }
