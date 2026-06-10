from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a concise animation viability report from a PDCA summary.")
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(args.summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(args.output)


def build_report(summary_path: Path) -> str:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    lines = [
        "# Animation Viability Report",
        "",
        f"Source summary: `{summary_path}`",
        "",
        "## Verdict",
        "",
    ]
    best = summary.get("best_by_asset", {})
    all_pass = True
    for asset, result in best.items():
        viability = result.get("animation_viability", {})
        score = float(viability.get("score", 0.0) or 0.0)
        if score < 0.75:
            all_pass = False
        lines.append(f"- `{asset}`: viability `{score:.3f}`, score `{float(result.get('score', 0.0)):.3f}`")
    if all_pass:
        overall = "Overall: **acceptable technical rig prototype**."
        player_facing = "Player-facing verdict: **not yet production animation quality**."
    else:
        overall = "Overall: **not yet acceptable as an animation prototype**."
        player_facing = "Player-facing verdict: **not acceptable**."
    lines.extend(
        [
            "",
            overall,
            "",
            player_facing,
            "",
            "## Adopted Prototype Assets",
            "",
        ]
    )
    for asset, result in best.items():
        lines.extend(_asset_lines(asset, result))
    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- This report checks animation mechanics, not final illustration quality.",
            "- Rigged outputs are preferred for prototype review because they use stable parts and deterministic motion.",
            "- ComfyUI outputs remain useful for visual target exploration, but not as practical animation frames yet.",
            "- Next quality step is replacing simple procedural parts with reference-derived or generated parts while preserving the rig.",
            "",
        ]
    )
    return "\n".join(lines)


def _asset_lines(asset: str, result: dict[str, Any]) -> list[str]:
    viability = result.get("animation_viability", {})
    summary = viability.get("summary", {})
    return [
        f"### {asset}",
        "",
        f"- run: `{result.get('run_dir')}`",
        f"- contact sheet: `{result.get('contact_sheet')}`",
        f"- preview GIF: `{result.get('preview_gif')}`",
        f"- manifest: `{result.get('manifest')}`",
        f"- viability score: `{viability.get('score')}`",
        f"- loop delta: `{summary.get('loop_delta')}`",
        f"- mean frame delta: `{summary.get('mean_frame_delta')}`",
        f"- max pose delta: `{summary.get('max_pose_delta')}`",
        f"- issues: `{result.get('issues', [])}`",
        "",
    ]


if __name__ == "__main__":
    main()
