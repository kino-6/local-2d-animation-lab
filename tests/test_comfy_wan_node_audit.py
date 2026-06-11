from __future__ import annotations

import importlib.util
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_comfy_wan_nodes.py"
_SPEC = importlib.util.spec_from_file_location("audit_comfy_wan_nodes", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

build_audit = _MODULE.build_audit


def test_audit_prefers_wan22_fun_control_when_ref_and_control_are_available() -> None:
    object_info = {
        "WanAnimateToVideo": {
            "input": {"optional": {"reference_image": ["IMAGE", {}], "pose_video": ["IMAGE", {}]}}
        },
        "WanFirstLastFrameToVideo": {
            "input": {"optional": {"start_image": ["IMAGE", {}], "end_image": ["IMAGE", {}]}}
        },
        "WanFunControlToVideo": {
            "input": {"optional": {"start_image": ["IMAGE", {}], "control_video": ["IMAGE", {}]}}
        },
        "Wan22FunControlToVideo": {
            "input": {"optional": {"ref_image": ["IMAGE", {}], "control_video": ["IMAGE", {}]}}
        },
        "UNETLoader": {
            "input": {
                "required": {
                    "unet_name": [["Wan2.1-Fun-1.3B-Control.safetensors", "wan2.1_i2v_480p_14B_fp16.safetensors"]]
                }
            }
        },
    }

    audit = build_audit(object_info, pattern="wan")

    summary = audit["capability_summary"]
    assert summary["wan_animate_has_pose_video"] is True
    assert summary["wan_animate_has_end_image"] is False
    assert summary["wan22_fun_control_has_ref_and_control"] is True
    assert summary["wan_fun_control_unet_available"] is True
    assert summary["recommended_next_route"].startswith("Try Wan22FunControlToVideo")


def test_audit_falls_back_to_animate_when_no_fun_control_route_exists() -> None:
    object_info = {
        "WanAnimateToVideo": {
            "input": {
                "optional": {
                    "reference_image": ["IMAGE", {}],
                    "pose_video": ["IMAGE", {}],
                    "character_mask": ["MASK", {}],
                }
            }
        }
    }

    audit = build_audit(object_info, pattern="wan")

    summary = audit["capability_summary"]
    assert summary["wan_animate_has_character_mask"] is True
    assert summary["wan_fun_control_has_start_and_control"] is False
    assert summary["recommended_next_route"].startswith("Stay on WanAnimateToVideo")


def test_audit_recommends_install_when_fun_nodes_exist_without_fun_unet() -> None:
    object_info = {
        "WanAnimateToVideo": {
            "input": {"optional": {"reference_image": ["IMAGE", {}], "pose_video": ["IMAGE", {}]}}
        },
        "WanFunControlToVideo": {
            "input": {"optional": {"start_image": ["IMAGE", {}], "control_video": ["IMAGE", {}]}}
        },
        "Wan22FunControlToVideo": {
            "input": {"optional": {"ref_image": ["IMAGE", {}], "control_video": ["IMAGE", {}]}}
        },
        "UNETLoader": {"input": {"required": {"unet_name": [["wan2.1_i2v_480p_14B_fp16.safetensors"]]}}},
    }

    audit = build_audit(object_info, pattern="wan")

    summary = audit["capability_summary"]
    assert summary["wan_fun_control_unet_available"] is False
    assert summary["recommended_next_route"].startswith("Install a Wan Fun-Control")


def test_audit_prefers_vace_when_vace_unet_is_available() -> None:
    object_info = {
        "WanAnimateToVideo": {
            "input": {"optional": {"reference_image": ["IMAGE", {}], "pose_video": ["IMAGE", {}]}}
        },
        "WanFunControlToVideo": {
            "input": {"optional": {"start_image": ["IMAGE", {}], "control_video": ["IMAGE", {}]}}
        },
        "Wan22FunControlToVideo": {
            "input": {"optional": {"ref_image": ["IMAGE", {}], "control_video": ["IMAGE", {}]}}
        },
        "WanVaceToVideo": {
            "input": {"optional": {"reference_image": ["IMAGE", {}], "control_video": ["IMAGE", {}]}}
        },
        "UNETLoader": {
            "input": {
                "required": {
                    "unet_name": [
                        [
                            "Wan2.1-Fun-1.3B-Control.safetensors",
                            "wan2.1_vace_1.3B_fp16.safetensors",
                        ]
                    ]
                }
            }
        },
    }

    audit = build_audit(object_info, pattern="wan")

    summary = audit["capability_summary"]
    assert summary["wan_vace_has_reference_and_control"] is True
    assert summary["wan_vace_unet_available"] is True
    assert summary["recommended_next_route"].startswith("Try WanVaceToVideo")
