from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate best PDCA assets in Godot from a summary JSON.")
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--godot", default=shutil.which("godot") or "godot")
    parser.add_argument("--godot-project", default=Path("godot"), type=Path)
    parser.add_argument("--raw-frames", action="store_true")
    args = parser.parse_args()

    results = validate_summary(
        summary_path=args.summary,
        godot=args.godot,
        godot_project=args.godot_project,
        prefer_composited=not args.raw_frames,
    )
    print(json.dumps(results, indent=2, ensure_ascii=False))
    if not all(result.get("ok", False) for result in results["results"]):
        raise SystemExit(1)


def validate_summary(
    summary_path: Path,
    godot: str,
    godot_project: Path,
    prefer_composited: bool = True,
) -> dict[str, Any]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    best_by_asset = summary.get("best_by_asset", {})
    results = []
    for asset, entry in best_by_asset.items():
        manifest = (Path(entry["run_dir"]) / "manifest.json").resolve()
        result = _run_godot(
            manifest=manifest,
            godot=godot,
            godot_project=godot_project,
            prefer_composited=prefer_composited,
        )
        result["asset"] = asset
        result["manifest"] = str(manifest)
        results.append(result)
    return {"summary": str(summary_path), "results": results}


def _run_godot(manifest: Path, godot: str, godot_project: Path, prefer_composited: bool) -> dict[str, Any]:
    command = [
        godot,
        "--headless",
        "--path",
        str(godot_project),
        "--script",
        "res://tests/e2e_runner.gd",
        "--",
        "--manifest",
        str(manifest),
    ]
    if not prefer_composited:
        command.append("--raw-frames")
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=90)
    payload = _last_json_line(completed.stdout)
    if completed.returncode != 0:
        payload = payload or {"ok": False, "error": completed.stderr.strip() or completed.stdout.strip()}
    return payload


def _last_json_line(output: str) -> dict[str, Any]:
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return json.loads(stripped)
    return {}


if __name__ == "__main__":
    main()
