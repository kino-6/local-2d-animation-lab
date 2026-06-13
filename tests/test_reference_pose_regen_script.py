from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

from PIL import Image


def test_workflow_can_use_ipadapter_advanced_with_attention_mask() -> None:
    module = _load_module()
    args = _args(ipadapter_mode="advanced", ipadapter_attn_mask="upper_body")

    workflow = module._workflow(args, "source.png", "pose.png", 2, attn_mask_name="mask.png")

    assert workflow["14"]["class_type"] == "IPAdapterAdvanced"
    inputs = workflow["14"]["inputs"]
    assert inputs["weight_type"] == "composition precise"
    assert inputs["combine_embeds"] == "average"
    assert inputs["embeds_scaling"] == "K+mean(V) w/ C penalty"
    assert inputs["attn_mask"] == ["16", 0]
    assert workflow["15"]["class_type"] == "LoadImage"
    assert workflow["15"]["inputs"]["image"] == "mask.png"
    assert workflow["16"]["class_type"] == "ImageToMask"
    assert workflow["10"]["inputs"]["model"] == ["14", 0]


def test_workflow_keeps_simple_ipadapter_baseline() -> None:
    module = _load_module()
    args = _args(ipadapter_mode="simple", ipadapter_weight_type="style transfer")

    workflow = module._workflow(args, "source.png", "pose.png", 0)

    assert workflow["14"]["class_type"] == "IPAdapter"
    assert "combine_embeds" not in workflow["14"]["inputs"]
    assert "attn_mask" not in workflow["14"]["inputs"]


def test_ipadapter_attention_mask_generation_writes_soft_mask(tmp_path: Path) -> None:
    module = _load_module()
    path = module._make_ipadapter_attn_mask("upper_body", tmp_path / "mask.png", 128, 128)

    image = Image.open(path).convert("L")
    assert image.size == (128, 128)
    assert image.getpixel((64, 28)) > 0
    assert image.getpixel((64, 116)) == 0


def _args(**overrides):
    values = {
        "checkpoint": "novaOrangeXL_v120.safetensors",
        "controlnet": "SDXL\\OpenPoseXL2.safetensors",
        "ipadapter_mode": "advanced",
        "ipadapter_preset": "PLUS (high strength)",
        "ipadapter_weight": 0.45,
        "ipadapter_weight_type": "composition precise",
        "ipadapter_combine_embeds": "average",
        "ipadapter_embeds_scaling": "K+mean(V) w/ C penalty",
        "ipadapter_start": 0.0,
        "ipadapter_end": 0.60,
        "ipadapter_attn_mask": "none",
        "positive": "positive",
        "negative": "negative",
        "width": 768,
        "height": 768,
        "controlnet_strength": 0.92,
        "controlnet_end": 0.68,
        "seed": 123,
        "seed_step": 0,
        "steps": 18,
        "cfg": 4.6,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "denoise": 0.78,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _load_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "regenerate_pose_sequence_controlnet.py"
    spec = importlib.util.spec_from_file_location("regenerate_pose_sequence_controlnet", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
