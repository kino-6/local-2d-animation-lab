from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


STRUCTURAL_LABELS = {
    "silhouette_redraw_jitter_review",
    "strong_duplicate_silhouette_risk",
    "double_foot_or_duplicate_leg_risk",
    "duplicate_silhouette_area_high",
    "repair_mask_too_large",
}

LOCAL_INPAINT_LABELS = {
    "lower_body_pale_afterimage_review",
    "foot_shadow_or_contact_artifact_review",
    "skin_colored_afterimage_near_legs_review",
    "cloak_or_hair_trail_review",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan masked correction actions from region and artifact reports.")
    parser.add_argument("--region-report", required=True, type=Path)
    parser.add_argument("--artifact-report", default=None, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--max-local-mask-coverage", default=0.18, type=float)
    parser.add_argument("--max-local-temporal-delta", default=0.18, type=float)
    args = parser.parse_args()

    region_payload = _read_json(args.region_report)
    artifact_payload = _read_json(args.artifact_report) if args.artifact_report else None
    plan = build_plan(
        region_payload,
        artifact_payload,
        max_local_mask_coverage=args.max_local_mask_coverage,
        max_local_temporal_delta=args.max_local_temporal_delta,
    )
    label = _safe_label(args.run_label or f"{args.region_report.parent.name}_correction_plan")
    run_dir = build_timestamped_run_dir(args.output_root, "masked_correction_plan", label)
    write_run_profile(run_dir, category="masked_correction_plan", label=label, args=args)
    plan["source_reports"] = {
        "region_report": str(args.region_report),
        "artifact_report": str(args.artifact_report) if args.artifact_report else None,
    }
    plan_path = run_dir / "masked_correction_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "plan": str(plan_path), **plan}, indent=2, ensure_ascii=False))


def build_plan(
    region_payload: dict[str, Any],
    artifact_payload: dict[str, Any] | None,
    *,
    max_local_mask_coverage: float,
    max_local_temporal_delta: float,
) -> dict[str, Any]:
    artifact_by_index = _artifact_by_index(artifact_payload)
    frame_plans: list[dict[str, Any]] = []
    for frame in region_payload.get("frame_reports", []):
        index = int(frame["index"])
        artifact = artifact_by_index.get(index, {})
        labels = set(str(label) for label in frame.get("issue_labels", []))
        labels.update(str(code) for code in artifact.get("issue_codes", []))
        labels.update(str(label) for label in artifact.get("review_labels", []))
        region_metrics = frame.get("regions", {})
        max_coverage = max((float(region.get("coverage", 0.0)) for region in region_metrics.values()), default=0.0)
        max_local_artifact_coverage = _max_local_artifact_coverage(region_metrics)
        max_temporal = max((float(region.get("temporal_delta", 0.0)) for region in region_metrics.values()), default=0.0)
        action, reasons = _action_for(
            labels,
            max_local_artifact_coverage=max_local_artifact_coverage,
            max_temporal_delta=max_temporal,
            artifact_gate=str(artifact.get("gate", "")),
            max_local_mask_coverage=max_local_mask_coverage,
            max_local_temporal_delta=max_local_temporal_delta,
        )
        target_regions = _target_regions(region_metrics, labels)
        frame_plans.append(
            {
                "index": index,
                "action": action,
                "reasons": reasons,
                "labels": sorted(labels),
                "target_regions": target_regions,
                "max_region_coverage": round(max_coverage, 5),
                "max_local_artifact_coverage": round(max_local_artifact_coverage, 5),
                "max_region_temporal_delta": round(max_temporal, 5),
                "artifact_gate": artifact.get("gate"),
                "before_region_metrics": region_metrics,
                "after_region_metrics": None,
            }
        )
    return {
        "status": "completed",
        "frame_count": len(frame_plans),
        "summary": _summarize(frame_plans),
        "frame_plans": frame_plans,
        "policy": {
            "max_local_mask_coverage": max_local_mask_coverage,
            "max_local_temporal_delta": max_local_temporal_delta,
            "structural_labels": sorted(STRUCTURAL_LABELS),
            "local_inpaint_labels": sorted(LOCAL_INPAINT_LABELS),
        },
    }


def _action_for(
    labels: set[str],
    *,
    max_local_artifact_coverage: float,
    max_temporal_delta: float,
    artifact_gate: str,
    max_local_mask_coverage: float,
    max_local_temporal_delta: float,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if artifact_gate == "retake_required":
        reasons.append("artifact_gate_retake_required")
    if labels & STRUCTURAL_LABELS:
        reasons.append("structural_label_present")
    if max_local_artifact_coverage > max_local_mask_coverage:
        reasons.append("local_mask_too_large")
    if max_temporal_delta > max_local_temporal_delta:
        reasons.append("temporal_delta_too_high")
    if reasons:
        return "retake_required", reasons
    if labels & LOCAL_INPAINT_LABELS:
        return "local_inpaint_candidate", ["small_local_artifact_labels"]
    return "postprocess_only", ["no_local_artifact_labels"]


def _target_regions(region_metrics: dict[str, Any], labels: set[str]) -> list[str]:
    targets = []
    if "lower_body_pale_afterimage_review" in labels or "skin_colored_afterimage_near_legs_review" in labels:
        targets.append("lower_body")
    if "foot_shadow_or_contact_artifact_review" in labels:
        targets.append("feet_contact")
    if "cloak_or_hair_trail_review" in labels:
        targets.append("cloak_or_hair_trail")
    return [target for target in targets if target in region_metrics]


def _max_local_artifact_coverage(region_metrics: dict[str, Any]) -> float:
    artifact_keys = (
        "pale_afterimage_coverage",
        "contact_shadow_coverage",
        "trail_coverage",
    )
    values: list[float] = []
    for region in region_metrics.values():
        for key in artifact_keys:
            if key in region:
                values.append(float(region.get(key, 0.0)))
    if values:
        return max(values, default=0.0)

    # Synthetic tests and legacy reports may only have coarse coverage.
    # Treat it as a local mask estimate only when artifact-specific metrics are absent.
    return max((float(region.get("coverage", 0.0)) for region in region_metrics.values()), default=0.0)


def _artifact_by_index(payload: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not payload:
        return {}
    reports = payload.get("frame_reports", [])
    return {int(report["index"]): report for report in reports if "index" in report}


def _summarize(frame_plans: list[dict[str, Any]]) -> dict[str, Any]:
    actions: dict[str, int] = {}
    labels: dict[str, int] = {}
    for plan in frame_plans:
        actions[plan["action"]] = actions.get(plan["action"], 0) + 1
        for label in plan["labels"]:
            labels[label] = labels.get(label, 0) + 1
    return {"action_counts": actions, "label_counts": labels}


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "masked_correction_plan"


if __name__ == "__main__":
    main()
