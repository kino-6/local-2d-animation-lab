from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "birefnet_foreground_masks.py"
_SPEC = importlib.util.spec_from_file_location("birefnet_foreground_masks", _SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

_workflow = _MODULE._workflow
_composite = _MODULE._composite
_prepare_mask = _MODULE._prepare_mask
_mask_gate = _MODULE._mask_gate
_mask_structure = _MODULE._mask_structure


def test_workflow_loads_birefnet_once_and_saves_each_mask() -> None:
    workflow, save_nodes = _workflow("birefnet.safetensors", ["a.png", "b.png"])

    assert workflow["1"]["class_type"] == "LoadBackgroundRemovalModel"
    assert workflow["1"]["inputs"]["bg_removal_name"] == "birefnet.safetensors"
    assert save_nodes == ["13", "17"]
    assert workflow["11"]["class_type"] == "RemoveBackground"
    assert workflow["15"]["inputs"]["bg_removal_model"] == ["1", 0]


def test_composite_keeps_foreground_and_whitens_background() -> None:
    image = Image.new("RGBA", (20, 20), (40, 90, 180, 255))
    mask = Image.new("L", (20, 20), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((6, 4, 13, 16), fill=255)

    result = _composite(image, mask, "white").convert("RGB")

    assert result.getpixel((0, 0)) == (255, 255, 255)
    assert result.getpixel((10, 10)) == (40, 90, 180)


def test_prepare_mask_can_grow_subject_edges() -> None:
    mask = Image.new("L", (11, 11), 0)
    mask.putpixel((5, 5), 255)

    grown = _prepare_mask(mask, grow=1, blur=0)

    assert grown.getpixel((4, 5)) == 255
    assert grown.getpixel((5, 4)) == 255


def test_mask_gate_flags_unusable_coverage_and_large_temporal_jump() -> None:
    normal = {
        "foreground_bbox_fill": 0.55,
        "lower_body_max_width_ratio": 0.18,
        "lower_body_mean_width_ratio": 0.1,
    }
    assert _mask_gate(0.01, 0.0, 0, normal) == "retake_foreground_too_small"
    assert _mask_gate(0.80, 0.0, 0, normal) == "retake_foreground_too_large"
    assert _mask_gate(0.20, 0.40, 1, normal) == "review_mask_temporal_jump"
    assert _mask_gate(0.20, 0.10, 1, normal) == "mask_ok"


def test_mask_gate_flags_sparse_or_wide_foreground_for_review() -> None:
    sparse = {
        "foreground_bbox_fill": 0.32,
        "lower_body_max_width_ratio": 0.18,
        "lower_body_mean_width_ratio": 0.1,
    }
    wide = {
        "foreground_bbox_fill": 0.55,
        "lower_body_max_width_ratio": 0.36,
        "lower_body_mean_width_ratio": 0.18,
    }

    assert _mask_gate(0.20, 0.0, 0, sparse) == "review_sparse_foreground_bbox"
    assert _mask_gate(0.20, 0.0, 0, wide) == "review_lower_body_silhouette_wide"


def test_mask_structure_reports_bbox_fill_and_lower_body_width() -> None:
    mask = Image.new("L", (100, 100), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((40, 10, 55, 50), fill=255)
    draw.rectangle((25, 51, 75, 90), fill=255)

    structure = _mask_structure(mask)

    assert 0.0 < structure["foreground_bbox_fill"] < 1.0
    assert structure["lower_body_max_width_ratio"] > 0.4
