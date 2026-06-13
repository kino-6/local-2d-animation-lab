from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from natural_sprite_lab.action_catalog import DEFAULT_ASSET_RECIPES
from natural_sprite_lab.backends import ComfyBackend
from natural_sprite_lab.pipeline import run_pipeline
from natural_sprite_lab.planning import WalkCycleDirector
from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, normalize_name, write_run_profile


@dataclass(frozen=True)
class ControlNetRetake:
    name: str
    seed: int
    steps: int
    cfg: float
    controlnet_strength: float
    note: str


RETAKES = (
    ControlNetRetake("baseline", 130018, 24, 6.0, 0.75, "novaOrangeXL baseline with stable seed"),
    ControlNetRetake("strong_pose", 130018, 24, 6.0, 0.90, "increase OpenPose adherence when action readability is weak"),
    ControlNetRetake("identity_lock", 130018, 28, 5.5, 0.80, "lower CFG and add steps for identity stability"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run novaOrangeXL + OpenPose ControlNet PDCA for sprite assets.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--action", default="attack_sword")
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--pose-template-root", default=Path("pose_templates"), type=Path)
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--checkpoint", default="novaOrangeXL_v120.safetensors")
    parser.add_argument("--controlnet", default="SDXL\\OpenPoseXL2.safetensors")
    parser.add_argument("--frame-count", default=120, type=int)
    parser.add_argument("--width", default=768, type=int)
    parser.add_argument("--height", default=768, type=int)
    parser.add_argument("--retakes", default=3, type=int)
    args = parser.parse_args()

    session_dir = build_timestamped_run_dir(args.output_root, "controlnet_pdca", args.action)
    write_run_profile(session_dir, category="controlnet_pdca", label=args.action, args=args)
    recipe = _recipe(args.action, args.frame_count)
    director = WalkCycleDirector(use_ollama=False)
    results = []
    for retake_index, retake in enumerate(RETAKES[: args.retakes], start=1):
        character_id = normalize_name(args.input.stem)
        run_dir = session_dir / character_id / _action_group(args.action) / f"{args.action}_{retake.name}"
        if (run_dir / "evaluation_report.json").exists() and (run_dir / "manifest.json").exists():
            outputs = _existing_outputs(run_dir)
        else:
            backend = ComfyBackend(
                server_url=args.comfy_url,
                checkpoint=args.checkpoint,
                width=args.width,
                height=args.height,
                steps=retake.steps,
                cfg=retake.cfg,
                seed=retake.seed,
                seed_step=0,
                controlnet=args.controlnet,
                controlnet_strength=retake.controlnet_strength,
                pose_template_root=args.pose_template_root,
                timeout_seconds=300.0,
            )
            outputs = run_pipeline(
                source_image=args.input,
                prompt=recipe,
                backend=backend,
                output_root=session_dir,
                retake=retake_index,
                run_id=f"{args.action}_{retake.name}",
                director=director,
            )
        side_by_side = _side_by_side(outputs.run_dir)
        evaluation = json.loads((outputs.run_dir / "evaluation_report.json").read_text(encoding="utf-8"))
        result = {
            "action": args.action,
            "retake": retake.name,
            "retake_config": asdict(retake),
            "score": evaluation["score"],
            "issues": evaluation["issues"],
            "issue_codes": _issue_codes(evaluation),
            "retake_advice": _retake_advice(evaluation),
            "quality_gate": _quality_gate(args.action, evaluation),
            "run_dir": str(outputs.run_dir),
            "manifest": str(outputs.manifest_path),
            "contact_sheet": str(outputs.composited_contact_sheet_path or outputs.contact_sheet_path),
            "preview_gif": str(outputs.gif_path),
            "side_by_side": str(side_by_side) if side_by_side else None,
        }
        results.append(result)
        print(f"{args.action}/{retake.name}: score={result['score']} issues={result['issue_codes']}")

    adopted = _select_adopted(results)
    rejected = [item for item in results if item is not adopted]
    pdca_log = {
        "rule": "novaOrangeXL + ControlNet(OpenPose) is the main path. Rig generation is not used.",
        "action": args.action,
        "frame_count": args.frame_count,
        "checkpoint": args.checkpoint,
        "controlnet": args.controlnet,
        "pose_template_root": str(args.pose_template_root),
        "adopted": adopted,
        "rejected": [
            {
                **item,
                "rejection_reason": item["retake_advice"] or "lower score than adopted candidate",
            }
            for item in rejected
        ],
        "results": results,
    }
    session_dir.mkdir(parents=True, exist_ok=True)
    log_path = session_dir / f"{args.action}_pdca_log.json"
    log_path.write_text(json.dumps(pdca_log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {"best_by_asset": {args.action: adopted}, "results": results, "pdca_log": str(log_path)}
    summary_path = session_dir / f"{args.action}_controlnet_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PDCA log: {log_path}")
    print(f"Summary: {summary_path}")


def _recipe(action: str, frame_count: int) -> str:
    for recipe in DEFAULT_ASSET_RECIPES:
        if recipe.name == action:
            return recipe.prompt.replace("120-frame", f"{frame_count}-frame")
    raise ValueError(f"Unknown action: {action}")


def _action_group(action: str) -> str:
    if action.startswith("attack_"):
        return "attack"
    if action.startswith("hit_"):
        return "hit"
    return action


def _select_adopted(results: list[dict[str, Any]]) -> dict[str, Any]:
    metric_best = max(results, key=lambda item: (float(item["score"]), -len(item["issue_codes"])))
    metric_codes = set(metric_best.get("issue_codes", []))
    visually_safer = [
        item
        for item in results
        if set(item.get("issue_codes", [])) == metric_codes and float(metric_best["score"]) - float(item["score"]) <= 0.10
    ]
    if visually_safer:
        # Later retakes are intentional PDCA responses to earlier visual failures; prefer them when metrics are close.
        return visually_safer[-1]
    return metric_best


def _existing_outputs(run_dir: Path) -> Any:
    from natural_sprite_lab.models import PipelineOutputs

    frames = sorted((run_dir / "frames").glob("*.png"))
    effects = sorted((run_dir / "effects").glob("*.png"))
    composites = sorted((run_dir / "frames_with_effects").glob("*.png"))
    return PipelineOutputs(
        run_dir=run_dir,
        frames_dir=run_dir / "frames",
        frame_paths=frames,
        spec_path=run_dir / "animation_spec.json",
        manifest_path=run_dir / "manifest.json",
        sprite_sheet_path=run_dir / "spritesheet.png",
        gif_path=run_dir / "preview.gif",
        contact_sheet_path=run_dir / "contact_sheet.png",
        effect_frame_paths=effects,
        effect_contact_sheet_path=run_dir / "effect_contact_sheet.png",
        composited_frame_paths=composites,
        composited_contact_sheet_path=run_dir / "contact_sheet_with_effects.png",
    )


def _issue_codes(evaluation: dict[str, Any]) -> list[str]:
    if evaluation.get("issue_codes"):
        return sorted(str(code) for code in evaluation["issue_codes"])

    text = " ".join(str(issue).lower() for issue in evaluation.get("issues", []))
    codes = []
    if "multi-character" in text or "fragmented" in text:
        codes.append("foreground_fragmentation")
    if "center drifts" in text:
        codes.append("center_drift")
    if "scale changes" in text or "height is unstable" in text:
        codes.append("scale_drift")
    if "colors are inconsistent" in text:
        codes.append("color_drift")
    if "motion" in text and "weak" in text:
        codes.append("weak_motion")
    if "loop closure" in text:
        codes.append("weak_loop_closure")
    if "semantic" in text or "cue" in text:
        codes.append("action_readability")
    return codes


def _retake_advice(evaluation: dict[str, Any]) -> str:
    codes = _issue_codes(evaluation)
    if "pose_action_mismatch" in codes:
        return "Check pose_template_name and action prompt variant before retake."
    if "action_readability" in codes or "weak_motion" in codes or "weak_attack_motion" in codes:
        return "Revise the OpenPose template before changing prompt settings."
    if "weak_hit_recoil" in codes:
        return "Increase recoil displacement and hold impact frames in the hit template."
    if "bow_string_arrow_breakage_likely" in codes or "bow_phase_missing" in codes:
        return "Add bow-specific control guidance or a line-art/reference layer for bow, string, and arrow."
    if "foreground_fragmentation" in codes or "multiple_or_fragmented_foreground" in codes:
        return "Strengthen negative prompt against extra characters and background clutter."
    if "background_contamination" in codes:
        return "Strengthen transparent/plain background constraints."
    if "center_drift" in codes or "scale_drift" in codes:
        return "Lock seed and framing; reduce stochastic variation before retake."
    if "color_drift" in codes:
        return "Strengthen identity prompt and reference guidance."
    return ""


def _quality_gate(action: str, evaluation: dict[str, Any]) -> dict[str, Any]:
    codes = set(_issue_codes(evaluation))
    blocking = codes & {
        "missing_or_tiny_foreground",
        "multiple_or_fragmented_foreground",
        "foreground_fragmentation",
        "pose_action_mismatch",
        "weak_attack_motion",
        "weak_hit_recoil",
        "bow_string_arrow_breakage_likely",
        "bow_phase_missing",
        "weak_loop_closure",
    }
    if action == "attack_bow":
        blocking.add("manual_bow_weapon_review_required")
    return {
        "status": "adoptable" if not blocking else "needs_retake_or_manual_review",
        "blocking_issue_codes": sorted(blocking),
        "note": "Score alone is not an adoption signal; inspect side-by-side sheet and Godot playback.",
    }


def _side_by_side(run_dir: Path) -> Path | None:
    pose_dir = run_dir / "controlnet_pose"
    frame_dir = run_dir / "frames"
    if not pose_dir.exists() or not frame_dir.exists():
        return None
    pose_paths = sorted(pose_dir.glob("*.png"))
    frame_paths = sorted(frame_dir.glob("*.png"))
    if not pose_paths or not frame_paths:
        return None
    count = min(len(pose_paths), len(frame_paths), 24)
    combined_paths = []
    out_dir = run_dir / "pose_vs_generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        pose = Image.open(pose_paths[index]).convert("RGBA").resize((256, 256))
        frame = Image.open(frame_paths[index]).convert("RGBA").resize((256, 256))
        combined = Image.new("RGBA", (512, 256), (255, 255, 255, 0))
        combined.alpha_composite(pose, (0, 0))
        combined.alpha_composite(frame, (256, 0))
        path = out_dir / f"frame_{index:03d}.png"
        combined.save(path)
        combined_paths.append(path)
    return make_contact_sheet(combined_paths, run_dir / "pose_vs_generated_contact_sheet.png")


if __name__ == "__main__":
    main()
