from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable
import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.visual_asset_gate import auto_fix_pack, evaluate_pack


@pytest.mark.parametrize(
    ("case_name", "action", "expected_finding"),
    [
        ("jump_scale_outlier", "jump", "large_width_or_scale_jitter"),
        ("hurt_side_panel_overlap", "hurt", "side_panel_or_silhouette_width_outlier"),
        ("hurt_hard_vertical_cut", "hurt", "hard_vertical_alpha_cut"),
        ("green_cyan_alpha_edge_fringe", "jump", "green_cyan_alpha_edge_fringe"),
        ("weak_weapon_readability", "attack_sword_light", "weak_weapon_readability"),
        ("action_style_drift", "hurt", "action_brightness_style_drift"),
        ("abrupt_frame_delta_outlier", "walk", "abrupt_frame_delta_outlier"),
        ("poor_idle_recovery", "hurt", "poor_recovery_to_idle_pose"),
        ("foreground_highlight_clipping", "idle", "foreground_highlight_clipping"),
        ("missing_weapon_layer_separation", "attack_sword_light", "missing_separated_weapon_or_effect_layer"),
        ("identity_lock_missing", "walk", "identity_consistency_lock_missing"),
        ("jump_character_too_small", "jump", "jump_character_scale_too_small"),
        ("idle_too_static", "idle", "idle_too_static_or_low_effort"),
        ("low_secondary_motion_hold_frames", "walk", "low_secondary_motion_or_hold_frame_reuse"),
        ("secondary_cloth_motion_policy_missing", "walk", "secondary_cloth_motion_policy_missing"),
    ],
)
def test_known_visual_trauma_corpus_cases_are_blocked(
    tmp_path: Path,
    case_name: str,
    action: str,
    expected_finding: str,
) -> None:
    pack = tmp_path / case_name
    _build_trauma_case(pack, case_name)

    report = evaluate_pack(pack / "manifest.json")

    assert report["decision"] == "needs_retake_or_manual_review"
    assert action in report["blocking_actions"]
    assert expected_finding in report["actions"][action]["findings"]


def _build_trauma_case(pack: Path, case_name: str) -> None:
    if case_name == "jump_scale_outlier":
        _build_single_action_pack(pack, "jump", _jump_scale_frames)
    elif case_name == "hurt_side_panel_overlap":
        _build_single_action_pack(pack, "hurt", _hurt_side_panel_frames)
    elif case_name == "hurt_hard_vertical_cut":
        _build_single_action_pack(pack, "hurt", _hurt_hard_cut_frames)
    elif case_name == "green_cyan_alpha_edge_fringe":
        _build_single_action_pack(pack, "jump", _green_fringe_frames)
    elif case_name == "weak_weapon_readability":
        _build_single_action_pack(pack, "attack_sword_light", _weak_weapon_frames)
    elif case_name == "action_style_drift":
        _build_style_drift_pack(pack)
    elif case_name == "abrupt_frame_delta_outlier":
        _build_single_action_pack(pack, "walk", _abrupt_motion_frames)
    elif case_name == "poor_idle_recovery":
        _build_poor_idle_recovery_pack(pack)
    elif case_name == "foreground_highlight_clipping":
        _build_single_action_pack(pack, "idle", _highlight_clipped_frames)
    elif case_name == "missing_weapon_layer_separation":
        _build_full_art_direction_pack(pack, separated_weapon=False, identity_lock=True, secondary_motion=True)
    elif case_name == "identity_lock_missing":
        _build_full_art_direction_pack(pack, separated_weapon=True, identity_lock=False, secondary_motion=True)
    elif case_name == "jump_character_too_small":
        _build_full_art_direction_pack(pack, separated_weapon=True, identity_lock=True, secondary_motion=True, jump_small=True)
    elif case_name == "idle_too_static":
        _build_single_action_pack(pack, "idle", _static_idle_frames)
    elif case_name == "low_secondary_motion_hold_frames":
        _build_single_action_pack(pack, "walk", _hold_reuse_frames)
    elif case_name == "secondary_cloth_motion_policy_missing":
        _build_full_art_direction_pack(pack, separated_weapon=True, identity_lock=True, secondary_motion=False)
    else:
        raise AssertionError(f"unknown trauma case: {case_name}")


def test_auto_fix_keeps_original_when_candidate_adds_new_trauma(tmp_path: Path) -> None:
    pack = tmp_path / "hurt_overlap_pack"
    _build_single_action_pack(pack, "hurt", _hurt_side_panel_frames)
    before = evaluate_pack(pack / "manifest.json")
    assert "side_panel_or_silhouette_width_outlier" in before["actions"]["hurt"]["findings"]
    assert "hard_vertical_alpha_cut" not in before["actions"]["hurt"]["findings"]

    fixed_dir = tmp_path / "fixed"
    auto_fix_pack(pack / "manifest.json", fixed_dir)
    after = evaluate_pack(fixed_dir / "manifest.json")

    assert "hard_vertical_alpha_cut" not in after["actions"]["hurt"]["findings"]
    assert after["actions"]["hurt"]["metrics"]["hard_vertical_alpha_cut_frames"] == []


def _build_single_action_pack(pack: Path, action: str, frame_builder: Callable[[Path, str], None]) -> None:
    frame_builder(pack, action)
    frame_paths = sorted((pack / "actions" / action / "frames").glob("*.png"))
    _write_manifest(pack, {action: [path.relative_to(pack).as_posix() for path in frame_paths]})


def _build_style_drift_pack(pack: Path) -> None:
    _plain_action_frames(pack, "walk", tone=40)
    _plain_action_frames(pack, "idle", tone=42)
    _plain_action_frames(pack, "hurt", tone=210)
    _write_manifest(
        pack,
        {
            action: [path.relative_to(pack).as_posix() for path in sorted((pack / "actions" / action / "frames").glob("*.png"))]
            for action in ["walk", "idle", "hurt"]
        },
    )


def _build_poor_idle_recovery_pack(pack: Path) -> None:
    _motion_frames(pack, "idle", [0, 0, 0, 0])
    _motion_frames(pack, "hurt", [0, 4, 8, 80])
    _write_manifest(
        pack,
        {
            action: [path.relative_to(pack).as_posix() for path in sorted((pack / "actions" / action / "frames").glob("*.png"))]
            for action in ["idle", "hurt"]
        },
    )


def _write_manifest(pack: Path, actions: dict[str, list[str]]) -> None:
    payload = {
        "route": "character_sprite_asset_pack",
        "actions": {
            action: {
                "frame_count": len(frames),
                "frames": frames,
                "runtime": {"fps": 8, "loop": action in {"walk", "idle", "run"}},
            }
            for action, frames in actions.items()
        },
    }
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_full_art_direction_pack(
    pack: Path,
    *,
    separated_weapon: bool,
    identity_lock: bool,
    secondary_motion: bool,
    jump_small: bool = False,
) -> None:
    builders = {
        "idle": lambda path, action: _art_direction_frames(path, action, height=118, width=42),
        "walk": lambda path, action: _art_direction_frames(path, action, height=122, width=46),
        "run": lambda path, action: _art_direction_frames(path, action, height=118, width=54),
        "jump": lambda path, action: _art_direction_frames(
            path,
            action,
            height=72 if jump_small else 118,
            width=38 if jump_small else 46,
        ),
        "hurt": lambda path, action: _art_direction_frames(path, action, height=112, width=48),
        "attack_sword_light": lambda path, action: _art_direction_frames(path, action, height=116, width=50, sword=True),
    }
    actions = {}
    for action, builder in builders.items():
        builder(pack, action)
        actions[action] = [
            path.relative_to(pack).as_posix()
            for path in sorted((pack / "actions" / action / "frames").glob("*.png"))
        ]
    payload = {
        "route": "character_sprite_asset_pack",
        "actions": {
            action: {
                "frame_count": len(frames),
                "frames": frames,
                "runtime": {"fps": 8, "loop": action in {"walk", "idle", "run"}},
            }
            for action, frames in actions.items()
        },
    }
    if separated_weapon:
        payload["actions"]["attack_sword_light"]["runtime"]["layered"] = {
            "z_order": ["weapon", "body", "effect"]
        }
    if identity_lock:
        payload["identity_consistency"] = {"locked_reference": "source_design.png"}
    if secondary_motion:
        payload["secondary_motion_policy"] = {"hair": "tracked", "skirt": "tracked"}
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _jump_scale_frames(pack: Path, action: str) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index, width in enumerate([48, 54, 188, 52]):
        image = Image.new("RGBA", (240, 180), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        left = (240 - width) // 2
        draw.ellipse((104, 12, 132, 40), fill=(238, 220, 210, 255))
        draw.rectangle((left, 44, left + width, 130), fill=(35, 35, 43, 255))
        draw.rectangle((left + 12, 130, left + 28, 170), fill=(32, 30, 35, 255))
        draw.rectangle((left + width - 28, 130, left + width - 12, 170), fill=(32, 30, 35, 255))
        image.save(frames / f"{action}_{index:03d}.png")


def _hurt_side_panel_frames(pack: Path, action: str) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        _make_hurt_frame(frames / f"{action}_{index:03d}.png", side_panel=index == 1, hard_cut=False)


def _hurt_hard_cut_frames(pack: Path, action: str) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        _make_hurt_frame(frames / f"{action}_{index:03d}.png", side_panel=False, hard_cut=index == 1)


def _green_fringe_frames(pack: Path, action: str) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        image = Image.new("RGBA", (120, 160), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 28, 82, 150), fill=(35, 35, 43, 255))
        draw.rectangle((36, 24, 86, 154), outline=(0, 210, 80, 255), width=4)
        draw.ellipse((52, 8, 74, 30), fill=(238, 220, 210, 255))
        image.save(frames / f"{action}_{index:03d}.png")


def _weak_weapon_frames(pack: Path, action: str) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        image = Image.new("RGBA", (140, 160), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((58, 10, 82, 34), fill=(238, 220, 210, 255))
        draw.rectangle((48, 38, 92, 108), fill=(34, 34, 42, 255))
        draw.rectangle((52, 108, 64, 150), fill=(32, 30, 35, 255))
        draw.rectangle((76, 108, 88, 150), fill=(32, 30, 35, 255))
        image.save(frames / f"{action}_{index:03d}.png")


def _abrupt_motion_frames(pack: Path, action: str) -> None:
    _motion_frames(pack, action, [0, 0, 44, 0, 0])


def _highlight_clipped_frames(pack: Path, action: str) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        image = Image.new("RGBA", (120, 160), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 34, 84, 122), fill=(34, 34, 42, 255))
        draw.rectangle((44, 8, 80, 62), fill=(255, 255, 255, 255))
        draw.ellipse((54, 18, 78, 42), fill=(255, 244, 236, 255))
        draw.rectangle((46, 122, 58, 154), fill=(16, 16, 18, 255))
        draw.rectangle((68, 122, 80, 154), fill=(16, 16, 18, 255))
        image.save(frames / f"{action}_{index:03d}.png")


def _static_idle_frames(pack: Path, action: str) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (160, 180), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((68, 12, 92, 36), fill=(238, 220, 210, 255))
    draw.rectangle((56, 40, 104, 122), fill=(34, 34, 42, 255))
    draw.rectangle((62, 122, 76, 168), fill=(32, 30, 35, 255))
    draw.rectangle((86, 122, 100, 168), fill=(32, 30, 35, 255))
    for index in range(4):
        image.save(frames / f"{action}_{index:03d}.png")


def _hold_reuse_frames(pack: Path, action: str) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    keyframes = []
    for x_offset in [0, 18, 34, 18]:
        image = Image.new("RGBA", (640, 640), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x = 280 + x_offset
        draw.ellipse((x + 20, 120, x + 76, 176), fill=(238, 220, 210, 255))
        draw.rectangle((x, 190, x + 96, 440), fill=(34, 34, 42, 255))
        draw.rectangle((x + 16, 440, x + 42, 610), fill=(32, 30, 35, 255))
        draw.rectangle((x + 58, 440, x + 84, 610), fill=(32, 30, 35, 255))
        keyframes.append(image)
    expanded = []
    for image in keyframes:
        expanded.extend([image, image.copy()])
    for index, image in enumerate(expanded):
        image.save(frames / f"{action}_{index:03d}.png")


def _art_direction_frames(
    pack: Path,
    action: str,
    *,
    height: int,
    width: int,
    sword: bool = False,
) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        image = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        left = 90 - width // 2 + (index % 2) * 2
        top = 170 - height
        right = left + width
        draw.ellipse((left + width * 0.25, top - 24, left + width * 0.75, top + 4), fill=(238, 220, 210, 255))
        draw.rectangle((left, top + 8, right, top + height * 0.68), fill=(34, 34, 42, 255))
        draw.rectangle((left + 6, top + height * 0.68, left + 18, 170), fill=(32, 30, 35, 255))
        draw.rectangle((right - 18, top + height * 0.68, right - 6, 170), fill=(32, 30, 35, 255))
        if sword:
            draw.line((right, top + 45, min(176, right + 54), top + 10), fill=(236, 236, 245, 255), width=3)
        image.save(frames / f"{action}_{index:03d}.png")


def _motion_frames(pack: Path, action: str, offsets: list[int]) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index, x_offset in enumerate(offsets):
        image = Image.new("RGBA", (180, 160), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x = 64 + x_offset
        draw.ellipse((x + 14, 10, x + 38, 34), fill=(238, 220, 210, 255))
        draw.rectangle((x, 38, x + 48, 106), fill=(34, 34, 42, 255))
        draw.rectangle((x + 8, 106, x + 20, 150), fill=(32, 30, 35, 255))
        draw.rectangle((x + 30, 106, x + 42, 150), fill=(32, 30, 35, 255))
        image.save(frames / f"{action}_{index:03d}.png")


def _plain_action_frames(pack: Path, action: str, tone: int) -> None:
    frames = pack / "actions" / action / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        image = Image.new("RGBA", (120, 160), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((52, 8, 74, 30), fill=(238, 220, 210, 255))
        draw.rectangle((40, 34, 84, 108), fill=(tone, tone, min(255, tone + 8), 255))
        draw.rectangle((46, 108, 58, 150), fill=(32, 30, 35, 255))
        draw.rectangle((68, 108, 80, 150), fill=(32, 30, 35, 255))
        image.save(frames / f"{action}_{index:03d}.png")


def _make_hurt_frame(path: Path, side_panel: bool, hard_cut: bool) -> None:
    image = Image.new("RGBA", (180, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((76, 10, 100, 34), fill=(238, 220, 210, 255))
    draw.rectangle((62, 38, 108, 106), fill=(34, 34, 42, 255))
    draw.rectangle((68, 106, 80, 150), fill=(32, 30, 35, 255))
    draw.rectangle((92, 106, 104, 150), fill=(32, 30, 35, 255))
    if side_panel:
        draw.ellipse((126, 28, 172, 138), outline=(65, 70, 76, 255), width=4)
        draw.arc((132, 36, 164, 130), start=70, end=285, fill=(65, 70, 76, 255), width=3)
        draw.line((108, 60, 128, 66), fill=(65, 70, 76, 255), width=2)
    if hard_cut:
        draw.rectangle((108, 18, 108, 150), fill=(36, 36, 44, 255))
    image.save(path)
