import importlib.util
import json
from pathlib import Path

from PIL import Image


def test_export_source_probe_package_summarizes_decision(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    exporter = _load_exporter()

    contact = tmp_path / "source_contact_sheet.png"
    control = tmp_path / "control_contact_sheet.png"
    comparison = tmp_path / "comparison_sheet.png"
    for path in (contact, control, comparison):
        Image.new("RGB", (32, 32), (255, 255, 255)).save(path)

    motion_report = tmp_path / "motion_source_report.json"
    motion_report.write_text(
        json.dumps(
            {
                "source_frames": 8,
                "frame_count": 120,
                "mean_confidence": 0.37371,
                "source_filter": {
                    "min_frame_mean_confidence": 0.25,
                    "retained_source_indices": [12, 13, 17, 18, 19, 21, 22, 23],
                },
            }
        ),
        encoding="utf-8",
    )
    span_report = tmp_path / "span_selection_report.json"
    span_report.write_text(
        json.dumps({"selection": {"score": 0.28623, "hard_failures": 5, "start_index": 1, "end_index": 8}}),
        encoding="utf-8",
    )
    gate_report = tmp_path / "artifact_repair_report.json"
    gate_report.write_text(
        json.dumps(
            {
                "summary": {
                    "gate_counts": {"retake_required": 6, "repair_candidate": 1, "no_repair_needed": 1},
                    "issue_counts": {"duplicate_silhouette_area_high": 4},
                    "recommendation": "retake_or_retrim_span_before_refine",
                    "mean_mask_coverage": 0.24613,
                }
            }
        ),
        encoding="utf-8",
    )

    package = exporter(
        source_label="mixkit_35419",
        output_root=tmp_path / "source_probe_packages",
        source_contact_sheet=contact,
        motion_source_report=motion_report,
        control_contact_sheet=control,
        span_report=span_report,
        gate_report=gate_report,
        comparison_sheet=comparison,
        decision="reject",
        reasons=["kept only diagnostic-quality pose frames"],
    )

    manifest = json.loads(Path(package["manifest"]).read_text(encoding="utf-8"))
    assert manifest["decision"] == "reject"
    assert manifest["metrics"]["motion_source"]["source_frames"] == 8
    assert manifest["metrics"]["span"]["hard_failures"] == 5
    assert manifest["metrics"]["gate"]["gate_counts"]["retake_required"] == 6
    assert Path(package["summary"]).exists()


def _load_exporter():
    script = Path(__file__).resolve().parents[1] / "scripts" / "export_source_probe_package.py"
    spec = importlib.util.spec_from_file_location("export_source_probe_package", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.export_source_probe_package
