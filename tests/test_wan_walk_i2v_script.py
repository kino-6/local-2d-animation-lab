from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_wan_walk_i2v.py"
_SPEC = importlib.util.spec_from_file_location("run_wan_walk_i2v", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

_pose_source_indices = _MODULE._pose_source_indices
_fun_control_workflow = _MODULE._fun_control_workflow
_vace_workflow = _MODULE._vace_workflow
_render_control_frame = _MODULE._render_control_frame


def test_pose_source_indices_default_samples_full_template() -> None:
    assert _pose_source_indices(pose_count=120, length=5, phase=0, sample_span=None) == [0, 30, 60, 89, 119]


def test_pose_source_indices_can_limit_sample_span_and_wrap_phase() -> None:
    assert _pose_source_indices(pose_count=120, length=5, phase=110, sample_span=20) == [110, 115, 0, 5, 10]


def test_wan22_fun_control_workflow_uses_ref_image_and_control_video() -> None:
    workflow = _fun_control_workflow(
        _minimal_args(),
        "start.png",
        ["pose_000.png", "pose_001.png"],
        class_type="Wan22FunControlToVideo",
    )

    node = workflow["11"]
    assert node["class_type"] == "Wan22FunControlToVideo"
    assert node["inputs"]["ref_image"] == ["8", 0]
    assert "control_video" in node["inputs"]
    assert "start_image" not in node["inputs"]
    assert "clip_vision_output" not in node["inputs"]


def test_fun_control_workflow_keeps_legacy_start_image_inputs() -> None:
    workflow = _fun_control_workflow(
        _minimal_args(),
        "start.png",
        ["pose_000.png"],
        class_type="WanFunControlToVideo",
    )

    node = workflow["11"]
    assert node["class_type"] == "WanFunControlToVideo"
    assert node["inputs"]["start_image"] == ["8", 0]
    assert node["inputs"]["clip_vision_output"] == ["10", 0]
    assert "ref_image" not in node["inputs"]


def test_vace_workflow_uses_reference_image_and_control_video() -> None:
    workflow = _vace_workflow(
        _minimal_args(),
        "reference.png",
        ["pose_000.png", "pose_001.png"],
    )

    node = workflow["11"]
    assert node["class_type"] == "WanVaceToVideo"
    assert node["inputs"]["reference_image"] == ["8", 0]
    assert "control_video" in node["inputs"]
    assert node["inputs"]["strength"] == 1.0
    assert workflow["19"]["class_type"] == "TrimVideoLatent"
    assert workflow["13"]["inputs"]["samples"] == ["19", 0]


def test_render_control_frame_can_overlay_weapon_guide() -> None:
    args = _minimal_args()
    frame = {
        "action": "attack",
        "variant": "sword",
        "frame_index": 48,
        "phase": "active",
        "keypoints": {
            "nose": [0.50, 0.20],
            "neck": [0.50, 0.31],
            "right_shoulder": [0.58, 0.35],
            "right_elbow": [0.64, 0.48],
            "right_wrist": [0.68, 0.60],
            "left_shoulder": [0.42, 0.35],
            "left_elbow": [0.36, 0.48],
            "left_wrist": [0.32, 0.60],
            "right_hip": [0.55, 0.57],
            "right_knee": [0.60, 0.74],
            "right_ankle": [0.63, 0.89],
            "left_hip": [0.45, 0.57],
            "left_knee": [0.40, 0.74],
            "left_ankle": [0.37, 0.89],
        },
    }

    base = _render_control_frame(args, frame, source_index=48, pose_count=120)
    args.weapon_guide = "sword"
    with_sword = _render_control_frame(args, frame, source_index=48, pose_count=120)

    assert with_sword.tobytes() != base.tobytes()


def _minimal_args() -> SimpleNamespace:
    return SimpleNamespace(
        unet="wan.safetensors",
        weight_dtype="fp8_e4m3fn",
        shift=8.0,
        clip="clip.safetensors",
        positive="positive",
        negative="negative",
        vae="vae.safetensors",
        clip_vision="clip_vision.safetensors",
        width=512,
        height=512,
        length=5,
        seed=1,
        steps=1,
        cfg=1.0,
        sampler="uni_pc",
        scheduler="simple",
        fps=8,
        vace_strength=1.0,
        pose_render_style="wan_balanced",
        weapon_guide="none",
    )
