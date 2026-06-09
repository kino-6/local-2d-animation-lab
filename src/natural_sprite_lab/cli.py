from __future__ import annotations

import argparse
from pathlib import Path

from natural_sprite_lab.backends import ComfyBackend, CutoutWalkBackend, DummyBackend
from natural_sprite_lab.pipeline import run_pipeline
from natural_sprite_lab.planning import WalkCycleDirector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="natural-sprite-lab",
        description="Generate local-first 2D sprite animation assets from one character image.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to the source character image.")
    parser.add_argument("--prompt", required=True, help="Natural-language animation instruction.")
    parser.add_argument("--output-root", default=Path("outputs"), type=Path, help="Output root directory.")
    parser.add_argument("--retake", default=1, type=int, help="Retake number for filenames and run metadata.")
    parser.add_argument(
        "--backend",
        default="dummy",
        choices=["dummy", "cutout-walk", "comfy"],
        help="Frame generation backend.",
    )
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188", help="ComfyUI server URL.")
    parser.add_argument("--comfy-checkpoint", default=None, help="ComfyUI checkpoint name.")
    parser.add_argument("--width", default=768, type=int, help="Generated frame width for ComfyUI.")
    parser.add_argument("--height", default=768, type=int, help="Generated frame height for ComfyUI.")
    parser.add_argument("--steps", default=24, type=int, help="ComfyUI sampler steps.")
    parser.add_argument("--cfg", default=6.5, type=float, help="ComfyUI CFG scale.")
    parser.add_argument("--seed", default=None, type=int, help="Base seed for generated frames.")
    parser.add_argument("--seed-step", default=1, type=int, help="Seed increment per frame for ComfyUI.")
    parser.add_argument(
        "--controlnet",
        default=None,
        help="Optional ComfyUI ControlNet name, for example SDXL\\OpenPoseXL2.safetensors.",
    )
    parser.add_argument(
        "--controlnet-strength",
        default=0.8,
        type=float,
        help="ControlNet strength for ComfyUI generation.",
    )
    parser.add_argument(
        "--director",
        default="none",
        choices=["none", "fallback", "ollama"],
        help="Optional walk-cycle planning director.",
    )
    parser.add_argument(
        "--ollama-model",
        default=None,
        help="Ollama model name for --director ollama. Defaults to OLLAMA_MODEL or llama3.2.",
    )
    parser.add_argument(
        "--director-timeout",
        default=30.0,
        type=float,
        help="Timeout in seconds for Ollama director requests.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.backend == "comfy":
        backend = ComfyBackend(
            server_url=args.comfy_url,
            checkpoint=args.comfy_checkpoint,
            width=args.width,
            height=args.height,
            steps=args.steps,
            cfg=args.cfg,
            seed=args.seed,
            seed_step=args.seed_step,
            controlnet=args.controlnet,
            controlnet_strength=args.controlnet_strength,
        )
    elif args.backend == "cutout-walk":
        backend = CutoutWalkBackend()
    else:
        backend = DummyBackend()
    director = None
    if args.director != "none":
        director = WalkCycleDirector(
            use_ollama=args.director == "ollama",
            ollama_model=args.ollama_model,
            timeout_seconds=args.director_timeout,
        )
    outputs = run_pipeline(
        source_image=args.input,
        prompt=args.prompt,
        backend=backend,
        output_root=args.output_root,
        retake=args.retake,
        director=director,
    )

    print("Generated animation assets:")
    print(f"  Run directory: {outputs.run_dir}")
    print(f"  Spec: {outputs.spec_path}")
    print(f"  Manifest: {outputs.manifest_path}")
    print(f"  Frames: {outputs.frames_dir}")
    if outputs.sprite_sheet_path:
        print(f"  Sprite sheet: {outputs.sprite_sheet_path}")
    if outputs.gif_path:
        print(f"  Preview GIF: {outputs.gif_path}")
    if outputs.contact_sheet_path:
        print(f"  Contact sheet: {outputs.contact_sheet_path}")
