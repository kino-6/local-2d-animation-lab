from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from PIL import Image

from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a compact review package for selected animation frames.")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--action", default="unknown")
    parser.add_argument("--character-id", default="unknown")
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--loop", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--source-report", action="append", default=[], type=Path)
    parser.add_argument("--comparison-sheet", action="append", default=[], type=Path)
    parser.add_argument("--source-command", default="")
    parser.add_argument("--visual-decision", default="unreviewed")
    parser.add_argument("--visual-label", action="append", default=[])
    parser.add_argument("--motion-score", default=None, type=float)
    parser.add_argument("--artifact-gate-summary", default="")
    parser.add_argument("--godot-status", default="")
    parser.add_argument("--validate-godot", action="store_true")
    parser.add_argument("--godot", default=shutil.which("godot") or "godot")
    parser.add_argument("--godot-project", default=Path("godot"), type=Path)
    args = parser.parse_args()

    package = export_review_package(
        frames_dir=args.frames_dir,
        output_root=args.output_root,
        run_label=args.run_label,
        action=args.action,
        character_id=args.character_id,
        fps=args.fps,
        loop=args.loop,
        source_reports=args.source_report,
        comparison_sheets=args.comparison_sheet,
        source_command=args.source_command,
        visual_decision=args.visual_decision,
        visual_labels=args.visual_label,
        motion_score=args.motion_score,
        artifact_gate_summary=args.artifact_gate_summary,
        godot_status=args.godot_status,
        validate_godot=args.validate_godot,
        godot=args.godot,
        godot_project=args.godot_project,
    )
    print(package["review_summary"])
    print(json.dumps(package, indent=2, ensure_ascii=False))


def export_review_package(
    frames_dir: Path,
    output_root: Path,
    run_label: str | None = None,
    action: str = "unknown",
    character_id: str = "unknown",
    fps: int = 8,
    loop: bool = True,
    source_reports: list[Path] | None = None,
    comparison_sheets: list[Path] | None = None,
    source_command: str = "",
    visual_decision: str = "unreviewed",
    visual_labels: list[str] | None = None,
    motion_score: float | None = None,
    artifact_gate_summary: str = "",
    godot_status: str = "",
    validate_godot: bool = False,
    godot: str = "godot",
    godot_project: Path = Path("godot"),
) -> dict[str, Any]:
    frame_paths = sorted(frames_dir.glob("*.png"), key=_frame_index)
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found: {frames_dir}")

    label = _safe_label(run_label or f"{frames_dir.parent.name}_review")
    review_dir = build_timestamped_run_dir(output_root, "review_package", label)
    write_run_profile(
        review_dir,
        category="review_package",
        label=label,
        extra={"action": action, "character_id": character_id, "visual_decision": visual_decision},
    )
    review_frames = review_dir / "frames"
    reports_dir = review_dir / "reports"
    review_frames.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    copied_frames = []
    for index, source in enumerate(frame_paths):
        output = review_frames / f"frame_{index:03d}.png"
        shutil.copy2(source, output)
        copied_frames.append(output)

    contact_sheet = make_contact_sheet(copied_frames, review_dir / "contact_sheet.png", columns=min(6, len(copied_frames)))
    preview_gif = make_preview_gif(copied_frames, review_dir / "preview.gif", duration_ms=round(1000 / fps), loop=loop)
    copied_reports = []
    for report in source_reports or []:
        if report.exists():
            output = _unique_path(reports_dir / report.name)
            shutil.copy2(report, output)
            copied_reports.append(output)
    copied_comparisons = []
    for sheet in comparison_sheets or []:
        if sheet.exists():
            output = review_dir / f"comparison_{len(copied_comparisons):02d}_{sheet.name}"
            shutil.copy2(sheet, output)
            copied_comparisons.append(output)

    first = Image.open(copied_frames[0])
    manifest = {
        "spec": {
            "action": action,
            "character_id": character_id,
            "frame_count": len(copied_frames),
            "fps": fps,
            "loop": loop,
            "width": first.width,
            "height": first.height,
        },
        "outputs": {
            "frame_paths": [_repo_relative(path) for path in copied_frames],
            "preview_gif": _repo_relative(preview_gif),
            "contact_sheet": _repo_relative(contact_sheet),
        },
        "review": {
            "source_frames_dir": str(frames_dir),
            "source_reports": [str(path) for path in source_reports or []],
            "copied_reports": [_repo_relative(path) for path in copied_reports],
            "comparison_sheets": [_repo_relative(path) for path in copied_comparisons],
            "source_command": source_command,
            "visual_decision": visual_decision,
            "visual_labels": visual_labels or [],
            "comparison_fields": {
                "motion_score": motion_score,
                "artifact_gate_summary": artifact_gate_summary,
                "visual_decision": visual_decision,
                "godot_status": godot_status,
            },
        },
    }
    manifest_path = review_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = _summary_text(
        action=action,
        character_id=character_id,
        frame_count=len(copied_frames),
        fps=fps,
        contact_sheet=contact_sheet,
        preview_gif=preview_gif,
        manifest_path=manifest_path,
        source_command=source_command,
        copied_reports=copied_reports,
        copied_comparisons=copied_comparisons,
        visual_decision=visual_decision,
        visual_labels=visual_labels or [],
        motion_score=motion_score,
        artifact_gate_summary=artifact_gate_summary,
        godot_status=godot_status,
    )
    summary_path = review_dir / "review_summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    godot_validation_path = None
    if validate_godot:
        validation = _run_godot_validation(manifest_path, godot, godot_project)
        godot_validation_path = review_dir / "godot_validation.json"
        godot_validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "review_dir": str(review_dir),
        "review_summary": str(summary_path),
        "manifest": str(manifest_path),
        "preview_gif": str(preview_gif),
        "contact_sheet": str(contact_sheet),
        "frame_count": len(copied_frames),
        "copied_reports": [str(path) for path in copied_reports],
        "comparison_sheets": [str(path) for path in copied_comparisons],
        "godot_validation": str(godot_validation_path) if godot_validation_path else None,
    }


def _summary_text(
    action: str,
    character_id: str,
    frame_count: int,
    fps: int,
    contact_sheet: Path,
    preview_gif: Path,
    manifest_path: Path,
    source_command: str,
    copied_reports: list[Path],
    copied_comparisons: list[Path],
    visual_decision: str,
    visual_labels: list[str],
    motion_score: float | None,
    artifact_gate_summary: str,
    godot_status: str,
) -> str:
    reports = "\n".join(f"- `{_repo_relative(path)}`" for path in copied_reports) or "- none"
    comparisons = "\n".join(f"- `{_repo_relative(path)}`" for path in copied_comparisons) or "- none"
    command = source_command or "not recorded"
    labels = ", ".join(visual_labels) or "none"
    motion = "not recorded" if motion_score is None else str(motion_score)
    artifact_gate = artifact_gate_summary or "not recorded"
    godot = godot_status or "not recorded"
    return f"""# Animation Review Package

## Summary

- action: `{action}`
- character_id: `{character_id}`
- frame_count: `{frame_count}`
- fps: `{fps}`
- preview: `{_repo_relative(preview_gif)}`
- contact_sheet: `{_repo_relative(contact_sheet)}`
- godot_manifest: `{_repo_relative(manifest_path)}`
- visual_decision: `{visual_decision}`
- visual_labels: `{labels}`
- motion_score: `{motion}`
- artifact_gate_summary: `{artifact_gate}`
- godot_status: `{godot}`

## Source Command

```text
{command}
```

## Reports

{reports}

## Comparison Sheets

{comparisons}

## Review Notes

- Inspect `preview.gif` for animation readability.
- Inspect `contact_sheet.png` for per-frame structure and identity stability.
- Use `manifest.json` with the Godot E2E runner for playback validation.
"""


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index:02d}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique path for {path}")


def _run_godot_validation(manifest_path: Path, godot: str, godot_project: Path) -> dict[str, Any]:
    command = [
        godot,
        "--headless",
        "--path",
        str(godot_project),
        "--script",
        "res://tests/e2e_runner.gd",
        "--",
        "--manifest",
        str(manifest_path.resolve()),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=90)
    payload = _last_json_line(completed.stdout)
    if completed.returncode != 0:
        payload = payload or {"ok": False, "error": completed.stderr.strip() or completed.stdout.strip()}
    payload["returncode"] = completed.returncode
    return payload


def _last_json_line(output: str) -> dict[str, Any]:
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return json.loads(stripped)
    return {}


def _frame_index(path: Path) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in path.stem).split()
    return int(digits[-1]) if digits else -1


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "review_package"


if __name__ == "__main__":
    main()
