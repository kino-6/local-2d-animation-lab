from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from natural_sprite_lab.backends.base import AnimationBackend
from natural_sprite_lab.evaluation import evaluate_animation
from natural_sprite_lab.models import OutputFormat, PipelineOutputs
from natural_sprite_lab.nl_parser import parse_prompt
from natural_sprite_lab.planning import WalkCycleDirector
from natural_sprite_lab.postprocess.action_effects import make_action_effect_layers
from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
from natural_sprite_lab.utils.io import write_json
from natural_sprite_lab.utils.paths import build_run_dir, make_run_id


def run_pipeline(
    source_image: Path,
    prompt: str,
    backend: AnimationBackend,
    output_root: Path = Path("outputs"),
    retake: int = 1,
    run_id: str | None = None,
    director: WalkCycleDirector | None = None,
) -> PipelineOutputs:
    source_image = source_image.expanduser().resolve()
    if not source_image.exists():
        raise FileNotFoundError(f"Input image does not exist: {source_image}")

    spec = parse_prompt(prompt, source_image)
    if director:
        spec = director.plan(source_image, prompt, spec)
    run_id = run_id or make_run_id(retake)
    run_dir = build_run_dir(output_root, spec.character_id, spec.action.value, run_id)
    frames_dir = run_dir / "frames"

    spec_path = write_json(run_dir / "animation_spec.json", spec.to_dict())
    generated = backend.generate_frames(source_image, spec, frames_dir, retake=retake)
    effect_frame_paths, composited_frame_paths = make_action_effect_layers(
        generated.frame_paths,
        spec.frame_plan,
        spec.action,
        run_dir / "effects",
        run_dir / "frames_with_effects",
    )

    sprite_sheet_path = None
    gif_path = None
    contact_sheet_path = None
    effect_contact_sheet_path = None
    composited_contact_sheet_path = None

    if OutputFormat.SPRITE_SHEET in spec.output_formats:
        sprite_sheet_path = make_sprite_sheet(generated.frame_paths, run_dir / "spritesheet.png")
    if OutputFormat.GIF_PREVIEW in spec.output_formats:
        gif_path = make_preview_gif(generated.frame_paths, run_dir / "preview.gif", loop=spec.loop)
    if OutputFormat.CONTACT_SHEET in spec.output_formats:
        contact_sheet_path = make_contact_sheet(generated.frame_paths, run_dir / "contact_sheet.png")
        if effect_frame_paths:
            effect_contact_sheet_path = make_contact_sheet(effect_frame_paths, run_dir / "effect_contact_sheet.png")
        if composited_frame_paths:
            composited_contact_sheet_path = make_contact_sheet(
                composited_frame_paths,
                run_dir / "contact_sheet_with_effects.png",
            )

    evaluation = evaluate_animation(generated.frame_paths)
    evaluation_path = write_json(run_dir / "evaluation_report.json", evaluation)

    outputs = PipelineOutputs(
        run_dir=run_dir,
        frames_dir=frames_dir,
        frame_paths=generated.frame_paths,
        spec_path=spec_path,
        manifest_path=run_dir / "manifest.json",
        sprite_sheet_path=sprite_sheet_path,
        gif_path=gif_path,
        contact_sheet_path=contact_sheet_path,
        effect_frame_paths=effect_frame_paths,
        effect_contact_sheet_path=effect_contact_sheet_path,
        composited_frame_paths=composited_frame_paths,
        composited_contact_sheet_path=composited_contact_sheet_path,
    )
    manifest_path = write_json(outputs.manifest_path, _manifest(source_image, prompt, spec, generated, outputs, evaluation_path, evaluation))

    return PipelineOutputs(
        run_dir=outputs.run_dir,
        frames_dir=outputs.frames_dir,
        frame_paths=outputs.frame_paths,
        spec_path=outputs.spec_path,
        manifest_path=manifest_path,
        sprite_sheet_path=outputs.sprite_sheet_path,
        gif_path=outputs.gif_path,
        contact_sheet_path=outputs.contact_sheet_path,
        effect_frame_paths=outputs.effect_frame_paths,
        effect_contact_sheet_path=outputs.effect_contact_sheet_path,
        composited_frame_paths=outputs.composited_frame_paths,
        composited_contact_sheet_path=outputs.composited_contact_sheet_path,
    )


def _manifest(
    source_image: Path,
    prompt: str,
    spec: Any,
    generated: Any,
    outputs: PipelineOutputs,
    evaluation_path: Path,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_image": str(source_image),
        "prompt": prompt,
        "spec": spec.to_dict(),
        "backend": {
            "name": generated.backend_name,
            "metadata": generated.backend_metadata,
        },
        "outputs": outputs.to_dict(),
        "evaluation": {
            "path": str(evaluation_path),
            "score": evaluation.get("score"),
            "issues": evaluation.get("issues", []),
            "summary": evaluation.get("summary", {}),
        },
        "game_engine_metadata": {
            "frame_width": None,
            "frame_height": None,
            "pivot": {"x": 0.5, "y": 1.0},
            "pixels_per_unit": 100,
        },
    }
