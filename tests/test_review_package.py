from pathlib import Path
import importlib.util

from PIL import Image


def test_export_review_package_writes_godot_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    export_review_package = _load_exporter()
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(3):
        Image.new("RGB", (32, 48), (255, 255 - index * 20, 255)).save(frames / f"frame_{index:03d}.png")
    comparison = tmp_path / "comparison_sheet.png"
    Image.new("RGB", (64, 64), (240, 240, 240)).save(comparison)

    package = export_review_package(
        frames_dir=frames,
        output_root=tmp_path / "review_packages",
        run_label="sample",
        action="run",
        character_id="anima_00013",
        fps=8,
        comparison_sheets=[comparison],
        visual_decision="selected_proof_only",
        visual_labels=["endpoint_warp_or_pose_teleport_review"],
        motion_score=12.5,
        artifact_gate_summary="no_repair_needed: 3/3",
        godot_status="ok",
    )

    manifest = Path(package["manifest"]).read_text(encoding="utf-8")
    assert '"frame_count": 3' in manifest
    assert '"action": "run"' in manifest
    assert '"visual_decision": "selected_proof_only"' in manifest
    assert '"endpoint_warp_or_pose_teleport_review"' in manifest
    assert '"motion_score": 12.5' in manifest
    assert '"godot_status": "ok"' in manifest
    assert (Path(package["review_dir"]) / "preview.gif").exists()
    assert (Path(package["review_dir"]) / "contact_sheet.png").exists()
    assert package["comparison_sheets"]


def test_export_review_package_keeps_duplicate_report_names(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    export_review_package = _load_exporter()
    frames = tmp_path / "frames"
    frames.mkdir()
    Image.new("RGB", (32, 48), (255, 255, 255)).save(frames / "frame_000.png")
    left_dir = tmp_path / "left"
    right_dir = tmp_path / "right"
    left_dir.mkdir()
    right_dir.mkdir()
    left_report = left_dir / "report.json"
    right_report = right_dir / "report.json"
    left_report.write_text('{"side":"left"}\n', encoding="utf-8")
    right_report.write_text('{"side":"right"}\n', encoding="utf-8")

    package = export_review_package(
        frames_dir=frames,
        output_root=tmp_path / "review_packages",
        run_label="duplicate_reports",
        source_reports=[left_report, right_report],
    )

    copied = [Path(path).name for path in package["copied_reports"]]
    assert copied == ["report.json", "report_01.json"]


def _load_exporter():
    script = Path(__file__).resolve().parents[1] / "scripts" / "export_review_package.py"
    spec = importlib.util.spec_from_file_location("export_review_package", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.export_review_package
