from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_sprite_asset_quality_flow.py"
_SPEC = importlib.util.spec_from_file_location("run_sprite_asset_quality_flow", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_decide_status_deterministic_reject_overrides_local_vl_acceptance() -> None:
    decision = _MODULE.decide_status(
        {
            "summary": {
                "candidate_status": "rejected",
                "gate_counts": {"retake_required": 1},
            }
        },
        {
            "is_adoptable_as_animation_or_walk_endpoint": True,
        },
    )

    assert decision["status"] == "rejected_animation_candidate"
    assert decision["local_vl_role"] == "secondary_only"
    assert "deterministic_artifact_gate_rejected" in decision["reasons"]


def test_quality_flow_preserves_frame_count_and_links_reports(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(3):
        _frame(frames / f"frame_{index:03d}.png", offset=index)

    artifact = tmp_path / "artifact_repair_report.json"
    artifact.write_text(
        json.dumps(
            {
                "summary": {
                    "candidate_status": "rejected",
                    "gate_counts": {"retake_required": 1, "repair_candidate": 0, "no_repair_needed": 2},
                }
            }
        ),
        encoding="utf-8",
    )
    vl = tmp_path / "local_vl_eval.json"
    vl.write_text(
        json.dumps({"is_adoptable_as_animation_or_walk_endpoint": True}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--frames-dir",
            str(frames),
            "--output-root",
            str(tmp_path / "flow"),
            "--run-label",
            "flow_test",
            "--asset-name",
            "test_character",
            "--animation",
            "walk",
            "--fps",
            "12",
            "--columns",
            "3",
            "--artifact-report",
            str(artifact),
            "--local-vl-report",
            str(vl),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    manifest = json.loads(Path(payload["manifest"]).read_text(encoding="utf-8"))
    package_manifest = json.loads(Path(manifest["package"]["manifest"]).read_text(encoding="utf-8"))

    assert manifest["source_frame_count"] == 3
    assert manifest["foreground_extraction"]["frames"]
    assert len(list(Path(manifest["postprocess"]["frames_dir"]).glob("*.png"))) == 3
    assert manifest["status"] == "rejected_animation_candidate"
    assert package_manifest["status"] == "rejected_animation_candidate"
    assert str(artifact) in package_manifest["quality_reports"]
    assert str(vl) in package_manifest["quality_reports"]


def _frame(path: Path, *, offset: int) -> None:
    image = Image.new("RGBA", (96, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    x = 36 + offset
    draw.ellipse((x + 8, 12, x + 24, 28), fill=(230, 190, 150, 255))
    draw.rectangle((x + 4, 28, x + 28, 88), fill=(20, 30, 80, 255))
    draw.line((x + 10, 88, x + 2, 116), fill=(20, 20, 25, 255), width=5)
    draw.line((x + 22, 88, x + 32, 116), fill=(20, 20, 25, 255), width=5)
    image.save(path)
