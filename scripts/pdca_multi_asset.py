from __future__ import annotations

import argparse
import json
from pathlib import Path

from natural_sprite_lab.backends import ComfyBackend
from natural_sprite_lab.pipeline import run_pipeline
from natural_sprite_lab.planning import WalkCycleDirector


ASSETS = [
    {
        "name": "walk",
        "prompt": "Create an 8-frame side-view walking animation, facing right. Interpret the reference as a character design and generate new full-body frames of the same character walking.",
    },
    {
        "name": "idle",
        "prompt": "Create an 8-frame calm idle breathing animation, facing right. Interpret the reference as a character design and generate new full-body frames of the same character standing naturally.",
    },
    {
        "name": "attack",
        "prompt": "Create an 8-frame quick slash attack animation, facing right. Interpret the reference as a character design. Generate one new full-body game animation frame per output image, showing the same character attacking.",
    },
    {
        "name": "hit",
        "prompt": "Create an 8-frame hit damage reaction animation, facing right. Interpret the reference as a character design. Generate one new full-body game animation frame per output image, showing the same character recoiling from a hit.",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local PDCA generation for multiple 2D character assets.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs_multi_asset_pdca"), type=Path)
    parser.add_argument("--checkpoint", default="novaOrangeXL_v120.safetensors")
    parser.add_argument("--controlnet", default="SDXL\\OpenPoseXL2.safetensors")
    parser.add_argument("--seed", default=130018, type=int)
    parser.add_argument("--width", default=768, type=int)
    parser.add_argument("--height", default=768, type=int)
    args = parser.parse_args()

    configs = [
        {"name": "balanced", "steps": 24, "cfg": 6.0, "controlnet_strength": 0.75, "seed_step": 0},
        {"name": "strong_pose", "steps": 24, "cfg": 6.0, "controlnet_strength": 0.9, "seed_step": 0},
    ]
    all_results = []
    for asset in ASSETS:
        asset_results = []
        for config in configs:
            backend = ComfyBackend(
                checkpoint=args.checkpoint,
                width=args.width,
                height=args.height,
                steps=config["steps"],
                cfg=config["cfg"],
                seed=args.seed,
                seed_step=config["seed_step"],
                controlnet=args.controlnet,
                controlnet_strength=config["controlnet_strength"],
            )
            outputs = run_pipeline(
                source_image=args.input,
                prompt=asset["prompt"],
                backend=backend,
                output_root=args.output_root,
                run_id=f"{asset['name']}_{config['name']}",
                director=WalkCycleDirector(use_ollama=False),
            )
            evaluation = json.loads((outputs.run_dir / "evaluation_report.json").read_text(encoding="utf-8"))
            result = {
                "asset": asset["name"],
                "config": config,
                "score": evaluation["score"],
                "issues": evaluation["issues"],
                "run_dir": str(outputs.run_dir),
                "contact_sheet": str(outputs.contact_sheet_path),
            }
            asset_results.append(result)
            all_results.append(result)

        best = max(asset_results, key=lambda result: result["score"])
        print(f"{asset['name']}: best={best['config']['name']} score={best['score']} {best['contact_sheet']}")

    best_by_asset = {
        asset["name"]: max(
            [result for result in all_results if result["asset"] == asset["name"]],
            key=lambda result: result["score"],
        )
        for asset in ASSETS
    }
    summary = {"best_by_asset": best_by_asset, "results": all_results}
    args.output_root.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_root / "multi_asset_pdca_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
