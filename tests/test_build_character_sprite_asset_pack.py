from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_character_sprite_asset_pack.py"


def test_build_character_sprite_asset_pack(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    walk_ready = tmp_path / "walk_ready"
    run_rough = tmp_path / "run_rough"
    jump_rough = tmp_path / "jump_rough"
    hurt_rough = tmp_path / "hurt_rough"
    attack_rough = tmp_path / "attack_rough"
    attack_body_rough = tmp_path / "attack_body_rough"
    dodge_rough = tmp_path / "dodge_rough"
    parry_rough = tmp_path / "parry_rough"
    parry_body_rough = tmp_path / "parry_body_rough"
    style_reference = tmp_path / "style_reference"
    output_dir = tmp_path / "character_sprite_asset_pack"
    _make_reference(reference)
    _make_walk_ready_package(walk_ready)
    _make_run_rough_frames(run_rough)
    _make_jump_rough_frames(jump_rough)
    _make_hurt_rough_frames(hurt_rough)
    _make_attack_sword_light_rough_frames(attack_rough)
    _make_attack_sword_light_body_rough_frames(attack_body_rough)
    _make_dodge_backstep_rough_frames(dodge_rough)
    _make_parry_sword_rough_frames(parry_rough)
    _make_parry_sword_body_rough_frames(parry_body_rough)

    subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--reference-image",
            str(reference),
            "--walk-production-ready-dir",
            str(walk_ready),
            "--run-rough-frames-dir",
            str(run_rough),
            "--jump-rough-frames-dir",
            str(jump_rough),
            "--hurt-rough-frames-dir",
            str(hurt_rough),
            "--attack-sword-light-rough-frames-dir",
            str(attack_rough),
            "--attack-sword-light-body-rough-frames-dir",
            str(attack_body_rough),
            "--dodge-backstep-rough-frames-dir",
            str(dodge_rough),
            "--parry-sword-rough-frames-dir",
            str(parry_rough),
            "--parry-sword-body-rough-frames-dir",
            str(parry_body_rough),
            "--style-reference-dir",
            str(style_reference),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "identity_report.json").exists()
    assert (output_dir / "runtime_manifest.json").exists()
    assert (output_dir / "production_gate.json").exists()
    assert (output_dir / "notes.md").exists()
    assert (output_dir / "pack_review" / "all_actions_contact_sheet.png").exists()
    assert (output_dir / "pack_review" / "consistency_report.json").exists()
    assert (output_dir / "pack_review" / "style_consistency_report.json").exists()
    assert (output_dir / "pack_review" / "godot_import_manifest.json").exists()
    assert (output_dir / "pack_review" / "aseprite_import_notes.md").exists()
    assert (style_reference / "manifest.json").exists()
    assert (style_reference / "contact_sheet.png").exists()

    walk_frames = sorted((output_dir / "actions" / "walk" / "frames").glob("walk_*.png"))
    idle_frames = sorted((output_dir / "actions" / "idle" / "frames").glob("idle_*.png"))
    assert len(walk_frames) == 8
    assert len(idle_frames) == 4
    assert (output_dir / "actions" / "walk" / "preview.gif").exists()
    assert (output_dir / "actions" / "idle" / "preview.gif").exists()
    assert (output_dir / "actions" / "idle" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "idle" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "idle" / "game_previews" / "height_128" / "preview.gif").exists()
    assert (output_dir / "actions" / "run" / "preview.gif").exists()
    assert (output_dir / "actions" / "run" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "run" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "run" / "production_ready_report.json").exists()
    assert (output_dir / "actions" / "run" / "game_previews" / "height_128" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "jump" / "preview.gif").exists()
    assert (output_dir / "actions" / "jump" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "jump" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "jump" / "production_ready_report.json").exists()
    assert (output_dir / "actions" / "jump" / "game_previews" / "height_128" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "hurt" / "preview.gif").exists()
    assert (output_dir / "actions" / "hurt" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "hurt" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "hurt" / "production_ready_report.json").exists()
    assert (output_dir / "actions" / "hurt" / "game_previews" / "height_128" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "attack_sword_light" / "preview.gif").exists()
    assert (output_dir / "actions" / "attack_sword_light" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "attack_sword_light" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "attack_sword_light" / "production_ready_report.json").exists()
    assert (output_dir / "actions" / "attack_sword_light" / "game_previews" / "height_128" / "contact_sheet.png").exists()
    _assert_layered_action_outputs(output_dir, "attack_sword_light", 16)
    assert (output_dir / "actions" / "dodge_backstep" / "preview.gif").exists()
    assert (output_dir / "actions" / "dodge_backstep" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "dodge_backstep" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "dodge_backstep" / "production_ready_report.json").exists()
    assert (output_dir / "actions" / "dodge_backstep" / "game_previews" / "height_128" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "parry_sword" / "preview.gif").exists()
    assert (output_dir / "actions" / "parry_sword" / "spritesheet.png").exists()
    assert (output_dir / "actions" / "parry_sword" / "contact_sheet.png").exists()
    assert (output_dir / "actions" / "parry_sword" / "production_ready_report.json").exists()
    assert (output_dir / "actions" / "parry_sword" / "game_previews" / "height_128" / "contact_sheet.png").exists()
    _assert_layered_action_outputs(output_dir, "parry_sword", 8)

    assert {Image.open(path).size for path in idle_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in idle_frames)
    idle_gif = Image.open(output_dir / "actions" / "idle" / "preview.gif")
    assert getattr(idle_gif, "n_frames", 1) == 4
    run_frames = sorted((output_dir / "actions" / "run" / "frames").glob("run_*.png"))
    assert len(run_frames) == 8
    assert {Image.open(path).size for path in run_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in run_frames)
    run_gif = Image.open(output_dir / "actions" / "run" / "preview.gif")
    assert getattr(run_gif, "n_frames", 1) >= 4
    jump_frames = sorted((output_dir / "actions" / "jump" / "frames").glob("jump_*.png"))
    assert len(jump_frames) == 12
    assert {Image.open(path).size for path in jump_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in jump_frames)
    jump_gif = Image.open(output_dir / "actions" / "jump" / "preview.gif")
    assert getattr(jump_gif, "n_frames", 1) >= 4
    hurt_frames = sorted((output_dir / "actions" / "hurt" / "frames").glob("hurt_*.png"))
    assert len(hurt_frames) == 8
    assert {Image.open(path).size for path in hurt_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in hurt_frames)
    hurt_gif = Image.open(output_dir / "actions" / "hurt" / "preview.gif")
    assert getattr(hurt_gif, "n_frames", 1) == 8
    attack_frames = sorted(
        (output_dir / "actions" / "attack_sword_light" / "frames").glob("attack_sword_light_*.png")
    )
    assert len(attack_frames) == 16
    assert {Image.open(path).size for path in attack_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in attack_frames)
    attack_gif = Image.open(output_dir / "actions" / "attack_sword_light" / "preview.gif")
    assert getattr(attack_gif, "n_frames", 1) >= 4
    dodge_frames = sorted((output_dir / "actions" / "dodge_backstep" / "frames").glob("dodge_backstep_*.png"))
    assert len(dodge_frames) == 8
    assert {Image.open(path).size for path in dodge_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in dodge_frames)
    dodge_gif = Image.open(output_dir / "actions" / "dodge_backstep" / "preview.gif")
    assert getattr(dodge_gif, "n_frames", 1) == 8
    parry_frames = sorted((output_dir / "actions" / "parry_sword" / "frames").glob("parry_sword_*.png"))
    assert len(parry_frames) == 8
    assert {Image.open(path).size for path in parry_frames} == {(96, 96)}
    assert all(Image.open(path).getpixel((0, 0))[3] == 0 for path in parry_frames)
    parry_gif = Image.open(output_dir / "actions" / "parry_sword" / "preview.gif")
    assert getattr(parry_gif, "n_frames", 1) == 8

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["route"] == "character_sprite_asset_pack"
    assert manifest["production_ready"] is True
    assert manifest["actions"]["walk"]["frame_count"] == 8
    assert manifest["actions"]["walk"]["production_ready"] is True
    assert manifest["actions"]["walk"]["runtime"]["loop"] is True
    assert manifest["actions"]["walk"]["runtime"]["origin"]["policy"] == "bottom_center_canvas"
    assert manifest["actions"]["idle"]["frame_count"] == 4
    assert manifest["actions"]["idle"]["production_ready"] is True
    assert manifest["actions"]["idle"]["runtime"]["loop"] is True
    assert manifest["actions"]["run"]["frame_count"] == 8
    assert manifest["actions"]["run"]["production_ready"] is True
    assert manifest["actions"]["run"]["runtime"]["loop"] is True
    assert manifest["actions"]["run"]["phase_names"] == [
        "right_contact",
        "right_down",
        "flight_forward",
        "left_reach",
        "left_contact",
        "left_down",
        "flight_backward",
        "right_reach",
    ]
    assert manifest["actions"]["jump"]["frame_count"] == 12
    assert manifest["actions"]["jump"]["production_ready"] is True
    assert manifest["actions"]["jump"]["runtime"]["loop"] is False
    assert manifest["actions"]["jump"]["runtime"]["source_frame_count"] == 12
    assert manifest["actions"]["jump"]["runtime"]["playback_frame_count"] == 12
    assert manifest["actions"]["jump"]["runtime"]["playback_frame_indices"] == list(range(12))
    assert manifest["actions"]["jump"]["phase_names"] == [
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
    ]
    assert manifest["actions"]["hurt"]["frame_count"] == 8
    assert manifest["actions"]["hurt"]["production_ready"] is True
    assert manifest["actions"]["hurt"]["runtime"]["loop"] is False
    assert manifest["actions"]["hurt"]["runtime"]["source_frame_count"] == 8
    assert manifest["actions"]["hurt"]["runtime"]["playback_frame_count"] == 8
    assert manifest["actions"]["hurt"]["runtime"]["playback_frame_indices"] == list(range(8))
    hurt_bbox = manifest["actions"]["hurt"]["runtime"]["visible_bbox"]
    assert hurt_bbox["x"] > 8
    assert hurt_bbox["x"] + hurt_bbox["width"] < manifest["actions"]["hurt"]["frame_size"]["width"] - 8
    assert manifest["actions"]["hurt"]["phase_names"] == [
        "brace",
        "impact_recoil",
        "strong_recoil",
        "peak_recoil",
        "stagger_forward",
        "crouch_settle",
        "recover_half",
        "recover",
    ]
    assert manifest["actions"]["attack_sword_light"]["frame_count"] == 16
    assert manifest["actions"]["attack_sword_light"]["production_ready"] is True
    assert manifest["actions"]["attack_sword_light"]["runtime"]["loop"] is False
    assert manifest["actions"]["attack_sword_light"]["runtime"]["source_frame_count"] == 16
    assert manifest["actions"]["attack_sword_light"]["runtime"]["playback_frame_count"] == 16
    assert manifest["actions"]["attack_sword_light"]["runtime"]["playback_frame_indices"] == list(range(16))
    assert manifest["actions"]["attack_sword_light"]["runtime"]["hit_frames"] == [6, 7]
    assert manifest["actions"]["attack_sword_light"]["frame_density_review"]["decision"] == "within_recommended_range"
    assert manifest["actions"]["attack_sword_light"]["runtime"]["layered"]["layers"] == ["body", "weapon", "effect"]
    assert manifest["actions"]["attack_sword_light"]["runtime"]["layered"]["source"] == "native_separated_layers"
    assert manifest["actions"]["attack_sword_light"]["layered"]["layers"] == ["body", "weapon", "effect"]
    assert manifest["actions"]["attack_sword_light"]["layered"]["source"] == "native_separated_layers"
    assert manifest["actions"]["attack_sword_light"]["phase_names"] == [
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
    ]
    assert manifest["actions"]["dodge_backstep"]["frame_count"] == 8
    assert manifest["actions"]["dodge_backstep"]["production_ready"] is True
    assert manifest["actions"]["dodge_backstep"]["runtime"]["loop"] is False
    assert manifest["actions"]["dodge_backstep"]["runtime"]["source_frame_count"] == 8
    assert manifest["actions"]["dodge_backstep"]["runtime"]["playback_frame_count"] == 8
    assert manifest["actions"]["dodge_backstep"]["runtime"]["playback_frame_indices"] == list(range(8))
    assert manifest["actions"]["dodge_backstep"]["runtime"]["invulnerable_frames"] == [2, 3, 4]
    assert manifest["actions"]["dodge_backstep"]["phase_names"] == [
        "ready",
        "anticipation_crouch",
        "push_off",
        "low_backstep",
        "slide_peak",
        "landing",
        "recover_low",
        "ready_return",
    ]
    assert manifest["actions"]["parry_sword"]["frame_count"] == 8
    assert manifest["actions"]["parry_sword"]["production_ready"] is True
    assert manifest["actions"]["parry_sword"]["runtime"]["loop"] is False
    assert manifest["actions"]["parry_sword"]["runtime"]["source_frame_count"] == 8
    assert manifest["actions"]["parry_sword"]["runtime"]["playback_frame_count"] == 8
    assert manifest["actions"]["parry_sword"]["runtime"]["playback_frame_indices"] == list(range(8))
    assert manifest["actions"]["parry_sword"]["runtime"]["parry_frames"] == [3, 4]
    assert manifest["actions"]["parry_sword"]["runtime"]["layered"]["layers"] == ["body", "weapon", "effect"]
    assert manifest["actions"]["parry_sword"]["runtime"]["layered"]["source"] == "native_separated_layers"
    assert manifest["actions"]["parry_sword"]["layered"]["layers"] == ["body", "weapon", "effect"]
    assert manifest["actions"]["parry_sword"]["layered"]["source"] == "native_separated_layers"
    assert manifest["actions"]["parry_sword"]["phase_names"] == [
        "ready",
        "raise_guard",
        "brace",
        "parry_contact",
        "deflect",
        "recoil_hold",
        "recover",
        "ready_return",
    ]
    assert manifest["backend_usage"] == {
        "uses_comfyui": False,
        "uses_wan_video": False,
        "uses_controlnet": False,
        "uses_new_model_backend": False,
        "uses_120_frame_generation": False,
    }
    assert manifest["runtime_manifest"] == "runtime_manifest.json"
    assert manifest["pack_review"] == {
        "all_actions_contact_sheet": "pack_review/all_actions_contact_sheet.png",
        "consistency_report": "pack_review/consistency_report.json",
        "style_consistency_report": "pack_review/style_consistency_report.json",
        "godot_import_manifest": "pack_review/godot_import_manifest.json",
        "aseprite_import_notes": "pack_review/aseprite_import_notes.md",
    }
    assert manifest["style_reference_set"]["frame_count"] == 5
    assert manifest["spritesheet_authoring_policy"]["generation_preference"] == "full_spritesheet_first_then_split_frames"
    assert manifest["spritesheet_authoring_policy"]["anchor_policy"] == "stable_root_anchor_with_bottom_center_runtime_origin"

    runtime_manifest = json.loads((output_dir / "runtime_manifest.json").read_text(encoding="utf-8"))
    assert runtime_manifest["origin_policy"] == "bottom_center_canvas"
    assert runtime_manifest["frame_density_policy"]["attack_sword_light"]["recommended_min"] == 12
    assert runtime_manifest["spritesheet_authoring_policy"]["grid_policy"] == (
        "detect_source_cells_before_falling_back_to_proportional_grid"
    )
    assert set(runtime_manifest["actions"]) == {
        "walk",
        "idle",
        "run",
        "jump",
        "hurt",
        "dodge_backstep",
        "parry_sword",
        "attack_sword_light",
    }
    assert runtime_manifest["actions"]["jump"]["loop"] is False
    assert runtime_manifest["actions"]["dodge_backstep"]["loop"] is False
    assert runtime_manifest["actions"]["dodge_backstep"]["invulnerable_frames"] == [2, 3, 4]
    assert runtime_manifest["actions"]["parry_sword"]["loop"] is False
    assert runtime_manifest["actions"]["parry_sword"]["parry_frames"] == [3, 4]
    assert runtime_manifest["actions"]["parry_sword"]["layered"]["z_order"] == ["weapon", "body", "effect"]
    assert runtime_manifest["actions"]["attack_sword_light"]["loop"] is False
    assert runtime_manifest["actions"]["attack_sword_light"]["hit_frames"] == [6, 7]
    assert runtime_manifest["actions"]["attack_sword_light"]["frame_density_review"]["source_frame_count"] == 16
    assert runtime_manifest["actions"]["attack_sword_light"]["layered"]["z_order"] == ["weapon", "body", "effect"]

    consistency = json.loads((output_dir / "pack_review" / "consistency_report.json").read_text(encoding="utf-8"))
    assert consistency["passed"] is True
    assert consistency["runtime_import_decision"] == "ready_for_godot_aseprite_import_review"
    assert consistency["checks"]["runtime_metadata_present"] is True
    assert consistency["checks"]["common_canvas_size"] is True
    assert consistency["checks"]["loop_flags_expected"] is True
    assert consistency["checks"]["style_consistency_gate_pass"] is True
    assert consistency["checks"]["frame_density_pass"] is True
    assert consistency["style_consistency"]["passed"] is True

    style_consistency = json.loads(
        (output_dir / "pack_review" / "style_consistency_report.json").read_text(encoding="utf-8")
    )
    assert style_consistency["passed"] is True
    assert set(style_consistency["actions"]) == {
        "walk",
        "idle",
        "run",
        "jump",
        "hurt",
        "dodge_backstep",
        "parry_sword",
        "attack_sword_light",
    }

    godot_manifest = json.loads((output_dir / "pack_review" / "godot_import_manifest.json").read_text(encoding="utf-8"))
    assert godot_manifest["asset_kind"] == "AnimatedSprite2D_action_pack"
    assert godot_manifest["spritesheet_authoring_policy"]["tail_frame_policy"] == (
        "do_not_export_a_duplicate_first_frame_as_the_final_loop_frame"
    )
    assert godot_manifest["actions"]["walk"]["loop"] is True
    assert godot_manifest["actions"]["hurt"]["loop"] is False
    assert godot_manifest["actions"]["dodge_backstep"]["loop"] is False
    assert godot_manifest["actions"]["dodge_backstep"]["invulnerable_frames"] == [2, 3, 4]
    assert godot_manifest["actions"]["parry_sword"]["loop"] is False
    assert godot_manifest["actions"]["parry_sword"]["parry_frames"] == [3, 4]
    assert godot_manifest["actions"]["parry_sword"]["layered"]["layers"] == ["body", "weapon", "effect"]
    assert godot_manifest["actions"]["attack_sword_light"]["loop"] is False
    assert godot_manifest["actions"]["attack_sword_light"]["hit_frames"] == [6, 7]
    assert godot_manifest["actions"]["attack_sword_light"]["layered"]["layers"] == ["body", "weapon", "effect"]
    assert godot_manifest["actions"]["attack_sword_light"]["frame_density_review"]["source_frame_count"] == 16

    identity = json.loads((output_dir / "identity_report.json").read_text(encoding="utf-8"))
    assert identity["all_required_cues_pass"] is True
    assert set(identity["cue_reports"]) == {
        "pink_bob_hair",
        "side_profile_anime_girl",
        "sailor_white_top",
        "red_tie",
        "navy_skirt",
        "dark_socks",
        "brown_shoes",
    }

    gate = json.loads((output_dir / "production_gate.json").read_text(encoding="utf-8"))
    assert gate["decision"] == "production_ready"
    assert gate["production_ready"] is True
    assert gate["checks"]["run_production_ready"] is True
    assert gate["checks"]["jump_production_ready"] is True
    assert gate["checks"]["hurt_production_ready"] is True
    assert gate["checks"]["dodge_backstep_production_ready"] is True
    assert gate["checks"]["parry_sword_production_ready"] is True
    assert gate["checks"]["attack_sword_light_production_ready"] is True
    assert gate["checks"]["runtime_metadata_present"] is True
    assert gate["checks"]["pack_review_generated"] is True
    assert gate["checks"]["consistency_gate_pass"] is True
    assert gate["checks"]["style_consistency_gate_pass"] is True
    assert gate["checks"]["frame_density_pass"] is True
    assert gate["blocking_issues"] == []

    run_report = json.loads(
        (output_dir / "actions" / "run" / "production_ready_report.json").read_text(encoding="utf-8")
    )
    assert run_report["production_ready"] is True
    assert run_report["source"] == "imagegen_run_8frame_20260614_rough"
    assert run_report["airborne_lift_detected"] is True

    jump_report = json.loads(
        (output_dir / "actions" / "jump" / "production_ready_report.json").read_text(encoding="utf-8")
    )
    assert jump_report["production_ready"] is True
    assert jump_report["source"] == "imagegen_jump_12frame_tiles_20260615_rough"

    hurt_report = json.loads(
        (output_dir / "actions" / "hurt" / "production_ready_report.json").read_text(encoding="utf-8")
    )
    assert hurt_report["production_ready"] is True
    assert hurt_report["source"] == "imagegen_hurt_8frame_tiles_20260615_rough"

    attack_report = json.loads(
        (output_dir / "actions" / "attack_sword_light" / "production_ready_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert attack_report["production_ready"] is True
    assert attack_report["source"] == "native_layers_route_a_attack_sword_light_body_16frame_retime_20260615"
    assert attack_report["frame_density_review"]["source_frame_count"] == 16

    dodge_report = json.loads(
        (output_dir / "actions" / "dodge_backstep" / "production_ready_report.json").read_text(encoding="utf-8")
    )
    assert dodge_report["production_ready"] is True
    assert dodge_report["source"] == "imagegen_dodge_backstep_8frame_tiles_20260615_rough"

    parry_report = json.loads(
        (output_dir / "actions" / "parry_sword" / "production_ready_report.json").read_text(encoding="utf-8")
    )
    assert parry_report["production_ready"] is True
    assert parry_report["source"] == "native_layers_imagegen_parry_sword_body_8frame_tiles_20260615"


def _make_reference(path: Path) -> None:
    image = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((30, 8, 58, 35), fill=(235, 120, 155, 255))
    draw.rectangle((35, 35, 58, 56), fill=(245, 245, 245, 255))
    draw.polygon([(43, 40), (51, 40), (47, 55)], fill=(170, 40, 45, 255))
    draw.polygon([(30, 56), (63, 56), (57, 68), (36, 68)], fill=(25, 35, 80, 255))
    draw.rectangle((37, 68, 43, 85), fill=(15, 25, 65, 255))
    draw.rectangle((52, 68, 58, 85), fill=(15, 25, 65, 255))
    draw.rectangle((33, 84, 47, 90), fill=(120, 65, 35, 255))
    draw.rectangle((49, 84, 64, 90), fill=(120, 65, 35, 255))
    image.save(path)


def _assert_layered_action_outputs(output_dir: Path, action: str, frame_count: int) -> None:
    action_dir = output_dir / "actions" / action
    layered_manifest = action_dir / "layered_manifest.json"
    assert layered_manifest.exists()
    payload = json.loads(layered_manifest.read_text(encoding="utf-8"))
    assert payload["layers"] == ["body", "weapon", "effect"]
    assert payload["z_order"] == ["weapon", "body", "effect"]
    assert payload["source"] == "native_separated_layers"
    assert payload["composite_source"] == "weapon + body + effect"
    for layer in ["body", "weapon", "effect"]:
        layer_dir = action_dir / "layers" / layer
        assert len(list((layer_dir / "frames").glob(f"{action}_*.png"))) == frame_count
        assert (layer_dir / "spritesheet.png").exists()
        assert (layer_dir / "preview.gif").exists()
        assert (layer_dir / "contact_sheet.png").exists()


def _make_walk_ready_package(path: Path) -> None:
    frames_dir = path / "frames"
    frames_dir.mkdir(parents=True)
    for index in range(8):
        _make_sprite_frame(frames_dir / f"walk_{index:03d}.png", index)
    Image.new("RGBA", (96 * 8, 96), (0, 0, 0, 0)).save(path / "spritesheet.png")
    Image.new("RGBA", (96 * 4, 120 * 2), (245, 245, 245, 255)).save(path / "contact_sheet.png")
    Image.new("P", (96, 96)).save(path / "preview.gif")
    report = {
        "status": "production_ready",
        "source": "test",
        "frame_count": 8,
        "frame_size": {"width": 96, "height": 96},
        "estimated_ground_y_range": 0,
        "alpha_edge_touch_frames": [],
        "production_ready": True,
    }
    (path / "production_ready_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


def _make_sprite_frame(path: Path, index: int) -> None:
    image = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    x = 44 + (index % 2)
    draw.ellipse((x - 12, 6, x + 16, 35), fill=(235, 120, 155, 255))
    draw.rectangle((x - 10, 34, x + 14, 56), fill=(245, 245, 245, 255))
    draw.polygon([(x - 2, 38), (x + 8, 38), (x + 3, 55)], fill=(170, 40, 45, 255))
    draw.polygon([(x - 16, 56), (x + 22, 56), (x + 16, 70), (x - 10, 70)], fill=(25, 35, 80, 255))
    draw.rectangle((x - 11, 70, x - 4, 88), fill=(15, 25, 65, 255))
    draw.rectangle((x + 10, 70, x + 17, 88), fill=(15, 25, 65, 255))
    draw.rectangle((x - 15, 87, x + 1, 92), fill=(120, 65, 35, 255))
    draw.rectangle((x + 6, 87, x + 23, 92), fill=(120, 65, 35, 255))
    image.save(path)


def _make_run_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    for index in range(8):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 42
        airborne = index in {2, 3, 6, 7}
        y_offset = -12 if airborne else 0
        stride = 20 if index in {0, 4} else 10
        draw.ellipse((x - 12, 6 + y_offset, x + 16, 35 + y_offset), fill=(235, 120, 155, 255))
        draw.rectangle((x - 8, 34 + y_offset, x + 18, 56 + y_offset), fill=(245, 245, 245, 255))
        draw.polygon([(x + 2, 38 + y_offset), (x + 12, 38 + y_offset), (x + 6, 55 + y_offset)], fill=(170, 40, 45, 255))
        draw.polygon([(x - 16, 56 + y_offset), (x + 24, 56 + y_offset), (x + 16, 70 + y_offset), (x - 12, 70 + y_offset)], fill=(25, 35, 80, 255))
        if index < 4:
            front, rear = stride, -stride
        else:
            front, rear = -stride, stride
        knee_y = 75 + y_offset
        foot_y = 91 + y_offset
        draw.line((x, 68 + y_offset, x + front, foot_y), fill=(15, 25, 65, 255), width=6)
        draw.line((x + 8, 68 + y_offset, x + rear, knee_y, x + rear // 2, foot_y), fill=(15, 25, 65, 255), width=6)
        draw.rectangle((x + front - 7, foot_y - 4, x + front + 10, foot_y + 1), fill=(120, 65, 35, 255))
        draw.rectangle((x + rear // 2 - 7, foot_y - 4, x + rear // 2 + 10, foot_y + 1), fill=(120, 65, 35, 255))
        image.save(path / f"run_{index:03d}.png")


def _make_jump_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    offsets = [8, 10, -2, -10, -18, -26, -30, -22, -12, 4, 8, 6]
    leg_shapes = [
        (-7, 6, 10, 7),
        (-8, 7, 11, 8),
        (-12, 1, 15, 2),
        (-9, -1, 11, 0),
        (-8, -2, 10, -1),
        (-5, -3, 8, -2),
        (-6, -3, 8, -2),
        (-10, -1, 12, 0),
        (-14, 0, 14, 1),
        (-9, 4, 10, 5),
        (-8, 5, 9, 6),
        (-8, 5, 9, 6),
    ]
    for index, y_offset in enumerate(offsets):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 43
        front, front_dy, rear, rear_dy = leg_shapes[index]
        _draw_connected_character(draw, x=x, y_offset=y_offset)
        draw.line((x, 69 + y_offset, x + front, 88 + y_offset + front_dy), fill=(15, 25, 65, 255), width=6)
        draw.line((x + 8, 69 + y_offset, x + rear, 88 + y_offset + rear_dy), fill=(15, 25, 65, 255), width=6)
        draw.rectangle((x + front - 6, 85 + y_offset + front_dy, x + front + 9, 90 + y_offset + front_dy), fill=(120, 65, 35, 255))
        draw.rectangle((x + rear - 6, 85 + y_offset + rear_dy, x + rear + 9, 90 + y_offset + rear_dy), fill=(120, 65, 35, 255))
        image.save(path / f"jump_{index:03d}.png")


def _make_hurt_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    leans = [0, -2, -4, -6, -4, -2, -1, 0]
    arm_reaches = [4, 8, 12, 14, 10, 8, 5, 4]
    for index, lean in enumerate(leans):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 43 + lean
        _draw_connected_character(draw, x=x, y_offset=0)
        reach = arm_reaches[index]
        draw.line((x + 6, 42, x + reach, 54), fill=(245, 245, 245, 255), width=5)
        draw.line((x + 12, 44, x + reach + 8, 58), fill=(245, 245, 245, 255), width=5)
        draw.line((x - 4, 69, x - 8, 90), fill=(15, 25, 65, 255), width=6)
        draw.line((x + 10, 69, x + 15, 90), fill=(15, 25, 65, 255), width=6)
        draw.rectangle((x - 13, 87, x + 3, 92), fill=(120, 65, 35, 255))
        draw.rectangle((x + 9, 87, x + 25, 92), fill=(120, 65, 35, 255))
        image.save(path / f"hurt_{index:03d}.png")


def _make_attack_sword_light_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    sword_tips = [
        (62, 28),
        (52, 18),
        (46, 12),
        (57, 16),
        (82, 30),
        (91, 46),
        (86, 61),
        (68, 75),
        (58, 70),
        (54, 58),
        (56, 46),
        (62, 34),
    ]
    x_offsets = [0, -1, -2, -2, 1, 3, 4, 3, 1, 0, 0, 0]
    for index, tip in enumerate(sword_tips):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 42 + x_offsets[index]
        _draw_connected_character(draw, x=x, y_offset=0)
        hand = (x + 16, 43)
        draw.line((x + 3, 42, hand[0], hand[1]), fill=(245, 220, 190, 255), width=5)
        draw.line((hand, tip), fill=(185, 190, 200, 255), width=4)
        draw.line((hand[0] - 3, hand[1], hand[0] + 4, hand[1]), fill=(95, 55, 35, 255), width=4)
        if index in {5, 6}:
            draw.arc((x + 25, 18, x + 72, 70), start=-35, end=55, fill=(220, 220, 230, 255), width=3)
        draw.line((x - 4, 69, x - 8 + index % 3, 90), fill=(15, 25, 65, 255), width=6)
        draw.line((x + 10, 69, x + 15 - index % 2, 90), fill=(15, 25, 65, 255), width=6)
        draw.rectangle((x - 13, 87, x + 3, 92), fill=(120, 65, 35, 255))
        draw.rectangle((x + 9, 87, x + 25, 92), fill=(120, 65, 35, 255))
        image.save(path / f"attack_sword_light_{index:03d}.png")


def _make_attack_sword_light_body_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    x_offsets = [0, -1, -2, -2, 1, -3, 2, 3, 4, 3, 1, 0, 0, 0, 0, 0]
    arm_poses = [
        (4, 48),
        (10, 43),
        (8, 45),
        (-6, 43),
        (12, 30),
        (18, 36),
        (-10, 54),
        (24, 44),
        (25, 48),
        (22, 46),
        (-8, 54),
        (-2, 55),
        (3, 55),
        (5, 56),
        (12, 58),
        (4, 48),
    ]
    for index, (x_offset, arm_y) in enumerate(zip(x_offsets, arm_poses)):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 42 + x_offset
        _draw_connected_character(draw, x=x, y_offset=0)
        hand_x = x + arm_y[0]
        hand_y = arm_y[1]
        draw.line((x + 3, 42, hand_x, hand_y), fill=(245, 220, 190, 255), width=5)
        draw.ellipse((hand_x - 3, hand_y - 3, hand_x + 3, hand_y + 3), fill=(245, 220, 190, 255))
        image.save(path / f"attack_sword_light_body_{index:03d}.png")


def _make_dodge_backstep_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    x_offsets = [0, -2, -6, -13, -20, -15, -7, 0]
    y_offsets = [0, 2, 4, 6, 4, 2, 1, 0]
    leans = [0, -1, -2, -4, -3, -2, -1, 0]
    for index, (x_offset, y_offset, lean) in enumerate(zip(x_offsets, y_offsets, leans)):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 43 + x_offset
        _draw_connected_character(draw, x=x, y_offset=y_offset)
        draw.line((x + 4, 42 + y_offset, x + 10 + lean, 57 + y_offset), fill=(245, 245, 245, 255), width=5)
        draw.line((x - 4, 69 + y_offset, x - 13, 90), fill=(15, 25, 65, 255), width=6)
        draw.line((x + 10, 69 + y_offset, x + 18, 88), fill=(15, 25, 65, 255), width=6)
        draw.rectangle((x - 20, 87, x - 4, 92), fill=(120, 65, 35, 255))
        draw.rectangle((x + 11, 85, x + 27, 90), fill=(120, 65, 35, 255))
        image.save(path / f"dodge_backstep_{index:03d}.png")


def _make_parry_sword_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    guard_tips = [(60, 70), (67, 54), (72, 42), (75, 31), (79, 35), (72, 44), (65, 57), (60, 70)]
    for index, tip in enumerate(guard_tips):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 43
        _draw_connected_character(draw, x=x, y_offset=0)
        hand = (x + 15, 45)
        draw.line((x + 3, 42, hand[0], hand[1]), fill=(245, 220, 190, 255), width=5)
        draw.line((hand, tip), fill=(185, 190, 200, 255), width=4)
        draw.line((hand[0] - 3, hand[1], hand[0] + 4, hand[1]), fill=(95, 55, 35, 255), width=4)
        if index in {3, 4}:
            draw.arc((x + 18, 20, x + 48, 60), start=-65, end=55, fill=(220, 230, 255, 255), width=3)
        draw.line((x - 4, 69, x - 8, 90), fill=(15, 25, 65, 255), width=6)
        draw.line((x + 10, 69, x + 15, 90), fill=(15, 25, 65, 255), width=6)
        draw.rectangle((x - 13, 87, x + 3, 92), fill=(120, 65, 35, 255))
        draw.rectangle((x + 9, 87, x + 25, 92), fill=(120, 65, 35, 255))
        image.save(path / f"parry_sword_{index:03d}.png")


def _make_parry_sword_body_rough_frames(path: Path) -> None:
    path.mkdir(parents=True)
    hand_poses = [(4, 58), (16, 43), (18, 34), (22, 34), (24, 45), (15, 35), (4, 55), (4, 58)]
    for index, (hand_dx, hand_y) in enumerate(hand_poses):
        image = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        x = 43
        _draw_connected_character(draw, x=x, y_offset=0)
        hand_x = x + hand_dx
        draw.line((x + 3, 42, hand_x, hand_y), fill=(245, 220, 190, 255), width=5)
        draw.ellipse((hand_x - 3, hand_y - 3, hand_x + 3, hand_y + 3), fill=(245, 220, 190, 255))
        image.save(path / f"parry_sword_body_{index:03d}.png")


def _draw_connected_character(draw: ImageDraw.ImageDraw, x: int, y_offset: int) -> None:
    draw.ellipse((x - 12, 6 + y_offset, x + 16, 35 + y_offset), fill=(235, 120, 155, 255))
    draw.rectangle((x - 8, 33 + y_offset, x + 18, 57 + y_offset), fill=(245, 245, 245, 255))
    draw.polygon(
        [(x + 2, 38 + y_offset), (x + 12, 38 + y_offset), (x + 6, 56 + y_offset)],
        fill=(170, 40, 45, 255),
    )
    draw.polygon(
        [(x - 16, 56 + y_offset), (x + 24, 56 + y_offset), (x + 16, 70 + y_offset), (x - 12, 70 + y_offset)],
        fill=(25, 35, 80, 255),
    )
