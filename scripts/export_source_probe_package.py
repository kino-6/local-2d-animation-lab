from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any

from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a compact source-motion probe package.")
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--source-video", type=Path)
    parser.add_argument("--source-contact-sheet", type=Path)
    parser.add_argument("--sdpose-report", type=Path)
    parser.add_argument("--motion-source-report", type=Path)
    parser.add_argument("--control-contact-sheet", type=Path)
    parser.add_argument("--span-report", type=Path)
    parser.add_argument("--gate-report", type=Path)
    parser.add_argument("--comparison-sheet", type=Path)
    parser.add_argument("--decision", choices=("accept", "diagnostic_only", "reject"), required=True)
    parser.add_argument("--reason", action="append", default=[])
    args = parser.parse_args()

    package = export_source_probe_package(
        source_label=args.source_label,
        output_root=args.output_root,
        source_video=args.source_video,
        source_contact_sheet=args.source_contact_sheet,
        sdpose_report=args.sdpose_report,
        motion_source_report=args.motion_source_report,
        control_contact_sheet=args.control_contact_sheet,
        span_report=args.span_report,
        gate_report=args.gate_report,
        comparison_sheet=args.comparison_sheet,
        decision=args.decision,
        reasons=args.reason,
    )
    print(package["summary"])
    print(json.dumps(package, indent=2, ensure_ascii=False))


def export_source_probe_package(
    source_label: str,
    output_root: Path,
    source_video: Path | None = None,
    source_contact_sheet: Path | None = None,
    sdpose_report: Path | None = None,
    motion_source_report: Path | None = None,
    control_contact_sheet: Path | None = None,
    span_report: Path | None = None,
    gate_report: Path | None = None,
    comparison_sheet: Path | None = None,
    decision: str = "diagnostic_only",
    reasons: list[str] | None = None,
) -> dict[str, Any]:
    label = _safe_label(source_label)
    package_dir = build_timestamped_run_dir(output_root, "source_probe_package", label)
    write_run_profile(
        package_dir,
        category="source_probe_package",
        label=label,
        extra={"decision": decision, "reasons": reasons or []},
    )
    evidence_dir = package_dir / "evidence"
    reports_dir = package_dir / "reports"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    copied = {
        "source_video": _copy_optional(source_video, evidence_dir),
        "source_contact_sheet": _copy_optional(source_contact_sheet, evidence_dir),
        "control_contact_sheet": _copy_optional(control_contact_sheet, evidence_dir),
        "comparison_sheet": _copy_optional(comparison_sheet, evidence_dir),
        "sdpose_report": _copy_optional(sdpose_report, reports_dir),
        "motion_source_report": _copy_optional(motion_source_report, reports_dir),
        "span_report": _copy_optional(span_report, reports_dir),
        "gate_report": _copy_optional(gate_report, reports_dir),
    }
    metrics = {
        "motion_source": _motion_source_metrics(motion_source_report),
        "span": _span_metrics(span_report),
        "gate": _gate_metrics(gate_report),
    }
    summary = _summary_text(
        source_label=source_label,
        decision=decision,
        reasons=reasons or [],
        copied=copied,
        metrics=metrics,
    )
    summary_path = package_dir / "source_probe_summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    manifest = {
        "source_label": source_label,
        "decision": decision,
        "reasons": reasons or [],
        "metrics": metrics,
        "evidence": {key: _repo_relative(value) if value else None for key, value in copied.items()},
        "summary": _repo_relative(summary_path),
    }
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "package_dir": str(package_dir),
        "summary": str(summary_path),
        "manifest": str(manifest_path),
        "decision": decision,
        "metrics": metrics,
    }


def _copy_optional(source: Path | None, target_dir: Path) -> Path | None:
    if source is None or not source.exists():
        return None
    output = target_dir / source.name
    shutil.copy2(source, output)
    return output


def _motion_source_metrics(path: Path | None) -> dict[str, Any]:
    data = _read_json(path)
    if not data:
        return {}
    source_filter = data.get("source_filter", {})
    return {
        "source_frames": data.get("source_frames"),
        "frame_count": data.get("frame_count"),
        "mean_confidence": data.get("mean_confidence"),
        "retained_source_indices": source_filter.get("retained_source_indices"),
        "min_frame_mean_confidence": source_filter.get("min_frame_mean_confidence"),
    }


def _span_metrics(path: Path | None) -> dict[str, Any]:
    data = _read_json(path)
    if not data:
        return {}
    selection = data.get("selection", {})
    return {
        "score": selection.get("score"),
        "hard_failures": selection.get("hard_failures"),
        "start_index": selection.get("start_index"),
        "end_index": selection.get("end_index"),
    }


def _gate_metrics(path: Path | None) -> dict[str, Any]:
    data = _read_json(path)
    if not data:
        return {}
    summary = data.get("summary", {})
    return {
        "gate_counts": summary.get("gate_counts"),
        "issue_counts": summary.get("issue_counts"),
        "recommendation": summary.get("recommendation"),
        "mean_mask_coverage": summary.get("mean_mask_coverage"),
    }


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_text(
    source_label: str,
    decision: str,
    reasons: list[str],
    copied: dict[str, Path | None],
    metrics: dict[str, Any],
) -> str:
    reason_lines = "\n".join(f"- {reason}" for reason in reasons) or "- not recorded"
    evidence_lines = "\n".join(
        f"- {key}: `{_repo_relative(path)}`" for key, path in copied.items() if path is not None
    ) or "- none"
    metrics_text = json.dumps(metrics, indent=2, ensure_ascii=False)
    return f"""# Source Motion Probe

## Summary

- source_label: `{source_label}`
- decision: `{decision}`

## Reasons

{reason_lines}

## Metrics

```json
{metrics_text}
```

## Evidence

{evidence_lines}
"""


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "source_probe"


if __name__ == "__main__":
    main()
