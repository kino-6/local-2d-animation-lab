from __future__ import annotations

import argparse
import json
from pathlib import Path

from natural_sprite_lab.backends import ComfyBackend
from natural_sprite_lab.pipeline import run_pipeline
from natural_sprite_lab.planning import WalkCycleDirector
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local PDCA sweep for reference walk-cycle generation.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--checkpoint", default="novaOrangeXL_v120.safetensors")
    parser.add_argument("--checkpoint-sweep", action="store_true", help="Try all locally known anime checkpoints.")
    parser.add_argument("--controlnet", default="SDXL\\OpenPoseXL2.safetensors")
    parser.add_argument("--seed", default=130018, type=int)
    parser.add_argument("--width", default=768, type=int)
    parser.add_argument("--height", default=768, type=int)
    args = parser.parse_args()

    session_dir = build_timestamped_run_dir(args.output_root, "walk_cycle_pdca", "walk_cycle")
    write_run_profile(session_dir, category="walk_cycle_pdca", label="walk_cycle", args=args)
    checkpoints = [args.checkpoint]
    if args.checkpoint_sweep:
        checkpoints = [
            "illustriousPencilXL_v320.safetensors",
            "noobaiXLNAIXL_epsilonPred11Version.safetensors",
            "novaOrangeXL_v120.safetensors",
            "plantMilkModelSuite_walnut.safetensors",
            "ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
        ]
    configs = [
        {"name": "balanced", "steps": 24, "cfg": 6.0, "controlnet_strength": 0.75, "seed_step": 0},
        {"name": "strong_pose", "steps": 24, "cfg": 6.0, "controlnet_strength": 0.9, "seed_step": 0},
        {"name": "slight_variation", "steps": 24, "cfg": 6.0, "controlnet_strength": 0.75, "seed_step": 1},
    ]
    results = []
    for checkpoint in checkpoints:
        for config in configs:
            run_name = f"{Path(checkpoint).stem}_{config['name']}" if args.checkpoint_sweep else config["name"]
            backend = ComfyBackend(
                checkpoint=checkpoint,
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
                prompt=args.prompt,
                backend=backend,
                output_root=session_dir,
                run_id=run_name,
                director=WalkCycleDirector(use_ollama=False),
            )
            evaluation_path = outputs.run_dir / "evaluation_report.json"
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
            results.append(
                {
                    "name": config["name"],
                    "checkpoint": checkpoint,
                    "score": evaluation["score"],
                    "issues": evaluation["issues"],
                    "run_dir": str(outputs.run_dir),
                    "contact_sheet": str(outputs.contact_sheet_path),
                    "config": {**config, "checkpoint": checkpoint},
                }
            )

    best = max(results, key=lambda result: result["score"])
    summary = {"best": best, "results": results}
    session_dir.mkdir(parents=True, exist_ok=True)
    summary_path = session_dir / "pdca_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PDCA summary: {summary_path}")
    print(f"Best: {best['name']} score={best['score']} contact_sheet={best['contact_sheet']}")


if __name__ == "__main__":
    main()
