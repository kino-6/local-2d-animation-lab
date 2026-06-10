from __future__ import annotations

import argparse
import json
from pathlib import Path

from natural_sprite_lab.action_catalog import DEFAULT_ASSET_RECIPES
from natural_sprite_lab.backends import RiggedSpriteBackend
from natural_sprite_lab.pipeline import run_pipeline
from natural_sprite_lab.planning import WalkCycleDirector


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate practical rigged 2D animation baseline assets.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_rigged_pdca"), type=Path)
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--height", default=512, type=int)
    args = parser.parse_args()

    results = []
    backend = RiggedSpriteBackend(width=args.width, height=args.height)
    director = WalkCycleDirector(use_ollama=False)
    for recipe in DEFAULT_ASSET_RECIPES:
        outputs = run_pipeline(
            source_image=args.input,
            prompt=recipe.prompt,
            backend=backend,
            output_root=args.output_root,
            run_id=f"{recipe.name}_rigged",
            director=director,
        )
        evaluation = json.loads((outputs.run_dir / "evaluation_report.json").read_text(encoding="utf-8"))
        result = {
            "asset": recipe.name,
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
        print(f"{recipe.name}: score={result['score']} viability={viability} {result['contact_sheet']}")

    summary = {
        "best_by_asset": {result["asset"]: result for result in results},
        "results": results,
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_root / "rigged_asset_pdca_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
