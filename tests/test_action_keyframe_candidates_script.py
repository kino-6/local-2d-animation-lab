from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageDraw


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_action_keyframe_candidates.py"
_SPEC = importlib.util.spec_from_file_location("generate_action_keyframe_candidates", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_action_candidate_prompt_templates_cover_run_and_hit() -> None:
    run = _MODULE.ACTION_CANDIDATES["run"][0].positive_template.format(identity_traits="black yellow armor")
    hit_light = _MODULE.ACTION_CANDIDATES["hit_light"][0].positive_template.format(identity_traits="black yellow armor")
    hit = _MODULE.ACTION_CANDIDATES["hit_heavy"][0].positive_template.format(identity_traits="black yellow armor")

    assert "conservative running stride" in run
    assert "light hit reaction" in hit_light
    assert "heavy damage recoil" in hit
    assert "black yellow armor" in run
    assert "black yellow armor" in hit_light
    assert "black yellow armor" in hit


def test_action_pose_images_are_distinct() -> None:
    run = _MODULE._pose_image("run_low_stride", 256, 256)
    hit = _MODULE._pose_image("hit_heavy_compact_recoil", 256, 256)

    assert run.size == (256, 256)
    assert hit.size == (256, 256)
    assert run.tobytes() != hit.tobytes()


def test_action_catalog_includes_hit_light() -> None:
    assert "hit_light" in _MODULE.ACTION_CANDIDATES


def test_img2img_endpoint_workflow_uses_source_latent() -> None:
    args = argparse.Namespace(
        checkpoint="novaOrangeXL_v120.safetensors",
        controlnet="SDXL\\OpenPoseXL2.safetensors",
        width=1024,
        height=1024,
        steps=12,
        cfg=4.8,
        sampler="dpmpp_2m",
        scheduler="karras",
        controlnet_strength=0.62,
        denoise=0.42,
        source_edit_region="full",
    )

    workflow = _MODULE._workflow(
        args,
        "positive",
        "negative",
        123,
        "pose.png",
        "run",
        "source.png",
    )

    assert workflow["5"]["inputs"]["latent_image"] == ["13", 0]
    assert workflow["5"]["inputs"]["denoise"] == 0.42
    assert workflow["11"]["inputs"]["image"] == "source.png"
    assert workflow["13"]["class_type"] == "VAEEncode"


def test_lower_body_endpoint_workflow_uses_inpaint_mask() -> None:
    args = argparse.Namespace(
        checkpoint="novaOrangeXL_v120.safetensors",
        controlnet="SDXL\\OpenPoseXL2.safetensors",
        width=1024,
        height=1024,
        steps=12,
        cfg=4.8,
        sampler="dpmpp_2m",
        scheduler="karras",
        controlnet_strength=0.62,
        denoise=0.58,
        source_edit_region="lower_body",
    )

    workflow = _MODULE._workflow(
        args,
        "positive",
        "negative",
        123,
        "pose.png",
        "run",
        "source.png",
        "lower_body_mask.png",
    )

    assert workflow["14"]["class_type"] == "LoadImageMask"
    assert workflow["14"]["inputs"]["image"] == "lower_body_mask.png"
    assert workflow["15"]["class_type"] == "VAEEncodeForInpaint"
    assert workflow["15"]["inputs"]["mask"] == ["14", 0]
    assert workflow["5"]["inputs"]["latent_image"] == ["15", 0]
    assert workflow["16"]["class_type"] == "ImageCompositeMasked"
    assert workflow["7"]["inputs"]["images"] == ["16", 0]


def test_lower_body_edit_mask_ignores_plain_background_panel(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    mask_path = tmp_path / "mask.png"
    image = Image.new("RGB", (128, 128), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((42, 8, 86, 120), fill=(232, 230, 210))
    draw.rectangle((54, 26, 74, 68), fill=(20, 25, 28))
    draw.rectangle((50, 66, 60, 112), fill=(12, 18, 22))
    draw.rectangle((68, 66, 78, 112), fill=(250, 210, 15))
    image.save(source)

    _MODULE._make_lower_body_edit_mask(source, mask_path)

    mask = Image.open(mask_path).convert("L")
    bbox = mask.getbbox()
    assert bbox is not None
    left, top, right, bottom = bbox
    assert left > 30
    assert right < 116
    assert top > 45
    assert bottom > 105
