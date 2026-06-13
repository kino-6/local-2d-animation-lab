from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any

from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a compact LocalVL calibration set.")
    parser.add_argument("--case", action="append", default=[], help="name|image|expected_status|report1,report2")
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    args = parser.parse_args()

    if not args.case:
        raise ValueError("At least one --case is required.")
    label = _safe_label(args.run_label or "local_vl_calibration")
    run_dir = build_timestamped_run_dir(args.output_root, "local_vl_calibration", label)
    write_run_profile(run_dir, category="local_vl_calibration", label=label, args=args)
    images_dir = run_dir / "images"
    reports_dir = run_dir / "reports"
    images_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    cases = []
    for index, spec in enumerate(args.case):
        case = _parse_case(spec)
        image_output = images_dir / f"{index:02d}_{_safe_label(case['name'])}{case['image'].suffix}"
        shutil.copy2(case["image"], image_output)
        copied_reports = []
        deterministic = []
        for report in case["reports"]:
            output = reports_dir / f"{index:02d}_{_safe_label(case['name'])}_{report.name}"
            shutil.copy2(report, output)
            copied_reports.append(output)
            deterministic.append(_read_json(report))
        cases.append(
            {
                "name": case["name"],
                "image": str(image_output),
                "expected_status": case["expected_status"],
                "reports": [str(path) for path in copied_reports],
                "deterministic_gate_statuses": [_deterministic_summary(item) for item in deterministic],
            }
        )

    manifest = {
        "status": "completed",
        "purpose": "Calibrate LocalVL against deterministic sprite animation quality blockers.",
        "cases": cases,
    }
    manifest_path = run_dir / "local_vl_calibration_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "manifest": str(manifest_path), **manifest}, indent=2, ensure_ascii=False))


def _parse_case(spec: str) -> dict[str, Any]:
    parts = spec.split("|")
    if len(parts) != 4:
        raise ValueError("--case must be name|image|expected_status|report1,report2")
    reports = [Path(part) for part in parts[3].split(",") if part]
    return {"name": parts[0], "image": Path(parts[1]), "expected_status": parts[2], "reports": reports}


def _deterministic_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    return {
        "candidate_status": summary.get("candidate_status") or payload.get("candidate_status"),
        "gate_counts": summary.get("gate_counts", {}),
        "action_counts": summary.get("action_counts", {}),
        "review_label_counts": summary.get("review_label_counts", {}),
        "issue_label_counts": summary.get("issue_label_counts", {}),
        "label_counts": summary.get("label_counts", {}),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "case"


if __name__ == "__main__":
    main()
