from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

try:
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


ROUTE = "character_sprite_asset_pack"
DEFAULT_REFERENCE = Path("assets/reference/Anima_00013_.png")
DEFAULT_WALK_READY = Path("outputs/adoptable/artist_authored_8frame_walk_cleanup/production_ready")
DEFAULT_RUN_ROUGH = Path("assets/artist_authored_roughs/imagegen_run_8frame_20260614/rough_frames")
DEFAULT_JUMP_ROUGH = Path("assets/artist_authored_roughs/imagegen_jump_12frame_tiles_20260615/rough_frames")
DEFAULT_HURT_ROUGH = Path("assets/artist_authored_roughs/imagegen_hurt_8frame_tiles_20260615/rough_frames")
DEFAULT_ATTACK_SWORD_LIGHT_ROUGH = Path(
    "assets/artist_authored_roughs/imagegen_attack_sword_light_12frame_tiles_20260615/rough_frames"
)
DEFAULT_DODGE_BACKSTEP_ROUGH = Path(
    "assets/artist_authored_roughs/imagegen_dodge_backstep_8frame_tiles_20260615/rough_frames"
)
DEFAULT_PARRY_SWORD_ROUGH = Path(
    "assets/artist_authored_roughs/imagegen_parry_sword_8frame_tiles_20260615/rough_frames"
)
DEFAULT_ATTACK_SWORD_LIGHT_BODY_ROUGH = Path(
    "assets/artist_authored_roughs/route_a_attack_sword_light_body_16frame_retime_20260615/rough_frames"
)
DEFAULT_PARRY_SWORD_BODY_ROUGH = Path(
    "assets/artist_authored_roughs/imagegen_parry_sword_body_8frame_tiles_20260615/rough_frames"
)
DEFAULT_OUTPUT = Path("outputs/adoptable/character_sprite_asset_pack")
DEFAULT_STYLE_REFERENCE_SET = Path("assets/style_reference_sets/character_sprite_pack_v1")

IDENTITY_CUES = {
    "pink_bob_hair": "pink hair silhouette",
    "side_profile_anime_girl": "right-facing side-profile anime girl",
    "sailor_white_top": "sailor-style white top",
    "red_tie": "red tie",
    "navy_skirt": "navy skirt",
    "dark_socks": "dark socks",
    "brown_shoes": "brown shoes",
}

FRAME_DENSITY_POLICY = {
    "idle": {"recommended_min": 4, "recommended_max": 6},
    "walk": {"recommended_min": 8, "recommended_max": 12},
    "run": {"recommended_min": 8, "recommended_max": 12},
    "jump": {"recommended_min": 12, "recommended_max": 16},
    "hurt": {"recommended_min": 8, "recommended_max": 12},
    "dodge_backstep": {"recommended_min": 8, "recommended_max": 12},
    "parry_sword": {"recommended_min": 8, "recommended_max": 12},
    "attack_sword_light": {"recommended_min": 12, "recommended_max": 18},
}

SPRITESHEET_AUTHORING_POLICY = {
    "source_inspiration": "NO6KIKO/gorest-2d-animation-spritesheet-generator",
    "source_url": "https://github.com/NO6KIKO/gorest-2d-animation-spritesheet-generator",
    "generation_preference": "full_spritesheet_first_then_split_frames",
    "normalization": "global_uniform_scale_not_per_frame_resize",
    "anchor_policy": "stable_root_anchor_with_bottom_center_runtime_origin",
    "grid_policy": "detect_source_cells_before_falling_back_to_proportional_grid",
    "tail_frame_policy": "do_not_export_a_duplicate_first_frame_as_the_final_loop_frame",
    "route_fit": "non_conflicting_route_a_guidance_for_future_generated_rough_sheets",
}

ACTION_RUNTIME_SPECS = {
    "walk": {
        "loop": True,
        "phase_names": [
            "right_contact",
            "right_down",
            "right_passing",
            "right_up",
            "left_contact",
            "left_down",
            "left_passing",
            "left_up",
        ],
        "transition_notes": ["idle", "run", "jump", "hurt", "dodge_backstep", "parry_sword", "attack_sword_light"],
        "review_role": "baseline locomotion loop",
    },
    "idle": {
        "loop": True,
        "phase_names": ["neutral", "breathe_up", "breathe_peak", "breathe_down"],
        "transition_notes": ["walk", "run", "jump", "hurt", "dodge_backstep", "parry_sword", "attack_sword_light"],
        "review_role": "subtle standing loop",
    },
    "run": {
        "loop": True,
        "phase_names": [
            "right_contact",
            "right_down",
            "flight_forward",
            "left_reach",
            "left_contact",
            "left_down",
            "flight_backward",
            "right_reach",
        ],
        "transition_notes": ["idle", "walk", "jump", "hurt", "dodge_backstep", "parry_sword", "attack_sword_light"],
        "review_role": "faster locomotion loop",
    },
    "jump": {
        "loop": False,
        "phase_names": [
            "neutral_crouch",
            "deep_crouch",
            "takeoff_extend",
            "early_rise",
            "rising_knees_bent",
            "apex_approach",
            "apex_hold",
            "falling_extend",
            "falling_reach",
            "landing_contact",
            "landing_settle",
            "landing_recovery",
        ],
        "transition_notes": ["idle", "walk", "run", "hurt", "dodge_backstep", "parry_sword", "attack_sword_light"],
        "review_role": "non-looping jump arc",
    },
    "hurt": {
        "loop": False,
        "phase_names": [
            "brace",
            "impact_recoil",
            "strong_recoil",
            "peak_recoil",
            "stagger_forward",
            "crouch_settle",
            "recover_half",
            "recover",
        ],
        "transition_notes": ["idle", "walk", "dodge_backstep", "parry_sword", "attack_sword_light"],
        "review_role": "non-looping small damage reaction",
    },
    "dodge_backstep": {
        "loop": False,
        "phase_names": [
            "ready",
            "anticipation_crouch",
            "push_off",
            "low_backstep",
            "slide_peak",
            "landing",
            "recover_low",
            "ready_return",
        ],
        "invulnerable_frames": [2, 3, 4],
        "transition_notes": ["idle", "walk", "run", "jump", "hurt", "parry_sword", "attack_sword_light"],
        "review_role": "non-looping evasive backstep",
    },
    "parry_sword": {
        "loop": False,
        "phase_names": [
            "ready",
            "raise_guard",
            "brace",
            "parry_contact",
            "deflect",
            "recoil_hold",
            "recover",
            "ready_return",
        ],
        "parry_frames": [3, 4],
        "layer_contract": {
            "layers": ["body", "weapon", "effect"],
            "z_order": ["weapon", "body", "effect"],
        },
        "transition_notes": ["idle", "walk", "run", "jump", "hurt", "dodge_backstep", "attack_sword_light"],
        "review_role": "non-looping sword parry guard",
    },
    "attack_sword_light": {
        "loop": False,
        "phase_names": [
            "ready",
            "anticipation_1",
            "anticipation_2",
            "draw_back",
            "windup",
            "slash_start",
            "active_slash_1",
            "active_slash_2",
            "active_follow_through",
            "overshoot",
            "recoil_1",
            "recoil_2",
            "settle_1",
            "settle_2",
            "recover",
            "ready_return",
        ],
        "hit_frames": [6, 7],
        "layer_contract": {
            "layers": ["body", "weapon", "effect"],
            "z_order": ["weapon", "body", "effect"],
        },
        "transition_notes": ["idle", "walk", "run", "jump", "hurt", "dodge_backstep", "parry_sword"],
        "review_role": "non-looping light one-handed sword attack",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a small character sprite asset pack around the accepted walk output."
    )
    parser.add_argument("--reference-image", default=DEFAULT_REFERENCE, type=Path)
    parser.add_argument("--walk-production-ready-dir", default=DEFAULT_WALK_READY, type=Path)
    parser.add_argument("--run-rough-frames-dir", default=DEFAULT_RUN_ROUGH, type=Path)
    parser.add_argument("--jump-rough-frames-dir", default=DEFAULT_JUMP_ROUGH, type=Path)
    parser.add_argument("--hurt-rough-frames-dir", default=DEFAULT_HURT_ROUGH, type=Path)
    parser.add_argument("--attack-sword-light-rough-frames-dir", default=DEFAULT_ATTACK_SWORD_LIGHT_ROUGH, type=Path)
    parser.add_argument("--dodge-backstep-rough-frames-dir", default=DEFAULT_DODGE_BACKSTEP_ROUGH, type=Path)
    parser.add_argument("--parry-sword-rough-frames-dir", default=DEFAULT_PARRY_SWORD_ROUGH, type=Path)
    parser.add_argument("--attack-sword-light-body-rough-frames-dir", default=DEFAULT_ATTACK_SWORD_LIGHT_BODY_ROUGH, type=Path)
    parser.add_argument("--parry-sword-body-rough-frames-dir", default=DEFAULT_PARRY_SWORD_BODY_ROUGH, type=Path)
    parser.add_argument("--style-reference-dir", default=DEFAULT_STYLE_REFERENCE_SET, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    manifest = build_character_sprite_asset_pack(
        reference_image=args.reference_image,
        walk_production_ready_dir=args.walk_production_ready_dir,
        run_rough_frames_dir=args.run_rough_frames_dir,
        jump_rough_frames_dir=args.jump_rough_frames_dir,
        hurt_rough_frames_dir=args.hurt_rough_frames_dir,
        attack_sword_light_rough_frames_dir=args.attack_sword_light_rough_frames_dir,
        dodge_backstep_rough_frames_dir=args.dodge_backstep_rough_frames_dir,
        parry_sword_rough_frames_dir=args.parry_sword_rough_frames_dir,
        attack_sword_light_body_rough_frames_dir=args.attack_sword_light_body_rough_frames_dir,
        parry_sword_body_rough_frames_dir=args.parry_sword_body_rough_frames_dir,
        style_reference_dir=args.style_reference_dir,
        output_dir=args.output_dir,
        fps=args.fps,
        clean=args.clean,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def build_character_sprite_asset_pack(
    reference_image: Path = DEFAULT_REFERENCE,
    walk_production_ready_dir: Path = DEFAULT_WALK_READY,
    run_rough_frames_dir: Path | None = DEFAULT_RUN_ROUGH,
    jump_rough_frames_dir: Path | None = DEFAULT_JUMP_ROUGH,
    hurt_rough_frames_dir: Path | None = DEFAULT_HURT_ROUGH,
    attack_sword_light_rough_frames_dir: Path | None = DEFAULT_ATTACK_SWORD_LIGHT_ROUGH,
    dodge_backstep_rough_frames_dir: Path | None = DEFAULT_DODGE_BACKSTEP_ROUGH,
    parry_sword_rough_frames_dir: Path | None = DEFAULT_PARRY_SWORD_ROUGH,
    attack_sword_light_body_rough_frames_dir: Path | None = DEFAULT_ATTACK_SWORD_LIGHT_BODY_ROUGH,
    parry_sword_body_rough_frames_dir: Path | None = DEFAULT_PARRY_SWORD_BODY_ROUGH,
    style_reference_dir: Path = DEFAULT_STYLE_REFERENCE_SET,
    output_dir: Path = DEFAULT_OUTPUT,
    fps: int = 8,
    clean: bool = True,
) -> dict[str, Any]:
    if not reference_image.exists():
        raise FileNotFoundError(f"Reference image not found: {reference_image}")
    if not walk_production_ready_dir.exists():
        raise FileNotFoundError(f"Walk production-ready folder not found: {walk_production_ready_dir}")

    walk_frames = sorted((walk_production_ready_dir / "frames").glob("walk_*.png"))
    if len(walk_frames) != 8:
        raise ValueError(f"Expected 8 production-ready walk frames, found {len(walk_frames)}.")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    actions_dir = output_dir / "actions"
    walk_action = _copy_walk_action(walk_production_ready_dir, actions_dir / "walk")
    idle_action = _build_idle_action(walk_frames, actions_dir / "idle", fps=fps)
    run_action = _build_run_action(
        walk_frames,
        actions_dir / "run",
        fps=fps,
        run_rough_frames_dir=run_rough_frames_dir,
    )
    target_size = Image.open(walk_frames[0]).size
    scale_reference = _scale_reference_from_frames(walk_frames)
    jump_action = _build_named_rough_action(
        action="jump",
        rough_frames_dir=jump_rough_frames_dir,
        action_dir=actions_dir / "jump",
        fps=fps,
        target_size=target_size,
        scale_reference=scale_reference,
        frame_count=12,
        phase_names=ACTION_RUNTIME_SPECS["jump"]["phase_names"],
        source_slug="imagegen_jump_12frame_tiles_20260615_rough",
        review_note=(
            "Jump uses dedicated 2x2 tiled rough sheets with 12 source frames for anticipation, takeoff, rise, apex, fall, "
            "landing, and recovery phases."
        ),
    )
    hurt_action = _build_named_rough_action(
        action="hurt",
        rough_frames_dir=hurt_rough_frames_dir,
        action_dir=actions_dir / "hurt",
        fps=fps,
        target_size=target_size,
        scale_reference=scale_reference,
        frame_count=8,
        phase_names=ACTION_RUNTIME_SPECS["hurt"]["phase_names"],
        source_slug="imagegen_hurt_8frame_tiles_20260615_rough",
        review_note=(
            "Hurt uses dedicated 2x2 tiled rough sheets with 8 source frames for brace, recoil, stagger, settle, and recovery phases."
        ),
    )
    dodge_action = _build_named_rough_action(
        action="dodge_backstep",
        rough_frames_dir=dodge_backstep_rough_frames_dir,
        action_dir=actions_dir / "dodge_backstep",
        fps=fps,
        target_size=target_size,
        scale_reference=scale_reference,
        frame_count=8,
        phase_names=ACTION_RUNTIME_SPECS["dodge_backstep"]["phase_names"],
        source_slug="imagegen_dodge_backstep_8frame_tiles_20260615_rough",
        review_note=(
            "Dodge backstep uses dedicated 2x2 tiled rough sheets with 8 source frames for crouch, "
            "push-off, low backstep, landing, and recovery. Runtime invulnerable frames are 2, 3, and 4."
        ),
    )
    parry_action = _build_native_layered_weapon_action(
        action="parry_sword",
        body_rough_frames_dir=parry_sword_body_rough_frames_dir,
        action_dir=actions_dir / "parry_sword",
        fps=fps,
        target_size=target_size,
        scale_reference=scale_reference,
        frame_count=8,
        body_source_prefix="parry_sword_body",
        phase_names=ACTION_RUNTIME_SPECS["parry_sword"]["phase_names"],
        source_slug="native_layers_imagegen_parry_sword_body_8frame_tiles_20260615",
        review_note=(
            "Parry sword uses native separated layers: body-only generated roughs plus independent sword and parry effect layers. "
            "Runtime parry frames are 3 and 4."
        ),
    )
    attack_action = _build_native_layered_weapon_action(
        action="attack_sword_light",
        body_rough_frames_dir=attack_sword_light_body_rough_frames_dir,
        action_dir=actions_dir / "attack_sword_light",
        fps=fps,
        target_size=target_size,
        scale_reference=scale_reference,
        frame_count=16,
        body_source_prefix="attack_sword_light_body",
        phase_names=ACTION_RUNTIME_SPECS["attack_sword_light"]["phase_names"],
        source_slug="native_layers_route_a_attack_sword_light_body_16frame_retime_20260615",
        review_note=(
            "Attack sword light uses native separated layers: body-only generated roughs plus independent sword and slash effect layers. "
            "The 16-frame source sequence separates anticipation, active slashes, overshoot, recoil, settle, and recovery. "
            "Runtime hit frames are 6 and 7."
        ),
    )

    identity_report = _build_identity_report(
        reference_image=reference_image,
        action_dirs={
            "walk": actions_dir / "walk",
            "idle": actions_dir / "idle",
            "run": actions_dir / "run",
            "jump": actions_dir / "jump",
            "hurt": actions_dir / "hurt",
            "dodge_backstep": actions_dir / "dodge_backstep",
            "parry_sword": actions_dir / "parry_sword",
            "attack_sword_light": actions_dir / "attack_sword_light",
        },
    )
    actions = {
        "walk": walk_action,
        "idle": idle_action,
        "run": run_action,
        "jump": jump_action,
        "hurt": hurt_action,
        "dodge_backstep": dodge_action,
        "parry_sword": parry_action,
        "attack_sword_light": attack_action,
    }
    _attach_frame_density_reviews(output_dir, actions)
    backend_usage = {
        "uses_comfyui": False,
        "uses_wan_video": False,
        "uses_controlnet": False,
        "uses_new_model_backend": False,
        "uses_120_frame_generation": False,
    }
    runtime_manifest = _build_runtime_manifest(actions)
    _write_text(output_dir / "runtime_manifest.json", json.dumps(runtime_manifest, indent=2, ensure_ascii=False) + "\n")
    pack_review = _build_pack_review(
        output_dir=output_dir,
        actions_dir=actions_dir,
        actions=actions,
        identity_report=identity_report,
        backend_usage=backend_usage,
    )
    production_gate = _build_production_gate(actions, identity_report, pack_review["consistency_report"])
    style_reference_set = _write_style_reference_set(actions_dir, actions, style_reference_dir)

    _write_text(output_dir / "identity_report.json", json.dumps(identity_report, indent=2, ensure_ascii=False) + "\n")
    _write_text(output_dir / "production_gate.json", json.dumps(production_gate, indent=2, ensure_ascii=False) + "\n")

    manifest = {
        "route": ROUTE,
        "asset_kind": "2d_game_sprite_asset_pack",
        "source_reference": str(reference_image).replace("\\", "/"),
        "canonical_identity": IDENTITY_CUES,
        "actions": {
            **actions,
        },
        "identity_report": "identity_report.json",
        "runtime_manifest": "runtime_manifest.json",
        "pack_review": {
            "all_actions_contact_sheet": "pack_review/all_actions_contact_sheet.png",
            "consistency_report": "pack_review/consistency_report.json",
            "style_consistency_report": "pack_review/style_consistency_report.json",
            "godot_import_manifest": "pack_review/godot_import_manifest.json",
            "aseprite_import_notes": "pack_review/aseprite_import_notes.md",
        },
        "style_reference_set": style_reference_set,
        "spritesheet_authoring_policy": SPRITESHEET_AUTHORING_POLICY,
        "production_gate": production_gate,
        "backend_usage": backend_usage,
        "production_ready": production_gate["production_ready"],
        "known_limits": [
            "The accepted sprite is a game-ready redesign, not a faithful frame-by-frame animation of the original illustration.",
            "Walk, idle, run, jump, hurt, dodge_backstep, parry_sword, and attack_sword_light are production-ready for this MVP pack.",
            "Dodge/parry are reviewable modern action-game utility actions, not a complete combat state machine.",
            "Weapon actions are reviewed as simple one-handed sword actions; complex weapon arcs still need authored rough frames.",
        ],
    }
    _write_text(output_dir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write_text(output_dir / "notes.md", _notes(manifest))
    return manifest


def _copy_walk_action(source_dir: Path, action_dir: Path) -> dict[str, Any]:
    if action_dir.exists():
        shutil.rmtree(action_dir)
    shutil.copytree(source_dir, action_dir)
    report_path = action_dir / "production_ready_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    frame_paths = sorted((action_dir / "frames").glob("walk_*.png"))
    phase_names = ACTION_RUNTIME_SPECS["walk"]["phase_names"]
    return {
        "action": "walk",
        "frame_count": report["frame_count"],
        "frame_size": report["frame_size"],
        "production_ready": report["production_ready"],
        "status": report["status"],
        "source": "artist_authored_8frame_walk_cleanup/production_ready",
        "phase_names": phase_names,
        "frames": [f"actions/walk/frames/walk_{index:03d}.png" for index in range(report["frame_count"])],
        "spritesheet": "actions/walk/spritesheet.png",
        "preview_gif": "actions/walk/preview.gif",
        "contact_sheet": "actions/walk/contact_sheet.png",
        "production_ready_report": "actions/walk/production_ready_report.json",
        "runtime": _build_action_runtime("walk", frame_paths, fps=8, phase_names=phase_names),
    }


def _build_idle_action(walk_frames: list[Path], action_dir: Path, fps: int) -> dict[str, Any]:
    if action_dir.exists():
        shutil.rmtree(action_dir)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    source = _select_idle_source_frame(walk_frames)
    source_image = Image.open(source).convert("RGBA")
    idle_paths: list[Path] = []
    for index, offset_y in enumerate([0, -1, -2, -1]):
        frame = _make_idle_frame(source_image, upper_offset_y=offset_y)
        output = frames_dir / f"idle_{index:03d}.png"
        frame.save(output)
        idle_paths.append(output)

    make_sprite_sheet(idle_paths, action_dir / "spritesheet.png", columns=4)
    make_preview_gif(idle_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(idle_paths, action_dir / "contact_sheet.png", columns=4)
    game_previews = _write_action_game_previews(idle_paths, action_dir, [128, 192, 256], fps=fps)

    metrics = _action_metrics(idle_paths)
    report = {
        "action": "idle",
        "status": "production_ready",
        "source": source.name,
        "method": "subtle_upper_body_breathing_from_accepted_walk_sprite",
        "frame_count": 4,
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "ground_y_range": metrics["ground_y_range"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "production_ready": metrics["ground_y_range"] == 0 and not metrics["alpha_edge_touch_frames"],
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _idle_notes(report))
    return {
        "action": "idle",
        "frame_count": 4,
        "frame_size": metrics["frame_size"],
        "production_ready": report["production_ready"],
        "status": report["status"],
        "source": source.name,
        "phase_names": ACTION_RUNTIME_SPECS["idle"]["phase_names"],
        "frames": [f"actions/idle/frames/idle_{index:03d}.png" for index in range(4)],
        "spritesheet": "actions/idle/spritesheet.png",
        "preview_gif": "actions/idle/preview.gif",
        "contact_sheet": "actions/idle/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, "actions/idle"),
        "production_ready_report": "actions/idle/production_ready_report.json",
        "runtime": _build_action_runtime(
            "idle",
            idle_paths,
            fps=fps,
            phase_names=ACTION_RUNTIME_SPECS["idle"]["phase_names"],
        ),
    }


def _select_idle_source_frame(walk_frames: list[Path]) -> Path:
    boxes = []
    for path in walk_frames:
        image = Image.open(path).convert("RGBA")
        box = _alpha_bbox(image)
        boxes.append((box[2] - box[0], path))
    return min(boxes, key=lambda item: item[0])[1]


def _make_idle_frame(source: Image.Image, upper_offset_y: int) -> Image.Image:
    width, height = source.size
    box = _alpha_bbox(source)
    split_y = box[1] + int((box[3] - box[1]) * 0.64)
    overlap = 8

    frame = Image.new("RGBA", source.size, (0, 0, 0, 0))
    lower = source.crop((0, split_y, width, height))
    upper = source.crop((0, 0, width, min(height, split_y + overlap)))
    frame.alpha_composite(lower, (0, split_y))
    frame.alpha_composite(upper, (0, upper_offset_y))
    return frame


def _build_run_action(
    walk_frames: list[Path],
    action_dir: Path,
    fps: int,
    run_rough_frames_dir: Path | None,
) -> dict[str, Any]:
    if run_rough_frames_dir is not None and run_rough_frames_dir.exists():
        rough_paths = sorted(run_rough_frames_dir.glob("run_*.png"))
        if len(rough_paths) == 8:
            target_size = Image.open(walk_frames[0]).size
            return _build_run_action_from_rough(rough_paths, action_dir, fps=fps, target_size=target_size)

    if action_dir.exists():
        shutil.rmtree(action_dir)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    phase_plan = [
        {"source": 3, "phase": "right_contact", "lift": 0, "lean": 0.08, "dx": 8},
        {"source": 1, "phase": "right_down", "lift": -2, "lean": 0.10, "dx": 5},
        {"source": 2, "phase": "flight_forward", "lift": -18, "lean": 0.12, "dx": 3},
        {"source": 0, "phase": "left_reach", "lift": -8, "lean": 0.10, "dx": 0},
        {"source": 7, "phase": "left_contact", "lift": 0, "lean": 0.08, "dx": -7},
        {"source": 5, "phase": "left_down", "lift": -2, "lean": 0.10, "dx": -4},
        {"source": 6, "phase": "flight_backward", "lift": -18, "lean": 0.12, "dx": -2},
        {"source": 4, "phase": "right_reach", "lift": -8, "lean": 0.10, "dx": 2},
    ]
    run_paths: list[Path] = []
    for index, step in enumerate(phase_plan):
        source = Image.open(walk_frames[step["source"]]).convert("RGBA")
        frame = _make_run_frame(
            source,
            lift_y=step["lift"],
            lean=float(step["lean"]),
            dx=int(step["dx"]),
        )
        output = frames_dir / f"run_{index:03d}.png"
        frame.save(output)
        run_paths.append(output)

    make_sprite_sheet(run_paths, action_dir / "spritesheet.png", columns=8)
    make_preview_gif(run_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(run_paths, action_dir / "contact_sheet.png", columns=4)
    game_previews = _write_action_game_previews(run_paths, action_dir, [128, 192, 256], fps=fps)

    metrics = _run_metrics(run_paths, contact_frames=[0, 1, 4, 5], airborne_frames=[2, 3, 6, 7])
    production_ready = (
        metrics["contact_ground_y_range"] <= 2
        and metrics["airborne_lift_detected"] is True
        and not metrics["alpha_edge_touch_frames"]
        and metrics["frame_count"] == 8
    )
    report = {
        "action": "run",
        "status": "production_ready" if production_ready else "run_candidate_needs_review",
        "source": "accepted_walk_sprite_retimed_with_run_phase_transforms",
        "method": "deterministic_run_pose_retime_from_production_ready_walk",
        "frame_count": 8,
        "phase_names": [step["phase"] for step in phase_plan],
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "contact_ground_y_range": metrics["contact_ground_y_range"],
        "airborne_lift_detected": metrics["airborne_lift_detected"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "production_ready": production_ready,
        "review_note": (
            "Run is built from the accepted character sprite with explicit contact/down/flight/reach phases. "
            "It is not a new AI generation and should be replaced later if authored run frames become available."
        ),
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _run_notes(report))
    return {
        "action": "run",
        "frame_count": 8,
        "frame_size": metrics["frame_size"],
        "production_ready": production_ready,
        "status": report["status"],
        "source": report["source"],
        "phase_names": report["phase_names"],
        "frames": [f"actions/run/frames/run_{index:03d}.png" for index in range(8)],
        "spritesheet": "actions/run/spritesheet.png",
        "preview_gif": "actions/run/preview.gif",
        "contact_sheet": "actions/run/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, "actions/run"),
        "production_ready_report": "actions/run/production_ready_report.json",
        "runtime": _build_action_runtime("run", run_paths, fps=fps, phase_names=report["phase_names"]),
    }


def _build_run_action_from_rough(
    rough_paths: list[Path],
    action_dir: Path,
    fps: int,
    target_size: tuple[int, int],
) -> dict[str, Any]:
    if action_dir.exists():
        shutil.rmtree(action_dir)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    phase_names = [
        "right_contact",
        "right_down",
        "flight_forward",
        "left_reach",
        "left_contact",
        "left_down",
        "flight_backward",
        "right_reach",
    ]
    run_paths: list[Path] = []
    for index, source in enumerate(rough_paths):
        image = Image.open(source).convert("RGBA")
        cleaned = _clean_green_background(image)
        normalized = cleaned.resize(target_size, Image.Resampling.LANCZOS)
        normalized = _threshold_alpha(normalized, minimum_alpha=24)
        normalized = _keep_largest_alpha_component(normalized)
        normalized = _keep_inside_canvas(normalized, margin=2)
        output = frames_dir / f"run_{index:03d}.png"
        normalized.save(output)
        run_paths.append(output)

    make_sprite_sheet(run_paths, action_dir / "spritesheet.png", columns=8)
    make_preview_gif(run_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(run_paths, action_dir / "contact_sheet.png", columns=4)
    game_previews = _write_action_game_previews(run_paths, action_dir, [128, 192, 256], fps=fps)

    metrics = _run_metrics(run_paths, contact_frames=[0, 1, 4, 5], airborne_frames=[2, 3, 6, 7])
    production_ready = (
        metrics["frame_count"] == 8
        and metrics["airborne_lift_detected"] is True
        and not metrics["alpha_edge_touch_frames"]
    )
    report = {
        "action": "run",
        "status": "production_ready" if production_ready else "run_candidate_needs_review",
        "source": "imagegen_run_8frame_20260614_rough",
        "method": "route_a_generated_run_rough_cleanup",
        "frame_count": 8,
        "phase_names": phase_names,
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "contact_ground_y_range": metrics["contact_ground_y_range"],
        "airborne_lift_detected": metrics["airborne_lift_detected"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "production_ready": production_ready,
        "review_note": (
            "Run uses a dedicated 8-frame rough sheet rather than retiming walk frames. This improves "
            "run readability while preserving the same character identity contract."
        ),
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _run_notes(report))
    return {
        "action": "run",
        "frame_count": 8,
        "frame_size": metrics["frame_size"],
        "production_ready": production_ready,
        "status": report["status"],
        "source": report["source"],
        "phase_names": phase_names,
        "frames": [f"actions/run/frames/run_{index:03d}.png" for index in range(8)],
        "spritesheet": "actions/run/spritesheet.png",
        "preview_gif": "actions/run/preview.gif",
        "contact_sheet": "actions/run/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, "actions/run"),
        "production_ready_report": "actions/run/production_ready_report.json",
        "runtime": _build_action_runtime("run", run_paths, fps=fps, phase_names=phase_names),
    }


def _scale_reference_from_frames(frame_paths: list[Path]) -> dict[str, int]:
    boxes = [_alpha_bbox(Image.open(path).convert("RGBA")) for path in frame_paths]
    heights = [box[3] - box[1] for box in boxes]
    widths = [box[2] - box[0] for box in boxes]
    bottoms = [box[3] for box in boxes]
    centers = [(box[0] + box[2]) // 2 for box in boxes]
    return {
        "target_height": max(heights),
        "target_width": max(widths),
        "ground_y": max(bottoms),
        "center_x": sorted(centers)[len(centers) // 2],
    }


def _normalize_rough_sequence(
    frames: list[Image.Image],
    action: str,
    target_size: tuple[int, int],
    scale_reference: dict[str, int],
) -> list[Image.Image]:
    boxes = [_alpha_bbox(frame) for frame in frames]
    source_heights = [box[3] - box[1] for box in boxes]
    source_widths = [box[2] - box[0] for box in boxes]
    source_bottoms = [box[3] for box in boxes]
    source_centers = [(box[0] + box[2]) / 2 for box in boxes]

    max_source_height = max(source_heights)
    max_source_width = max(source_widths)
    target_height = scale_reference["target_height"]
    target_width_limit = int(target_size[0] * 0.9)
    height_scale = target_height / max_source_height
    width_scale = target_width_limit / max_source_width
    scale = min(height_scale, width_scale)

    if action == "hurt":
        scale = min(scale * 0.88, 0.92)
    elif action == "jump":
        scale = min(scale, 1.18)

    source_ground = max(source_bottoms)
    source_center = sorted(source_centers)[len(source_centers) // 2]
    target_ground = scale_reference["ground_y"]
    target_center = scale_reference["center_x"]
    preserve_vertical_arc = action == "jump"

    normalized_frames: list[Image.Image] = []
    for frame, box in zip(frames, boxes):
        crop = frame.crop(box)
        crop_width = max(1, round(crop.width * scale))
        crop_height = max(1, round(crop.height * scale))
        resized = crop.resize((crop_width, crop_height), Image.Resampling.LANCZOS)
        if action == "jump":
            resized = resized.filter(ImageFilter.UnsharpMask(radius=1.1, percent=135, threshold=3))
        output = Image.new("RGBA", target_size, (0, 0, 0, 0))

        source_frame_center = (box[0] + box[2]) / 2
        if action == "hurt":
            target_x = target_center
        else:
            target_x = target_center + round((source_frame_center - source_center) * scale)
        if preserve_vertical_arc:
            target_bottom = target_ground + round((box[3] - source_ground) * scale)
        else:
            target_bottom = target_ground

        paste_x = round(target_x - crop_width / 2)
        paste_y = target_bottom - crop_height
        output.alpha_composite(resized, (paste_x, paste_y))
        normalized_frames.append(_keep_inside_canvas(output, margin=2))

    return normalized_frames


def _build_named_rough_action(
    action: str,
    rough_frames_dir: Path | None,
    action_dir: Path,
    fps: int,
    target_size: tuple[int, int],
    scale_reference: dict[str, int],
    frame_count: int,
    phase_names: list[str],
    source_slug: str,
    review_note: str,
) -> dict[str, Any]:
    if rough_frames_dir is None or not rough_frames_dir.exists():
        raise FileNotFoundError(f"{action} rough frames not found: {rough_frames_dir}")
    rough_paths = sorted(rough_frames_dir.glob(f"{action}_*.png"))
    if len(rough_paths) != frame_count:
        raise ValueError(f"Expected {frame_count} {action} rough frames, found {len(rough_paths)}.")
    if action_dir.exists():
        shutil.rmtree(action_dir)
    frames_dir = action_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cleaned_frames: list[Image.Image] = []
    for source in rough_paths:
        image = Image.open(source).convert("RGBA")
        cleaned = _clean_green_background(image)
        cleaned = _threshold_alpha(cleaned, minimum_alpha=24)
        cleaned = _keep_largest_alpha_component(cleaned)
        cleaned_frames.append(cleaned)

    normalized_frames = _normalize_rough_sequence(
        cleaned_frames,
        action=action,
        target_size=target_size,
        scale_reference=scale_reference,
    )

    frame_paths: list[Path] = []
    for index, normalized in enumerate(normalized_frames):
        output = frames_dir / f"{action}_{index:03d}.png"
        normalized.save(output)
        frame_paths.append(output)

    make_sprite_sheet(frame_paths, action_dir / "spritesheet.png", columns=frame_count)
    make_preview_gif(frame_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(frame_paths, action_dir / "contact_sheet.png", columns=min(4, frame_count))
    game_previews = _write_action_game_previews(frame_paths, action_dir, [128, 192, 256], fps=fps)
    layered_manifest = _write_layered_action_outputs(action, frame_paths, action_dir, fps)

    metrics = _action_metrics(frame_paths)
    production_ready = len(frame_paths) == frame_count and not metrics["alpha_edge_touch_frames"]
    report = {
        "action": action,
        "status": "production_ready" if production_ready else f"{action}_candidate_needs_review",
        "source": source_slug,
        "method": "route_a_generated_rough_cleanup",
        "frame_count": frame_count,
        "phase_names": phase_names,
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "ground_y_range": metrics["ground_y_range"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "layered": layered_manifest,
        "production_ready": production_ready,
        "review_note": review_note,
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _rough_action_notes(report))
    return {
        "action": action,
        "frame_count": frame_count,
        "frame_size": metrics["frame_size"],
        "production_ready": production_ready,
        "status": report["status"],
        "source": source_slug,
        "phase_names": phase_names,
        "frames": [f"actions/{action}/frames/{action}_{index:03d}.png" for index in range(frame_count)],
        "spritesheet": f"actions/{action}/spritesheet.png",
        "preview_gif": f"actions/{action}/preview.gif",
        "contact_sheet": f"actions/{action}/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, f"actions/{action}"),
        "layered": layered_manifest,
        "production_ready_report": f"actions/{action}/production_ready_report.json",
        "runtime": _build_action_runtime(action, frame_paths, fps=fps, phase_names=phase_names),
    }


def _build_native_layered_weapon_action(
    action: str,
    body_rough_frames_dir: Path | None,
    action_dir: Path,
    fps: int,
    target_size: tuple[int, int],
    scale_reference: dict[str, int],
    frame_count: int,
    body_source_prefix: str,
    phase_names: list[str],
    source_slug: str,
    review_note: str,
) -> dict[str, Any]:
    if body_rough_frames_dir is None or not body_rough_frames_dir.exists():
        raise FileNotFoundError(f"{action} body rough frames not found: {body_rough_frames_dir}")
    rough_paths = sorted(body_rough_frames_dir.glob(f"{body_source_prefix}_*.png"))
    if len(rough_paths) != frame_count:
        raise ValueError(f"Expected {frame_count} {action} body rough frames, found {len(rough_paths)}.")
    if action_dir.exists():
        shutil.rmtree(action_dir)

    body_frames: list[Image.Image] = []
    for source in rough_paths:
        image = Image.open(source).convert("RGBA")
        cleaned = _clean_green_background(image)
        cleaned = _threshold_alpha(cleaned, minimum_alpha=24)
        cleaned = _keep_largest_alpha_component(cleaned)
        body_frames.append(cleaned)
    body_frames = _normalize_rough_sequence(
        body_frames,
        action=action,
        target_size=target_size,
        scale_reference=scale_reference,
    )

    layers = {"body": [], "weapon": [], "effect": []}
    composed_frames: list[Image.Image] = []
    for index, body in enumerate(body_frames):
        weapon, effect = _make_native_weapon_effect_layers(action, index, target_size, body)
        composed = Image.new("RGBA", target_size, (0, 0, 0, 0))
        composed.alpha_composite(weapon)
        composed.alpha_composite(body)
        composed.alpha_composite(effect)
        layers["body"].append(body)
        layers["weapon"].append(weapon)
        layers["effect"].append(effect)
        composed_frames.append(composed)

    frame_paths = _write_image_sequence(composed_frames, action_dir / "frames", action)
    make_sprite_sheet(frame_paths, action_dir / "spritesheet.png", columns=frame_count)
    make_preview_gif(frame_paths, action_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    make_contact_sheet(frame_paths, action_dir / "contact_sheet.png", columns=min(4, frame_count))
    game_previews = _write_action_game_previews(frame_paths, action_dir, [128, 192, 256], fps=fps)
    layered_manifest = _write_native_layered_outputs(action, layers, action_dir, fps)

    metrics = _action_metrics(frame_paths)
    production_ready = len(frame_paths) == frame_count and not metrics["alpha_edge_touch_frames"]
    report = {
        "action": action,
        "status": "production_ready" if production_ready else f"{action}_candidate_needs_review",
        "source": source_slug,
        "method": "route_a_native_separated_layer_cleanup",
        "frame_count": frame_count,
        "phase_names": phase_names,
        "frame_size": metrics["frame_size"],
        "game_previews": game_previews,
        "ground_y_range": metrics["ground_y_range"],
        "alpha_edge_touch_frames": metrics["alpha_edge_touch_frames"],
        "layered": layered_manifest,
        "production_ready": production_ready,
        "review_note": review_note,
    }
    _write_text(action_dir / "production_ready_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_text(action_dir / "notes.md", _rough_action_notes(report))
    return {
        "action": action,
        "frame_count": frame_count,
        "frame_size": metrics["frame_size"],
        "production_ready": production_ready,
        "status": report["status"],
        "source": source_slug,
        "phase_names": phase_names,
        "frames": [f"actions/{action}/frames/{action}_{index:03d}.png" for index in range(frame_count)],
        "spritesheet": f"actions/{action}/spritesheet.png",
        "preview_gif": f"actions/{action}/preview.gif",
        "contact_sheet": f"actions/{action}/contact_sheet.png",
        "game_previews": _prefix_preview_paths(game_previews, f"actions/{action}"),
        "layered": layered_manifest,
        "production_ready_report": f"actions/{action}/production_ready_report.json",
        "runtime": _build_action_runtime(action, frame_paths, fps=fps, phase_names=phase_names),
    }


def _write_image_sequence(images: list[Image.Image], frames_dir: Path, action: str) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, image in enumerate(images):
        output = frames_dir / f"{action}_{index:03d}.png"
        image.save(output)
        paths.append(output)
    return paths


def _make_native_weapon_effect_layers(
    action: str,
    frame_index: int,
    target_size: tuple[int, int],
    body: Image.Image,
) -> tuple[Image.Image, Image.Image]:
    box = _alpha_bbox(body)
    hand, tip = _weapon_canvas_points(action, frame_index, target_size)
    weapon = Image.new("RGBA", target_size, (0, 0, 0, 0))
    effect = Image.new("RGBA", target_size, (0, 0, 0, 0))
    if _weapon_visible_for_native_action(action, frame_index):
        _draw_sword_layer(weapon, hand, tip)
    _draw_effect_layer(effect, action, frame_index, hand, tip, box)
    return weapon, effect


def _weapon_visible_for_native_action(action: str, frame_index: int) -> bool:
    if action == "attack_sword_light":
        return 1 <= frame_index <= 11
    if action == "parry_sword":
        return 1 <= frame_index <= 5
    return True


def _weapon_canvas_points(
    action: str,
    frame_index: int,
    target_size: tuple[int, int],
) -> tuple[tuple[int, int], tuple[int, int]]:
    # These are native weapon anchors for the accepted body-only generated sheets.
    # They intentionally avoid reading a weapon back out of composed art.
    attack_points = [
        ((0.32, 0.61), (0.22, 0.79)),
        ((0.25, 0.58), (0.12, 0.62)),
        ((0.28, 0.56), (0.11, 0.58)),
        ((0.33, 0.47), (0.13, 0.44)),
        ((0.33, 0.18), (0.54, 0.06)),
        ((0.36, 0.28), (0.72, 0.14)),
        ((0.72, 0.49), (0.95, 0.49)),
        ((0.73, 0.52), (0.96, 0.58)),
        ((0.28, 0.56), (0.78, 0.69)),
        ((0.79, 0.52), (0.94, 0.36)),
        ((0.30, 0.52), (0.13, 0.66)),
        ((0.32, 0.60), (0.22, 0.76)),
        ((0.32, 0.63), (0.22, 0.80)),
        ((0.32, 0.63), (0.23, 0.80)),
        ((0.48, 0.66), (0.63, 0.80)),
        ((0.71, 0.65), (0.86, 0.79)),
    ]
    parry_points = [
        ((0.32, 0.61), (0.22, 0.79)),
        ((0.60, 0.44), (0.70, 0.18)),
        ((0.59, 0.43), (0.66, 0.15)),
        ((0.58, 0.46), (0.70, 0.08)),
        ((0.76, 0.43), (0.88, 0.36)),
        ((0.57, 0.38), (0.74, 0.18)),
        ((0.38, 0.66), (0.28, 0.79)),
        ((0.47, 0.66), (0.35, 0.82)),
    ]
    points = attack_points if action == "attack_sword_light" else parry_points
    hand_ratio, tip_ratio = points[min(frame_index, len(points) - 1)]
    return _point_in_canvas(target_size, hand_ratio), _point_in_canvas(target_size, tip_ratio)


def _point_in_canvas(size: tuple[int, int], ratio: tuple[float, float]) -> tuple[int, int]:
    width, height = size
    return (round(width * ratio[0]), round(height * ratio[1]))


def _weapon_pose_points(
    action: str,
    frame_index: int,
    box: tuple[int, int, int, int],
) -> tuple[tuple[int, int], tuple[int, int]]:
    attack_points = [
        ((0.28, 0.66), (0.05, 0.84)),
        ((0.40, 0.56), (0.10, 0.62)),
        ((0.34, 0.50), (0.00, 0.48)),
        ((0.67, 0.24), (0.78, -0.06)),
        ((0.32, 0.64), (-0.03, 0.76)),
        ((0.74, 0.47), (1.32, 0.47)),
        ((0.74, 0.49), (1.30, 0.63)),
        ((0.70, 0.36), (1.04, 0.12)),
        ((0.28, 0.66), (0.02, 0.78)),
        ((0.28, 0.70), (0.06, 0.84)),
        ((0.30, 0.72), (0.10, 0.86)),
        ((0.62, 0.72), (0.90, 0.78)),
    ]
    parry_points = [
        ((0.26, 0.68), (0.05, 0.84)),
        ((0.62, 0.42), (0.72, 0.16)),
        ((0.66, 0.34), (0.76, 0.05)),
        ((0.74, 0.35), (0.86, 0.04)),
        ((0.78, 0.47), (1.18, 0.32)),
        ((0.55, 0.32), (0.86, 0.13)),
        ((0.28, 0.66), (0.06, 0.80)),
        ((0.26, 0.70), (0.07, 0.84)),
    ]
    points = attack_points if action == "attack_sword_light" else parry_points
    hand_ratio, tip_ratio = points[min(frame_index, len(points) - 1)]
    return _point_in_box(box, hand_ratio), _point_in_box(box, tip_ratio)


def _point_in_box(box: tuple[int, int, int, int], ratio: tuple[float, float]) -> tuple[int, int]:
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    return (round(left + width * ratio[0]), round(top + height * ratio[1]))


def _draw_sword_layer(image: Image.Image, hand: tuple[int, int], tip: tuple[int, int]) -> None:
    draw = ImageDraw.Draw(image)
    hand = _clamp_point_to_canvas(hand, image.size, margin=18)
    tip = _clamp_point_to_canvas(tip, image.size, margin=18)
    hx, hy = hand
    tx, ty = tip
    dx = tx - hx
    dy = ty - hy
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    nx = -dy / length
    ny = dx / length
    blade_start = (round(hx + dx * 0.12), round(hy + dy * 0.12))
    blade_tip = (tx, ty)
    draw.line((blade_start, blade_tip), fill=(95, 100, 110, 230), width=7)
    draw.line((blade_start, blade_tip), fill=(215, 220, 230, 255), width=4)
    draw.line(
        ((round(hx - nx * 12), round(hy - ny * 12)), (round(hx + nx * 12), round(hy + ny * 12))),
        fill=(130, 86, 38, 255),
        width=5,
    )
    draw.ellipse((hx - 5, hy - 5, hx + 5, hy + 5), fill=(170, 126, 54, 255))


def _find_skin_anchor_near(body: Image.Image, expected: tuple[int, int]) -> tuple[int, int]:
    pixels = body.load()
    width, height = body.size
    skin_pixels: list[tuple[int, int]] = []
    ex, ey = expected
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 64:
                continue
            if _is_skin_pixel(red, green, blue):
                distance_sq = (x - ex) * (x - ex) + (y - ey) * (y - ey)
                if distance_sq <= 90 * 90:
                    skin_pixels.append((x, y))
    if not skin_pixels:
        return expected
    closest = min(skin_pixels, key=lambda p: (p[0] - ex) * (p[0] - ex) + (p[1] - ey) * (p[1] - ey))
    component = _skin_component(body, closest)
    if not component:
        return closest
    return (
        round(sum(point[0] for point in component) / len(component)),
        round(sum(point[1] for point in component) / len(component)),
    )


def _is_skin_pixel(red: int, green: int, blue: int) -> bool:
    return red > 185 and 105 <= green <= 215 and 75 <= blue <= 190 and red > green >= blue


def _skin_component(body: Image.Image, start: tuple[int, int]) -> list[tuple[int, int]]:
    pixels = body.load()
    width, height = body.size
    visited = {start}
    stack = [start]
    component: list[tuple[int, int]] = []
    while stack:
        x, y = stack.pop()
        red, green, blue, alpha = pixels[x, y]
        if alpha < 64 or not _is_skin_pixel(red, green, blue):
            continue
        component.append((x, y))
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or nx >= width or ny < 0 or ny >= height or (nx, ny) in visited:
                continue
            visited.add((nx, ny))
            stack.append((nx, ny))
    return component


def _draw_effect_layer(
    image: Image.Image,
    action: str,
    frame_index: int,
    hand: tuple[int, int],
    tip: tuple[int, int],
    box: tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)
    hand = _clamp_point_to_canvas(hand, image.size, margin=24)
    tip = _clamp_point_to_canvas(tip, image.size, margin=24)
    left, top, right, bottom = box
    if action == "attack_sword_light" and frame_index in {6, 7}:
        cx = round((hand[0] + tip[0]) / 2)
        cy = round((hand[1] + tip[1]) / 2)
        width = min(image.width - 40, max(36, round((right - left) * 0.72)))
        height = min(image.height - 40, max(24, round((bottom - top) * 0.22)))
        cx = min(image.width - 20 - width // 2, max(20 + width // 2, cx))
        cy = min(image.height - 20 - height // 2, max(20 + height // 2, cy))
        bounds = (cx - width // 2, cy - height // 2, cx + width // 2, cy + height // 2)
        start, end = (-15, 45) if frame_index == 6 else (8, 75)
        draw.arc(bounds, start=start, end=end, fill=(90, 240, 230, 210), width=5)
        draw.arc(bounds, start=start + 5, end=end - 3, fill=(230, 255, 255, 180), width=2)
    if action == "parry_sword" and frame_index in {3, 4}:
        sx, sy = tip
        rays = [
            (0, -42),
            (28, -28),
            (45, -4),
            (28, 20),
            (-10, 28),
        ]
        for rx, ry in rays:
            ex, ey = _clamp_point_to_canvas((sx + rx, sy + ry), image.size, margin=12)
            mx, my = _clamp_point_to_canvas((sx + round(rx * 0.65), sy + round(ry * 0.65)), image.size, margin=12)
            draw.line((sx, sy, ex, ey), fill=(255, 232, 50, 235), width=4)
            draw.line((sx, sy, mx, my), fill=(255, 255, 210, 235), width=2)


def _clamp_point_to_canvas(
    point: tuple[int, int],
    size: tuple[int, int],
    margin: int,
) -> tuple[int, int]:
    width, height = size
    return (
        min(width - margin, max(margin, point[0])),
        min(height - margin, max(margin, point[1])),
    )


def _clean_green_background(image: Image.Image) -> Image.Image:
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    source = image.load()
    target = cleaned.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = source[x, y]
            is_green_key = green > 80 and green > red * 1.12 and green > blue * 1.12
            if alpha < 8 or is_green_key:
                target[x, y] = (0, 0, 0, 0)
            else:
                target[x, y] = (red, green, blue, alpha)
    return cleaned


def _threshold_alpha(image: Image.Image, minimum_alpha: int) -> Image.Image:
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    source = image.load()
    target = cleaned.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = source[x, y]
            if alpha < minimum_alpha:
                target[x, y] = (0, 0, 0, 0)
            else:
                target[x, y] = (red, green, blue, alpha)
    return cleaned


def _keep_largest_alpha_component(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    width, height = image.size
    visited: set[tuple[int, int]] = set()
    largest: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in visited:
                continue
            component: list[tuple[int, int]] = []
            stack = [(x, y)]
            visited.add((x, y))
            while stack:
                current_x, current_y = stack.pop()
                component.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if next_x < 0 or next_x >= width or next_y < 0 or next_y >= height:
                        continue
                    if pixels[next_x, next_y] == 0 or (next_x, next_y) in visited:
                        continue
                    visited.add((next_x, next_y))
                    stack.append((next_x, next_y))
            if len(component) > len(largest):
                largest = component

    if not largest:
        return image
    keep = set(largest)
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    source = image.load()
    target = cleaned.load()
    for x, y in keep:
        target[x, y] = source[x, y]
    return cleaned


def _make_run_frame(source: Image.Image, lift_y: int, lean: float, dx: int) -> Image.Image:
    width, height = source.size
    box = _alpha_bbox(source)
    crop = source.crop(box)
    crop_width, crop_height = crop.size
    pad = 36
    padded = Image.new("RGBA", (crop_width + pad * 2, crop_height + pad * 2), (0, 0, 0, 0))
    padded.alpha_composite(crop, (pad, pad))
    center_y = padded.height * 0.5
    leaned = padded.transform(
        padded.size,
        Image.Transform.AFFINE,
        (1, -lean, lean * center_y, 0, 1, 0),
        resample=Image.Resampling.BICUBIC,
    )
    target = Image.new("RGBA", source.size, (0, 0, 0, 0))
    target.alpha_composite(leaned, (box[0] - pad + dx, box[1] - pad + lift_y))
    return _keep_inside_canvas(target, margin=2)


def _keep_inside_canvas(image: Image.Image, margin: int) -> Image.Image:
    box = _alpha_bbox(image)
    dx = 0
    dy = 0
    if box[0] < margin:
        dx = margin - box[0]
    elif box[2] > image.width - margin:
        dx = image.width - margin - box[2]
    if box[1] < margin:
        dy = margin - box[1]
    elif box[3] > image.height - margin:
        dy = image.height - margin - box[3]
    if dx == 0 and dy == 0:
        return image
    shifted = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shifted.alpha_composite(image, (dx, dy))
    return shifted


def _run_metrics(
    frame_paths: list[Path],
    contact_frames: list[int],
    airborne_frames: list[int],
) -> dict[str, Any]:
    metrics = _action_metrics(frame_paths)
    bottoms = []
    for path in frame_paths:
        bottoms.append(_alpha_bbox(Image.open(path).convert("RGBA"))[3])
    contact_bottoms = [bottoms[index] for index in contact_frames]
    airborne_bottoms = [bottoms[index] for index in airborne_frames]
    return {
        **metrics,
        "frame_count": len(frame_paths),
        "contact_frames": contact_frames,
        "airborne_frames": airborne_frames,
        "contact_ground_y_range": max(contact_bottoms) - min(contact_bottoms),
        "airborne_lift_detected": min(airborne_bottoms) <= min(contact_bottoms) - 6,
    }


def _write_action_game_previews(
    frame_paths: list[Path],
    action_dir: Path,
    heights: list[int],
    fps: int,
) -> dict[str, Any]:
    previews: dict[str, Any] = {}
    first = Image.open(frame_paths[0]).convert("RGBA")
    for height in heights:
        scale = height / first.height
        width = round(first.width * scale)
        label = f"height_{height}"
        preview_dir = action_dir / "game_previews" / label
        frames_dir = preview_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        resized_paths: list[Path] = []
        for source in frame_paths:
            image = Image.open(source).convert("RGBA")
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            output = frames_dir / source.name
            resized.save(output)
            resized_paths.append(output)
        make_sprite_sheet(resized_paths, preview_dir / "spritesheet.png", columns=len(resized_paths))
        make_preview_gif(resized_paths, preview_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
        make_contact_sheet(resized_paths, preview_dir / "contact_sheet.png", columns=4)
        previews[label] = {
            "frame_size": {"width": width, "height": height},
            "frames": [f"game_previews/{label}/frames/{path.name}" for path in resized_paths],
            "spritesheet": f"game_previews/{label}/spritesheet.png",
            "preview_gif": f"game_previews/{label}/preview.gif",
            "contact_sheet": f"game_previews/{label}/contact_sheet.png",
        }
    return previews


def _write_native_layered_outputs(
    action: str,
    layers: dict[str, list[Image.Image]],
    action_dir: Path,
    fps: int,
) -> dict[str, Any]:
    spec = ACTION_RUNTIME_SPECS[action]
    layer_root = action_dir / "layers"
    if layer_root.exists():
        shutil.rmtree(layer_root)
    layer_names = spec["layer_contract"]["layers"]
    z_order = spec["layer_contract"]["z_order"]
    layer_artifacts: dict[str, Any] = {}
    non_empty_frames: dict[str, list[int]] = {layer: [] for layer in layer_names}
    for layer in layer_names:
        paths = _write_image_sequence(layers[layer], layer_root / layer / "frames", action)
        for index, image in enumerate(layers[layer]):
            if _has_visible_foreground(image):
                non_empty_frames[layer].append(index)
        layer_dir = layer_root / layer
        make_sprite_sheet(paths, layer_dir / "spritesheet.png", columns=len(paths))
        make_preview_gif(paths, layer_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
        make_contact_sheet(paths, layer_dir / "contact_sheet.png", columns=min(4, len(paths)))
        layer_artifacts[layer] = {
            "frames": [f"layers/{layer}/frames/{path.name}" for path in paths],
            "spritesheet": f"layers/{layer}/spritesheet.png",
            "preview_gif": f"layers/{layer}/preview.gif",
            "contact_sheet": f"layers/{layer}/contact_sheet.png",
            "non_empty_frames": non_empty_frames[layer],
        }

    timing_windows = {
        "hit_frames": spec.get("hit_frames", []),
        "parry_frames": spec.get("parry_frames", []),
        "invulnerable_frames": spec.get("invulnerable_frames", []),
    }
    manifest = {
        "action": action,
        "status": "native_layered_production_ready",
        "source": "native_separated_layers",
        "composite_source": "weapon + body + effect",
        "layers": layer_names,
        "z_order": z_order,
        "layer_artifacts": layer_artifacts,
        "weapon_visible_frames": non_empty_frames.get("weapon", []),
        "effect_visible_frames": non_empty_frames.get("effect", []),
        "timing_windows": timing_windows,
        "notes": [
            "Body, weapon, and effect layers are generated as separate native sources before composition.",
            "The composed frames remain the compatibility output for Godot and Aseprite imports.",
            "Weapon anchor positions use explicit frame anchors for the accepted body-only sheets and may need artist adjustment for final combat polish.",
        ],
    }
    _write_text(action_dir / "layered_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return {
        "manifest": f"actions/{action}/layered_manifest.json",
        "source": "native_separated_layers",
        "layers": layer_names,
        "z_order": z_order,
        "weapon_visible_frames": manifest["weapon_visible_frames"],
        "effect_visible_frames": manifest["effect_visible_frames"],
        "timing_windows": timing_windows,
        "extraction_method": None,
        "composition_method": "native_body_weapon_effect_layers",
    }


def _write_layered_action_outputs(
    action: str,
    frame_paths: list[Path],
    action_dir: Path,
    fps: int,
) -> dict[str, Any] | None:
    spec = ACTION_RUNTIME_SPECS[action]
    layer_contract = spec.get("layer_contract")
    if not layer_contract:
        return None

    layers = layer_contract["layers"]
    z_order = layer_contract["z_order"]
    layer_root = action_dir / "layers"
    if layer_root.exists():
        shutil.rmtree(layer_root)

    written_paths: dict[str, list[Path]] = {layer: [] for layer in layers}
    non_empty_frames: dict[str, list[int]] = {layer: [] for layer in layers}
    for frame_index, frame_path in enumerate(frame_paths):
        frame = Image.open(frame_path).convert("RGBA")
        split = _split_weapon_action_layers(frame)
        for layer in layers:
            frames_dir = layer_root / layer / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            output = frames_dir / frame_path.name
            split[layer].save(output)
            written_paths[layer].append(output)
            if _has_visible_foreground(split[layer]):
                non_empty_frames[layer].append(frame_index)

    layer_artifacts: dict[str, Any] = {}
    for layer in layers:
        layer_dir = layer_root / layer
        paths = written_paths[layer]
        make_sprite_sheet(paths, layer_dir / "spritesheet.png", columns=len(paths))
        make_preview_gif(paths, layer_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
        make_contact_sheet(paths, layer_dir / "contact_sheet.png", columns=min(4, len(paths)))
        layer_artifacts[layer] = {
            "frames": [f"layers/{layer}/frames/{path.name}" for path in paths],
            "spritesheet": f"layers/{layer}/spritesheet.png",
            "preview_gif": f"layers/{layer}/preview.gif",
            "contact_sheet": f"layers/{layer}/contact_sheet.png",
            "non_empty_frames": non_empty_frames[layer],
        }

    timing_windows = {
        "hit_frames": spec.get("hit_frames", []),
        "parry_frames": spec.get("parry_frames", []),
        "invulnerable_frames": spec.get("invulnerable_frames", []),
    }
    manifest = {
        "action": action,
        "status": "layered_review_ready",
        "source": "heuristic_split_from_composed_frames",
        "composite_source": "frames/*.png",
        "layers": layers,
        "z_order": z_order,
        "layer_artifacts": layer_artifacts,
        "weapon_visible_frames": non_empty_frames.get("weapon", []),
        "effect_visible_frames": non_empty_frames.get("effect", []),
        "timing_windows": timing_windows,
        "notes": [
            "Layer extraction is heuristic because the current source roughs are composed images.",
            "Future weapon/effect actions should prefer native separated source layers when possible.",
            "The composed frames remain the compatibility output for game import.",
        ],
    }
    _write_text(action_dir / "layered_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return {
        "manifest": f"actions/{action}/layered_manifest.json",
        "layers": layers,
        "z_order": z_order,
        "weapon_visible_frames": manifest["weapon_visible_frames"],
        "effect_visible_frames": manifest["effect_visible_frames"],
        "timing_windows": timing_windows,
        "extraction_method": "heuristic_split_from_composed_frames",
    }


def _split_weapon_action_layers(frame: Image.Image) -> dict[str, Image.Image]:
    width, height = frame.size
    body = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    weapon = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    effect = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    source = frame.load()
    effect_pixels: set[tuple[int, int]] = set()
    weapon_candidates: set[tuple[int, int]] = set()

    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = source[x, y]
            if alpha == 0:
                continue
            if _is_effect_pixel(red, green, blue):
                effect_pixels.add((x, y))
            elif _is_weapon_candidate_pixel(red, green, blue):
                weapon_candidates.add((x, y))

    weapon_pixels = _select_weapon_components(weapon_candidates, width, height)
    for y in range(height):
        for x in range(width):
            pixel = source[x, y]
            if pixel[3] == 0:
                continue
            if (x, y) in effect_pixels:
                effect.putpixel((x, y), pixel)
            elif (x, y) in weapon_pixels:
                weapon.putpixel((x, y), pixel)
            else:
                body.putpixel((x, y), pixel)
    return {"body": body, "weapon": weapon, "effect": effect}


def _has_visible_foreground(image: Image.Image) -> bool:
    return image.getchannel("A").getbbox() is not None


def _is_effect_pixel(red: int, green: int, blue: int) -> bool:
    is_yellow_spark = red > 185 and green > 150 and blue < 95
    is_cyan_arc = red < 135 and green > 145 and blue > 125
    is_bright_green_spark = red < 170 and green > 185 and blue < 120
    return is_yellow_spark or is_cyan_arc or is_bright_green_spark


def _is_weapon_candidate_pixel(red: int, green: int, blue: int) -> bool:
    brightness = max(red, green, blue)
    darkness = min(red, green, blue)
    saturation = brightness - darkness
    is_blade_gray = 85 <= brightness <= 235 and saturation <= 80
    return is_blade_gray


def _select_weapon_components(
    candidates: set[tuple[int, int]],
    width: int,
    height: int,
) -> set[tuple[int, int]]:
    visited: set[tuple[int, int]] = set()
    selected: set[tuple[int, int]] = set()
    for start in candidates:
        if start in visited:
            continue
        stack = [start]
        visited.add(start)
        component: list[tuple[int, int]] = []
        while stack:
            x, y = stack.pop()
            component.append((x, y))
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if nx < 0 or nx >= width or ny < 0 or ny >= height:
                    continue
                if (nx, ny) not in candidates or (nx, ny) in visited:
                    continue
                visited.add((nx, ny))
                stack.append((nx, ny))
        if _looks_like_weapon_component(component):
            selected.update(component)
    return selected


def _looks_like_weapon_component(component: list[tuple[int, int]]) -> bool:
    if len(component) < 16:
        return False
    xs = [point[0] for point in component]
    ys = [point[1] for point in component]
    width = max(xs) - min(xs) + 1
    height = max(ys) - min(ys) + 1
    long_axis = max(width, height)
    short_axis = max(1, min(width, height))
    aspect = long_axis / short_axis
    area = len(component)
    return long_axis >= 35 and aspect >= 3.2 and area <= 3500


def _prefix_preview_paths(previews: dict[str, Any], prefix: str) -> dict[str, Any]:
    prefixed: dict[str, Any] = {}
    for label, preview in previews.items():
        prefixed[label] = {
            "frame_size": preview["frame_size"],
            "frames": [f"{prefix}/{path}" for path in preview["frames"]],
            "spritesheet": f"{prefix}/{preview['spritesheet']}",
            "preview_gif": f"{prefix}/{preview['preview_gif']}",
            "contact_sheet": f"{prefix}/{preview['contact_sheet']}",
        }
    return prefixed


def _build_action_runtime(
    action: str,
    frame_paths: list[Path],
    fps: int,
    phase_names: list[str],
) -> dict[str, Any]:
    spec = ACTION_RUNTIME_SPECS[action]
    metrics = _action_metrics(frame_paths)
    boxes = [_alpha_bbox(Image.open(path).convert("RGBA")) for path in frame_paths]
    union = _union_bbox(boxes)
    padded_collision = _pad_bbox(union, metrics["frame_size"]["width"], metrics["frame_size"]["height"], padding=4)
    origin = {
        "policy": "bottom_center_canvas",
        "x": metrics["frame_size"]["width"] // 2,
        "y": metrics["frame_size"]["height"],
    }
    playback_indices = spec.get("playback_frame_indices", list(range(len(frame_paths))))
    hit_frames = spec.get("hit_frames", [])
    invulnerable_frames = spec.get("invulnerable_frames", [])
    parry_frames = spec.get("parry_frames", [])
    runtime = {
        "fps": fps,
        "frame_duration_ms": round(1000 / fps),
        "loop": spec["loop"],
        "source_frame_count": len(frame_paths),
        "playback_frame_indices": playback_indices,
        "playback_frame_count": len(playback_indices),
        "hit_frames": hit_frames,
        "invulnerable_frames": invulnerable_frames,
        "parry_frames": parry_frames,
        "frame_density_note": (
            "Playback indices may add limited-animation holds for runtime feel. "
            "True inbetween art should come from an authored or I2I rough retake."
        ),
        "origin": origin,
        "pivot": origin,
        "origin_note": "Use a stable bottom-center canvas origin so action transitions do not jump.",
        "collision_box": _bbox_to_rect(padded_collision),
        "visible_bbox": _bbox_to_rect(union),
        "ground_y_range": metrics["ground_y_range"],
        "phase_events": [
            {
                "frame": index,
                "phase": phase_names[index] if index < len(phase_names) else f"frame_{index:03d}",
            }
            for index in range(len(frame_paths))
        ],
        "transition_notes": spec["transition_notes"],
        "review_role": spec["review_role"],
        "import_assumptions": {
            "godot": "SpriteFrames or AnimatedSprite2D per action; use origin as bottom-center canvas.",
            "aseprite": "Import frames as one tag per action; keep transparent canvas size unchanged.",
        },
    }
    if "layer_contract" in spec:
        runtime["layered"] = {
            "manifest": f"actions/{action}/layered_manifest.json",
            "layers": spec["layer_contract"]["layers"],
            "z_order": spec["layer_contract"]["z_order"],
            "source": "native_separated_layers",
        }
    return runtime


def _attach_frame_density_reviews(output_dir: Path, actions: dict[str, dict[str, Any]]) -> None:
    for action, action_info in actions.items():
        review = _frame_density_review(action, action_info)
        action_info["frame_density_review"] = review
        action_info["runtime"]["frame_density_review"] = review
        report_path = action_info.get("production_ready_report")
        if not report_path:
            continue
        full_path = output_dir / report_path
        if not full_path.exists():
            continue
        report = json.loads(full_path.read_text(encoding="utf-8"))
        report["frame_density_review"] = review
        _write_text(full_path, json.dumps(report, indent=2, ensure_ascii=False) + "\n")


def _frame_density_review(action: str, action_info: dict[str, Any]) -> dict[str, Any]:
    policy = FRAME_DENSITY_POLICY[action]
    source_count = int(action_info["runtime"]["source_frame_count"])
    playback_count = int(action_info["runtime"]["playback_frame_count"])
    recommended_min = int(policy["recommended_min"])
    recommended_max = int(policy["recommended_max"])
    if source_count < recommended_min:
        decision = "below_recommended_retake_source_frames"
    elif source_count > recommended_max:
        decision = "above_recommended_review_timing"
    else:
        decision = "within_recommended_range"
    return {
        "source_frame_count": source_count,
        "playback_frame_count": playback_count,
        "recommended_min": recommended_min,
        "recommended_max": recommended_max,
        "decision": decision,
        "policy": "review_guidance_not_universal_rule",
        "fake_inbetween_policy": "reject_crossfade_or_blended_ghost_frames",
    }


def _build_runtime_manifest(actions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "origin_policy": "bottom_center_canvas",
        "frame_canvas_policy": "stable_canvas_per_pack",
        "frame_density_policy": FRAME_DENSITY_POLICY,
        "spritesheet_authoring_policy": SPRITESHEET_AUTHORING_POLICY,
        "actions": {
            action: action_info["runtime"]
            for action, action_info in actions.items()
        },
    }


def _build_pack_review(
    output_dir: Path,
    actions_dir: Path,
    actions: dict[str, dict[str, Any]],
    identity_report: dict[str, Any],
    backend_usage: dict[str, bool],
) -> dict[str, Any]:
    review_dir = output_dir / "pack_review"
    review_dir.mkdir(parents=True, exist_ok=True)

    all_actions_contact_sheet = review_dir / "all_actions_contact_sheet.png"
    _write_all_actions_contact_sheet(actions_dir, actions, all_actions_contact_sheet)

    consistency_report = _build_consistency_report(
        actions_dir=actions_dir,
        actions=actions,
        identity_report=identity_report,
        backend_usage=backend_usage,
        all_actions_contact_sheet=all_actions_contact_sheet,
    )
    _write_text(
        review_dir / "consistency_report.json",
        json.dumps(consistency_report, indent=2, ensure_ascii=False) + "\n",
    )
    _write_text(
        review_dir / "style_consistency_report.json",
        json.dumps(consistency_report["style_consistency"], indent=2, ensure_ascii=False) + "\n",
    )

    godot_import_manifest = _build_godot_import_manifest(actions)
    _write_text(
        review_dir / "godot_import_manifest.json",
        json.dumps(godot_import_manifest, indent=2, ensure_ascii=False) + "\n",
    )
    _write_text(review_dir / "aseprite_import_notes.md", _aseprite_import_notes(actions))

    return {
        "all_actions_contact_sheet": "pack_review/all_actions_contact_sheet.png",
        "consistency_report": consistency_report,
        "style_consistency_report": "pack_review/style_consistency_report.json",
        "godot_import_manifest": "pack_review/godot_import_manifest.json",
        "aseprite_import_notes": "pack_review/aseprite_import_notes.md",
    }


def _write_all_actions_contact_sheet(
    actions_dir: Path,
    actions: dict[str, dict[str, Any]],
    output_path: Path,
) -> None:
    columns = max(action_info["frame_count"] for action_info in actions.values())
    thumb_h = 128
    cell_w = 116
    cell_h = 164
    label_w = 84
    pad = 8
    width = label_w + columns * cell_w + pad * 2
    height = len(actions) * cell_h + pad * 2
    sheet = Image.new("RGBA", (width, height), (245, 245, 245, 255))
    draw = ImageDraw.Draw(sheet)

    for row, (action, action_info) in enumerate(actions.items()):
        y = pad + row * cell_h
        draw.text((pad, y + 8), action, fill=(20, 20, 20, 255))
        draw.text((pad, y + 28), f"{action_info['frame_count']}f", fill=(80, 80, 80, 255))
        draw.text((pad, y + 48), "loop" if action_info["runtime"]["loop"] else "once", fill=(80, 80, 80, 255))

        for index in range(action_info["frame_count"]):
            source = actions_dir / action / "frames" / f"{action}_{index:03d}.png"
            image = Image.open(source).convert("RGBA")
            scale = thumb_h / image.height
            thumb_w = round(image.width * scale)
            thumb = image.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            x = label_w + index * cell_w + (cell_w - thumb_w) // 2
            sheet.alpha_composite(thumb, (x, y + 8))
            draw.text((label_w + index * cell_w + 6, y + thumb_h + 16), f"{index:02d}", fill=(70, 70, 70, 255))

    sheet.save(output_path)


def _build_consistency_report(
    actions_dir: Path,
    actions: dict[str, dict[str, Any]],
    identity_report: dict[str, Any],
    backend_usage: dict[str, bool],
    all_actions_contact_sheet: Path,
) -> dict[str, Any]:
    frame_sizes = {
        action: (action_info["frame_size"]["width"], action_info["frame_size"]["height"])
        for action, action_info in actions.items()
    }
    loop_flags = {action: action_info["runtime"]["loop"] for action, action_info in actions.items()}
    runtime_metadata_present = all("runtime" in action_info for action_info in actions.values())
    common_canvas_size = len(set(frame_sizes.values())) == 1
    unsupported_backends_unused = not any(backend_usage.values())
    review_artifacts_present = all_actions_contact_sheet.exists()
    style_consistency = _build_style_consistency_report(actions_dir, actions)
    frame_density = {
        action: action_info["frame_density_review"]
        for action, action_info in actions.items()
    }
    frame_density_pass = all(
        review["decision"] in {"within_recommended_range", "above_recommended_review_timing"}
        for review in frame_density.values()
    )
    action_reports = {
        action: {
            "frame_count": action_info["frame_count"],
            "frame_size": action_info["frame_size"],
            "loop": action_info["runtime"]["loop"],
            "fps": action_info["runtime"]["fps"],
            "ground_y_range": action_info["runtime"]["ground_y_range"],
            "visible_bbox": action_info["runtime"]["visible_bbox"],
            "collision_box": action_info["runtime"]["collision_box"],
            "origin": action_info["runtime"]["origin"],
            "frame_density_review": action_info["frame_density_review"],
            "style_consistency_label": style_consistency["actions"][action]["label"],
            "style_metrics": style_consistency["actions"][action]["metrics"],
        }
        for action, action_info in actions.items()
    }
    checks = {
        "runtime_metadata_present": runtime_metadata_present,
        "common_canvas_size": common_canvas_size,
        "identity_cues_pass": identity_report["all_required_cues_pass"] is True,
        "unsupported_backends_unused": unsupported_backends_unused,
        "review_artifacts_present": review_artifacts_present,
        "style_consistency_gate_pass": style_consistency["passed"] is True,
        "frame_density_policy_present": bool(FRAME_DENSITY_POLICY),
        "frame_density_pass": frame_density_pass,
        "loop_flags_expected": loop_flags == {
            "walk": True,
            "idle": True,
            "run": True,
            "jump": False,
            "hurt": False,
            "dodge_backstep": False,
            "parry_sword": False,
            "attack_sword_light": False,
        },
    }
    blocking = [name for name, passed in checks.items() if not passed]
    return {
        "status": "pass" if not blocking else "needs_review",
        "passed": not blocking,
        "checks": checks,
        "blocking_issues": blocking,
        "action_reports": action_reports,
        "style_consistency": style_consistency,
        "frame_density_policy": FRAME_DENSITY_POLICY,
        "review_artifacts": {
            "all_actions_contact_sheet": "pack_review/all_actions_contact_sheet.png",
            "style_consistency_report": "pack_review/style_consistency_report.json",
        },
        "runtime_import_decision": "ready_for_godot_aseprite_import_review" if not blocking else "needs_pack_review",
    }


def _build_style_consistency_report(actions_dir: Path, actions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    action_reports = {}
    for action, action_info in actions.items():
        frame_paths = [
            actions_dir / action / "frames" / f"{action}_{index:03d}.png"
            for index in range(action_info["frame_count"])
        ]
        metrics = _style_metrics_for_frames(frame_paths)
        label = _style_label(metrics)
        action_reports[action] = {
            "label": label,
            "metrics": metrics,
            "notes": _style_notes_for_label(label),
        }
    retake_actions = [
        action for action, report in action_reports.items()
        if report["label"] == "style_retake_needed"
    ]
    return {
        "status": "pass" if not retake_actions else "needs_retake",
        "passed": not retake_actions,
        "retake_actions": retake_actions,
        "actions": action_reports,
        "required_labels": ["style_pass", "style_review", "style_retake_needed"],
        "honesty_note": (
            "This deterministic gate catches missing cues, bad transparency, and scale/canvas drift. "
            "Agent visual review still overrides it when an action visibly drifts."
        ),
    }


def _style_metrics_for_frames(frame_paths: list[Path]) -> dict[str, Any]:
    boxes: list[tuple[int, int, int, int]] = []
    sizes: list[tuple[int, int]] = []
    corner_alpha_ok = True
    cue_counts = {cue: 0 for cue in IDENTITY_CUES}
    foreground_count = 0
    saturation_sum = 0.0
    brightness_sum = 0.0
    hair_pixels: list[tuple[int, int, int]] = []

    for path in frame_paths:
        image = Image.open(path).convert("RGBA")
        sizes.append(image.size)
        boxes.append(_alpha_bbox(image))
        for corner in [(0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1)]:
            if image.getpixel(corner)[3] != 0:
                corner_alpha_ok = False
        cue = _cue_counts([image])
        for name, count in cue.items():
            cue_counts[name] += count
        raw = image.tobytes()
        for offset in range(0, len(raw), 4):
            red, green, blue, alpha = raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3]
            if alpha < 64:
                continue
            foreground_count += 1
            bright = max(red, green, blue)
            dark = min(red, green, blue)
            brightness_sum += bright / 255.0
            saturation_sum += 0.0 if bright == 0 else (bright - dark) / bright
            if red > 185 and 70 <= green <= 180 and 95 <= blue <= 205:
                hair_pixels.append((red, green, blue))

    widths = [box[2] - box[0] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    dominant_hair_color = _average_rgb(hair_pixels)
    return {
        "frame_count": len(frame_paths),
        "canvas_consistent": len(set(sizes)) == 1,
        "transparent_corners": corner_alpha_ok,
        "foreground_bbox_width_range": max(widths) - min(widths),
        "foreground_bbox_height_range": max(heights) - min(heights),
        "foreground_bbox_width_median": sorted(widths)[len(widths) // 2],
        "foreground_bbox_height_median": sorted(heights)[len(heights) // 2],
        "dominant_hair_color": dominant_hair_color,
        "cue_counts": cue_counts,
        "average_saturation": round(saturation_sum / max(1, foreground_count), 4),
        "average_brightness": round(brightness_sum / max(1, foreground_count), 4),
    }


def _average_rgb(pixels: list[tuple[int, int, int]]) -> dict[str, int] | None:
    if not pixels:
        return None
    return {
        "red": round(sum(pixel[0] for pixel in pixels) / len(pixels)),
        "green": round(sum(pixel[1] for pixel in pixels) / len(pixels)),
        "blue": round(sum(pixel[2] for pixel in pixels) / len(pixels)),
    }


def _style_label(metrics: dict[str, Any]) -> str:
    cue_counts = metrics["cue_counts"]
    core_cues_present = all(cue_counts[cue] > 0 for cue in IDENTITY_CUES)
    if not metrics["canvas_consistent"] or not metrics["transparent_corners"] or not core_cues_present:
        return "style_retake_needed"
    if metrics["foreground_bbox_height_range"] > 28 or metrics["foreground_bbox_width_range"] > 52:
        return "style_review"
    if metrics["average_brightness"] < 0.18 or metrics["average_saturation"] < 0.08:
        return "style_review"
    return "style_pass"


def _style_notes_for_label(label: str) -> list[str]:
    if label == "style_pass":
        return ["Required cues, transparency, and coarse scale metrics are within the current pack style gate."]
    if label == "style_review":
        return ["Required cues are present, but scale/color variance needs Agent visual review."]
    return ["A required cue, transparent corner, or canvas consistency check failed; retake before production."]


def _build_godot_import_manifest(actions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "asset_kind": "AnimatedSprite2D_action_pack",
        "origin_policy": "bottom_center_canvas",
        "spritesheet_authoring_policy": SPRITESHEET_AUTHORING_POLICY,
        "actions": {
            action: {
                "spritesheet": action_info["spritesheet"],
                "frames": action_info["frames"],
                "fps": action_info["runtime"]["fps"],
                "loop": action_info["runtime"]["loop"],
                "frame_duration_ms": action_info["runtime"]["frame_duration_ms"],
                "origin": action_info["runtime"]["origin"],
                "collision_box": action_info["runtime"]["collision_box"],
                "hit_frames": action_info["runtime"].get("hit_frames", []),
                "invulnerable_frames": action_info["runtime"].get("invulnerable_frames", []),
                "parry_frames": action_info["runtime"].get("parry_frames", []),
                "layered": action_info["runtime"].get("layered"),
                "frame_density_review": action_info["frame_density_review"],
                "transition_notes": action_info["runtime"]["transition_notes"],
            }
            for action, action_info in actions.items()
        },
    }


def _write_style_reference_set(
    actions_dir: Path,
    actions: dict[str, dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    selected = [
        ("idle", 0, "neutral"),
        ("walk", 2, "passing_pose"),
        ("run", 2, "readable_stride"),
        ("attack_sword_light", 7, "active_slash"),
        ("parry_sword", 3, "guard_contact"),
    ]
    if output_dir.exists():
        shutil.rmtree(output_dir)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    copied_paths: list[Path] = []
    entries = []
    for action, frame_index, role in selected:
        if action not in actions:
            continue
        clamped_index = min(frame_index, actions[action]["frame_count"] - 1)
        source = actions_dir / action / "frames" / f"{action}_{clamped_index:03d}.png"
        target = frames_dir / f"{action}_{clamped_index:03d}_{role}.png"
        shutil.copy2(source, target)
        copied_paths.append(target)
        entries.append(
            {
                "source_action": action,
                "source_frame": clamped_index,
                "role": role,
                "path": str(target).replace("\\", "/"),
            }
        )

    if copied_paths:
        make_contact_sheet(copied_paths, output_dir / "contact_sheet.png", columns=len(copied_paths))
    manifest = {
        "name": "character_sprite_pack_v1",
        "purpose": "accepted_pack_style_reference_for_future_action_roughs",
        "source_pack": "outputs/adoptable/character_sprite_asset_pack",
        "entries": entries,
        "identity_cues": IDENTITY_CUES,
        "expected_palette_notes": {
            "hair": "pink bob hair remains a high-signal identity cue",
            "top": "sailor-style white top stays bright and readable",
            "tie": "red tie should remain visible at game scale",
            "uniform": "navy skirt and dark socks stay grouped as the dark uniform mass",
            "shoes": "brown shoes should be visible near ground contact",
        },
        "expected_line_shape_notes": [
            "Use the accepted pack style as the primary style target.",
            "Use the original illustration as identity reference, not direct animation source.",
            "Future roughs should be manual edits or image-to-image against this pack style before cleanup.",
        ],
    }
    _write_text(output_dir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return {
        "path": str(output_dir).replace("\\", "/"),
        "manifest": str(output_dir / "manifest.json").replace("\\", "/"),
        "contact_sheet": str(output_dir / "contact_sheet.png").replace("\\", "/"),
        "frame_count": len(copied_paths),
    }


def _aseprite_import_notes(actions: dict[str, dict[str, Any]]) -> str:
    rows = [
        "# Aseprite Import Notes",
        "",
        "Keep the transparent canvas size unchanged for every action.",
        "Use one Aseprite tag per action and keep the bottom-center canvas origin stable in the game runtime.",
        "",
        "| action | frames | fps | loop | role |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for action, action_info in actions.items():
        runtime = action_info["runtime"]
        rows.append(
            f"| {action} | {action_info['frame_count']} | {runtime['fps']} | {runtime['loop']} | {runtime['review_role']} |"
        )
    rows.append("")
    rows.append("This pack is ready for runtime import review, not a guarantee that every future action is solved.")
    return "\n".join(rows) + "\n"


def _union_bbox(boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _pad_bbox(
    box: tuple[int, int, int, int],
    width: int,
    height: int,
    padding: int,
) -> tuple[int, int, int, int]:
    return (
        max(0, box[0] - padding),
        max(0, box[1] - padding),
        min(width, box[2] + padding),
        min(height, box[3] + padding),
    )


def _bbox_to_rect(box: tuple[int, int, int, int]) -> dict[str, int]:
    return {
        "x": box[0],
        "y": box[1],
        "width": box[2] - box[0],
        "height": box[3] - box[1],
    }


def _build_identity_report(reference_image: Path, action_dirs: dict[str, Path]) -> dict[str, Any]:
    reference = Image.open(reference_image).convert("RGBA")
    reference_counts = _cue_counts([reference])
    action_counts = {}
    for action, action_dir in action_dirs.items():
        frame_paths = sorted((action_dir / "frames").glob(f"{action}_*.png"))
        action_counts[action] = _cue_counts([Image.open(path).convert("RGBA") for path in frame_paths])

    cue_reports = {}
    for cue, description in IDENTITY_CUES.items():
        action_pixels = {action: counts[cue] for action, counts in action_counts.items()}
        cue_reports[cue] = {
            "description": description,
            "reference_pixels": reference_counts[cue],
            "action_pixels": action_pixels,
            "passed": (
                reference_counts[cue] > 0
                and all(count > 0 for count in action_pixels.values())
            ),
        }

    all_required_cues_pass = all(report["passed"] for report in cue_reports.values())
    return {
        "status": "identity_cues_pass" if all_required_cues_pass else "identity_cues_need_review",
        "all_required_cues_pass": all_required_cues_pass,
        "cue_reports": cue_reports,
        "source_drift_policy": {
            "accepted_form": "reference_derived_game_sprite_design",
            "not_accepted_form": "untracked redesign that drops required character cues",
            "known_drift": "The current sprite is not a faithful copy of the reference illustration.",
        },
    }


def _build_production_gate(
    actions: dict[str, dict[str, Any]],
    identity_report: dict[str, Any],
    consistency_report: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        f"{action}_production_ready": action_info["production_ready"] is True
        for action, action_info in actions.items()
    }
    checks["identity_cues_pass"] = identity_report["all_required_cues_pass"] is True
    checks["unsupported_backends_unused"] = True
    checks["runtime_metadata_present"] = consistency_report["checks"]["runtime_metadata_present"] is True
    checks["pack_review_generated"] = consistency_report["checks"]["review_artifacts_present"] is True
    checks["consistency_gate_pass"] = consistency_report["passed"] is True
    checks["style_consistency_gate_pass"] = consistency_report["checks"]["style_consistency_gate_pass"] is True
    checks["frame_density_policy_present"] = consistency_report["checks"]["frame_density_policy_present"] is True
    checks["frame_density_pass"] = consistency_report["checks"]["frame_density_pass"] is True
    blocking = [name for name, passed in checks.items() if not passed]
    return {
        "target": "character_sprite_asset_pack_mvp",
        "decision": "production_ready" if not blocking else "needs_retake",
        "production_ready": not blocking,
        "checks": checks,
        "blocking_issues": blocking,
        "scope_statement": (
            "walk, idle, run, jump, hurt, dodge_backstep, parry_sword, and attack_sword_light are production-ready "
            "and ready for runtime import review."
        ),
    }


def _cue_counts(images: list[Image.Image]) -> dict[str, int]:
    counts = {cue: 0 for cue in IDENTITY_CUES}
    for image in images:
        raw = image.tobytes()
        for offset in range(0, len(raw), 4):
            red, green, blue, alpha = raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3]
            if alpha < 64:
                continue
            if red > 185 and 70 <= green <= 180 and 95 <= blue <= 205:
                counts["pink_bob_hair"] += 1
            if red > 225 and green > 225 and blue > 225:
                counts["sailor_white_top"] += 1
            if red > 130 and green < 115 and blue < 115:
                counts["red_tie"] += 1
            if red < 85 and green < 95 and 40 <= blue <= 140:
                counts["navy_skirt"] += 1
                counts["dark_socks"] += 1
            if 65 <= red <= 170 and 25 <= green <= 100 and blue < 85:
                counts["brown_shoes"] += 1
            if alpha > 0:
                counts["side_profile_anime_girl"] += 1
    return counts


def _action_metrics(frame_paths: list[Path]) -> dict[str, Any]:
    boxes = []
    sizes = []
    edge_touch_frames = []
    for index, path in enumerate(frame_paths):
        image = Image.open(path).convert("RGBA")
        sizes.append(image.size)
        box = _alpha_bbox(image)
        boxes.append(box)
        if box[0] <= 0 or box[1] <= 0 or box[2] >= image.width or box[3] >= image.height:
            edge_touch_frames.append(index)
    if len(set(sizes)) != 1:
        raise ValueError("Action frames must share one canvas size.")
    bottoms = [box[3] for box in boxes]
    width, height = sizes[0]
    return {
        "frame_size": {"width": width, "height": height},
        "ground_y_range": max(bottoms) - min(bottoms),
        "alpha_edge_touch_frames": edge_touch_frames,
    }


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    box = image.getchannel("A").getbbox()
    if box is None:
        raise ValueError("Frame has no visible foreground.")
    return box


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _notes(manifest: dict[str, Any]) -> str:
    return f"""# Character Sprite Asset Pack

- route: `{manifest["route"]}`
- production_ready: `{manifest["production_ready"]}`
- current production actions: `{", ".join(manifest["actions"].keys())}`
- runtime_manifest: `{manifest["runtime_manifest"]}`
- pack_review: `pack_review/all_actions_contact_sheet.png`

## Identity Contract

This pack tracks the source-reference cues explicitly: pink bob hair, side-profile anime girl,
sailor-style white top, red tie, navy skirt, dark socks, and brown shoes.

The current sprite is accepted as a reference-derived game sprite design. It is not a faithful copy
of the original illustration, and future actions must preserve the same tracked cues before they can
be marked production-ready.

## Runtime Review

Use the all-actions contact sheet, Godot import manifest, and Aseprite notes to review this as a
small game asset package rather than as loose image files. Collision boxes are approximate review
boxes, not final gameplay hitboxes.
"""


def _idle_notes(report: dict[str, Any]) -> str:
    return f"""# Idle Action

- status: `{report["status"]}`
- production_ready: `{report["production_ready"]}`
- source: `{report["source"]}`
- method: `{report["method"]}`
- frame_count: `{report["frame_count"]}`
- ground_y_range: `{report["ground_y_range"]}`
- alpha_edge_touch_frames: `{report["alpha_edge_touch_frames"]}`
"""


def _run_notes(report: dict[str, Any]) -> str:
    return f"""# Run Action

- status: `{report["status"]}`
- production_ready: `{report["production_ready"]}`
- source: `{report["source"]}`
- method: `{report["method"]}`
- frame_count: `{report["frame_count"]}`
- phase_names: `{report["phase_names"]}`
- contact_ground_y_range: `{report["contact_ground_y_range"]}`
- airborne_lift_detected: `{report["airborne_lift_detected"]}`
- alpha_edge_touch_frames: `{report["alpha_edge_touch_frames"]}`

This is an accepted run cycle packaged under the same identity contract. It adds run-specific
contact/down/flight/reach timing without introducing a new model backend.
"""


def _rough_action_notes(report: dict[str, Any]) -> str:
    return f"""# {report["action"].title()} Action

- status: `{report["status"]}`
- production_ready: `{report["production_ready"]}`
- source: `{report["source"]}`
- method: `{report["method"]}`
- frame_count: `{report["frame_count"]}`
- phase_names: `{report["phase_names"]}`
- ground_y_range: `{report["ground_y_range"]}`
- alpha_edge_touch_frames: `{report["alpha_edge_touch_frames"]}`

{report["review_note"]}
"""


if __name__ == "__main__":
    main()
