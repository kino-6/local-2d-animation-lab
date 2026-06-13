from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from natural_sprite_lab.quality import analyze_frame_quality, analyze_motion_readability, prepare_analysis_frame
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the standardized postprocess, quality gate, LocalVL, and packaging flow."
    )
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--asset-name", default="character")
    parser.add_argument("--animation", default="walk")
    parser.add_argument("--fps", default=12, type=int)
    parser.add_argument("--columns", default=11, type=int)
    parser.add_argument("--frame-width", default=512, type=int)
    parser.add_argument("--frame-height", default=768, type=int)
    parser.add_argument("--target-height", default=704, type=int)
    parser.add_argument("--background-threshold", default=100, type=int)
    parser.add_argument("--background-min-channel", default=185, type=int)
    parser.add_argument("--pad", default=32, type=int)
    parser.add_argument("--source-generation-report", action="append", default=[], type=Path)
    parser.add_argument("--artifact-report", default=None, type=Path)
    parser.add_argument("--local-vl-report", default=None, type=Path)
    parser.add_argument("--skip-artifact-gate", action="store_true")
    parser.add_argument("--skip-local-vl", action="store_true")
    parser.add_argument("--motion-metric", choices=("global", "foreground", "max"), default="foreground")
    parser.add_argument("--motion-analysis-max-size", default=512, type=int)
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    args = parser.parse_args()

    source_paths = sorted(args.frames_dir.glob("*.png"), key=_frame_index)
    if not source_paths:
        raise FileNotFoundError(f"No PNG frames found: {args.frames_dir}")

    label = _safe_label(args.run_label or f"{args.asset_name}_{args.animation}_quality_flow")
    run_dir = build_timestamped_run_dir(args.output_root, "sprite_asset_quality_flow", label)
    write_run_profile(
        run_dir,
        category="sprite_asset_quality_flow",
        label=label,
        args=args,
        memo="End-to-end quality flow: foreground extraction, stabilization, deterministic gate, LocalVL, and packaging.",
    )

    foreground_package = _run_json(
        [
            sys.executable,
            "scripts/package_game_sprite_asset.py",
            "--frames-dir",
            str(args.frames_dir),
            "--output-root",
            str(run_dir / "foreground_extract"),
            "--run-label",
            "foreground",
            "--asset-name",
            args.asset_name,
            "--animation",
            args.animation,
            "--fps",
            str(args.fps),
            "--frame-width",
            str(args.frame_width),
            "--frame-height",
            str(args.frame_height),
            "--target-height",
            str(args.target_height),
            "--background-threshold",
            str(args.background_threshold),
            "--background-min-channel",
            str(args.background_min_channel),
            "--pad",
            str(args.pad),
            "--columns",
            str(args.columns),
            "--status",
            "foreground_extraction_intermediate",
        ],
        timeout=args.timeout_seconds,
    )
    foreground_frames = Path(foreground_package["frames"])
    foreground_count = len(list(foreground_frames.glob("*.png")))
    if foreground_count != len(source_paths):
        raise RuntimeError(f"Frame count changed during foreground extraction: {len(source_paths)} -> {foreground_count}")

    stabilize = _run_json(
        [
            sys.executable,
            "scripts/stabilize_sprite_sequence.py",
            "--frames-dir",
            str(foreground_frames),
            "--output-root",
            str(run_dir / "postprocess"),
            "--run-label",
            "stabilized",
            "--fps",
            str(args.fps),
            "--columns",
            str(args.columns),
        ],
        timeout=args.timeout_seconds,
    )
    stabilized_frames = Path(stabilize["frames"])
    stabilized_count = len(list(stabilized_frames.glob("*.png")))
    if stabilized_count != len(source_paths):
        raise RuntimeError(f"Frame count changed during postprocess: {len(source_paths)} -> {stabilized_count}")
    motion_readability = _motion_readability_report(
        stabilized_frames,
        action=args.animation,
        output_dir=run_dir / "motion_readability",
        motion_metric=args.motion_metric,
        analysis_max_size=args.motion_analysis_max_size,
    )
    motion_readability_report = Path(motion_readability["report"])

    artifact_report = args.artifact_report
    artifact_payload = _read_json(artifact_report) if artifact_report else None
    if artifact_report is None and not args.skip_artifact_gate:
        gate = _run_json(
            [
                sys.executable,
                "scripts/repair_frame_artifacts.py",
                "--frames-dir",
                str(stabilized_frames),
                "--output-root",
                str(run_dir / "quality_gates"),
                "--run-label",
                "artifact_gate",
                "--fps",
                str(args.fps),
                "--mask-only",
                "--analysis-max-size",
                "512",
                "--timeout-seconds",
                str(args.timeout_seconds),
                "--max-queue-size",
                "-1",
            ],
            timeout=args.timeout_seconds + 60,
        )
        artifact_report = Path(gate["report"]) if "report" in gate else _latest_report(run_dir / "quality_gates", "artifact_repair_report.json")
        artifact_payload = _read_json(artifact_report)

    local_vl_report = args.local_vl_report
    local_vl_payload = _read_json(local_vl_report) if local_vl_report else None
    if local_vl_report is None and not args.skip_local_vl:
        vl = _run_json(
            [
                sys.executable,
                "scripts/evaluate_sprite_with_ollama_vl.py",
                "--image",
                str(stabilize["contact_sheet"]),
                "--action",
                args.animation,
                "--output-root",
                str(run_dir / "local_vl"),
                "--run-label",
                "local_vl",
                "--timeout-seconds",
                str(args.timeout_seconds),
            ],
            timeout=args.timeout_seconds + 60,
        )
        local_vl_report = Path(vl["run_dir"]) / "local_vl_eval.json"
        local_vl_payload = _read_json(local_vl_report)

    decision = decide_status(artifact_payload, local_vl_payload, motion_readability)
    quality_reports = [
        path for path in [artifact_report, local_vl_report, motion_readability_report, *args.source_generation_report] if path
    ]
    package_cmd = [
        sys.executable,
        "scripts/package_game_sprite_asset.py",
        "--frames-dir",
        str(stabilized_frames),
        "--output-root",
        str(run_dir / "packages"),
        "--run-label",
        "package",
        "--asset-name",
        args.asset_name,
        "--animation",
        args.animation,
        "--fps",
        str(args.fps),
        "--frame-width",
        str(args.frame_width),
        "--frame-height",
        str(args.frame_height),
        "--target-height",
        str(args.target_height),
        "--background-threshold",
        str(args.background_threshold),
        "--background-min-channel",
        str(args.background_min_channel),
        "--pad",
        str(args.pad),
        "--columns",
        str(args.columns),
        "--status",
        decision["status"],
    ]
    for report in quality_reports:
        package_cmd.extend(["--quality-report", str(report)])
    package = _run_json(package_cmd, timeout=args.timeout_seconds)

    manifest = {
        "status": decision["status"],
        "decision": decision,
        "asset_name": args.asset_name,
        "animation": args.animation,
        "source_frames_dir": str(args.frames_dir),
        "source_frame_count": len(source_paths),
        "foreground_extraction": foreground_package,
        "postprocess": {
            "frames_dir": stabilize["frames"],
            "report": str(Path(stabilize["run_dir"]) / "stabilize_sprite_sequence_report.json"),
            "preview_gif": stabilize["preview_gif"],
            "contact_sheet": stabilize["contact_sheet"],
            "before_summary": stabilize["before_summary"],
            "after_summary": stabilize["after_summary"],
        },
        "artifact_gate_report": str(artifact_report) if artifact_report else None,
        "local_vl_report": str(local_vl_report) if local_vl_report else None,
        "motion_readability_report": str(motion_readability_report),
        "motion_readability": motion_readability["motion_readability"],
        "source_generation_reports": [str(path) for path in args.source_generation_report],
        "package": package,
        "quality_reports": [str(path) for path in quality_reports],
    }
    manifest_path = run_dir / "quality_flow_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "manifest": str(manifest_path), **manifest}, indent=2, ensure_ascii=False))


def decide_status(
    artifact_payload: dict[str, Any] | None,
    local_vl_payload: dict[str, Any] | None,
    motion_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    motion_status = (motion_payload or {}).get("motion_readability", {}).get("status")
    motion_issues = (motion_payload or {}).get("motion_readability", {}).get("issue_codes") or []
    if motion_status and motion_status != "passed":
        reasons.append("motion_readability_gate_rejected")
    artifact_status = None
    summary = artifact_payload.get("summary", {}) if artifact_payload else {}
    if artifact_payload:
        artifact_status = summary.get("candidate_status") or artifact_payload.get("candidate_status")
        gate_counts = summary.get("gate_counts", {})
        if artifact_status == "rejected" or int(gate_counts.get("retake_required", 0) or 0) > 0:
            reasons.append("deterministic_artifact_gate_rejected")
            return {
                "status": "rejected_animation_candidate",
                "artifact_status": artifact_status,
                "motion_status": motion_status,
                "local_vl_role": "secondary_only",
                "reasons": reasons,
            }
        if artifact_status == "selected_proof_only":
            reasons.append("deterministic_gate_selected_proof_only")
            return {
                "status": "selected_proof_only",
                "artifact_status": artifact_status,
                "motion_status": motion_status,
                "local_vl_role": "secondary_only",
                "reasons": reasons,
            }
    if motion_status and motion_status != "passed":
        return {
            "status": "rejected_animation_candidate",
            "artifact_status": artifact_status,
            "motion_status": motion_status,
            "motion_issue_codes": motion_issues,
            "local_vl_role": "secondary_only",
            "reasons": reasons,
        }

    endpoint_key = next(
        (key for key in (local_vl_payload or {}) if key.startswith("is_adoptable_as_animation_or_")),
        None,
    )
    vl_adoptable = bool(local_vl_payload.get(endpoint_key)) if endpoint_key and local_vl_payload else False
    if artifact_status in {"adopted_full_source", "adopted_animation_candidate"} and vl_adoptable:
        return {
            "status": "adopted_animation_candidate",
            "artifact_status": artifact_status,
            "motion_status": motion_status,
            "local_vl_role": "confirming_signal",
            "reasons": ["deterministic_gate_passed", "local_vl_confirmed"],
        }
    if artifact_payload:
        return {
            "status": "needs_manual_review",
            "artifact_status": artifact_status,
            "motion_status": motion_status,
            "local_vl_role": "secondary_only",
            "reasons": ["deterministic_gate_not_final"],
        }
    return {
        "status": "unreviewed_animation_candidate",
        "artifact_status": None,
        "motion_status": motion_status,
        "local_vl_role": "not_run",
        "reasons": ["artifact_gate_missing"],
    }


def _motion_readability_report(
    frames_dir: Path,
    *,
    action: str,
    output_dir: Path,
    motion_metric: str,
    analysis_max_size: int,
) -> dict[str, Any]:
    frame_paths = sorted(frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {frames_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir = output_dir / "analysis_frames"
    qualities = []
    previous = None
    for index, path in enumerate(frame_paths):
        analysis_path = prepare_analysis_frame(path, analysis_dir / f"analysis_{index:03d}.png", analysis_max_size)
        qualities.append(analyze_frame_quality(analysis_path, index=index, previous_path=previous))
        previous = analysis_path
    motion = analyze_motion_readability(qualities, action=action, motion_metric=motion_metric)
    payload = {
        "status": "completed",
        "source_frames_dir": str(frames_dir),
        "motion_readability": motion.to_dict(),
        "frame_quality": [quality.to_dict() for quality in qualities],
    }
    report_path = output_dir / "motion_readability_report.json"
    payload["report"] = str(report_path)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def _run_json(command: list[str], *, timeout: float) -> dict[str, Any]:
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    return _extract_last_json(completed.stdout)


def _extract_last_json(text: str) -> dict[str, Any]:
    starts = [index for index, char in enumerate(text) if char == "{"]
    for start in reversed(starts):
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No JSON object found in output: {text[-500:]}")


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_report(root: Path, name: str) -> Path:
    matches = sorted(root.rglob(name), key=lambda path: path.stat().st_mtime)
    if not matches:
        raise FileNotFoundError(name)
    return matches[-1]


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "sprite_quality_flow"


if __name__ == "__main__":
    main()
