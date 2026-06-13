from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_local_vl_calibration_set.py"


def test_build_local_vl_calibration_set_copies_image_and_reports(tmp_path: Path) -> None:
    image = tmp_path / "sheet.png"
    Image.new("RGB", (16, 16), (255, 255, 255)).save(image)
    report = tmp_path / "gate.json"
    report.write_text(
        json.dumps({"summary": {"candidate_status": "rejected", "gate_counts": {"retake_required": 1}}}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--output-root",
            str(tmp_path / "calibration"),
            "--run-label",
            "cal",
            "--case",
            f"rejected_walk|{image}|rejected_animation_candidate|{report}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    manifest = json.loads(Path(payload["manifest"]).read_text(encoding="utf-8"))

    assert manifest["cases"][0]["expected_status"] == "rejected_animation_candidate"
    assert Path(manifest["cases"][0]["image"]).exists()
    assert Path(manifest["cases"][0]["reports"][0]).exists()
    assert manifest["cases"][0]["deterministic_gate_statuses"][0]["candidate_status"] == "rejected"
