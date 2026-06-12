from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


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
