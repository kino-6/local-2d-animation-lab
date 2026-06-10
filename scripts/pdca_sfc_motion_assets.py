from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from natural_sprite_lab.action_catalog import DEFAULT_ASSET_RECIPES
from natural_sprite_lab.backends import RiggedSpriteBackend
from natural_sprite_lab.pipeline import run_pipeline
from natural_sprite_lab.planning import WalkCycleDirector


@dataclass(frozen=True)
class MotionConfig:
    name: str
    source_frames: int
    style: str


CONFIGS = [
    MotionConfig("sfc_120", 120, "sfc"),
    MotionConfig("sfc_60", 60, "sfc"),
    MotionConfig("puppet_120", 120, "puppet"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="PDCA sweep for SFC-style limited 2D animation motion.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_sfc_motion_pdca"), type=Path)
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--height", default=512, type=int)
    args = parser.parse_args()

    results = []
    director = WalkCycleDirector(use_ollama=False)
    for config in CONFIGS:
        backend = RiggedSpriteBackend(
            width=args.width,
            height=args.height,
            source_frame_count=config.source_frames,
            motion_style=config.style,
        )
        for recipe in DEFAULT_ASSET_RECIPES:
            run_id = f"{recipe.name}_{config.name}"
            outputs = run_pipeline(
                source_image=args.input,
                prompt=recipe.prompt,
                backend=backend,
                output_root=args.output_root,
                run_id=run_id,
                director=director,
            )
            evaluation = json.loads((outputs.run_dir / "evaluation_report.json").read_text(encoding="utf-8"))
            result = {
                "asset": recipe.name,
                "config": config.name,
                "style": config.style,
                "source_frames": config.source_frames,
                "score": evaluation["score"],
                "issues": evaluation["issues"],
                "animation_viability": evaluation.get("animation_viability", {}),
                "run_dir": str(outputs.run_dir),
                "contact_sheet": str(outputs.composited_contact_sheet_path or outputs.contact_sheet_path),
                "preview_gif": str(outputs.gif_path),
                "manifest": str(outputs.manifest_path),
            }
            results.append(result)
            viability = result["animation_viability"].get("score")
            print(
                f"{recipe.name}/{config.name}: "
                f"score={result['score']} viability={viability} {result['contact_sheet']}"
            )

    best_by_asset = {}
    for result in results:
        current = best_by_asset.get(result["asset"])
        if current is None or _rank(result) > _rank(current):
            best_by_asset[result["asset"]] = result

    summary = {
        "pdca_rule": (
            "Plan high-density motion first, keep nonessential body parts held, "
            "then sample down into game-ready frame counts."
        ),
        "configs": [config.__dict__ for config in CONFIGS],
        "best_by_asset": best_by_asset,
        "results": results,
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_root / "sfc_motion_pdca_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Summary: {summary_path}")


def _rank(result: dict) -> tuple[float, float, int, int]:
    viability = result.get("animation_viability", {})
    economy = viability.get("summary", {}).get("motion_economy", {})
    style_bonus = 0.02 if result.get("style") == "sfc" else 0.0
    return (
        float(result.get("score", 0.0)) + style_bonus,
        float(viability.get("score", 0.0)),
        1 if result.get("style") == "sfc" else 0,
        int(economy.get("source_frame_count", 0) or 0),
    )


if __name__ == "__main__":
    main()
