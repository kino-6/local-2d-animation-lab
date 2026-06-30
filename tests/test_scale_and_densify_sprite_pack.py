from __future__ import annotations

import json
import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scale_and_densify_sprite_pack.py"
_SPEC = importlib.util.spec_from_file_location("scale_and_densify_sprite_pack", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
scale_and_densify_pack = _MODULE.scale_and_densify_pack


def test_scale_and_densify_pack_increases_size_and_frame_count(tmp_path: Path) -> None:
    source = tmp_path / "source_pack"
    output = tmp_path / "output_pack"
    _make_pack(source)

    manifest = scale_and_densify_pack(
        manifest_path=source / "manifest.json",
        output_dir=output,
        frame_size=(96, 128),
        inbetweens=1,
        asset_name="scaled_test_pack",
    )

    assert manifest["asset_name"] == "scaled_test_pack"
    assert manifest["actions"]["idle"]["frame_count"] == 4
    assert manifest["actions"]["hurt"]["frame_count"] == 5
    assert manifest["actions"]["idle"]["runtime"]["fps"] == 12.0
    assert manifest["actions"]["hurt"]["runtime"]["fps"] == 10.0

    for action in ["idle", "hurt"]:
        frame_paths = [output / rel for rel in manifest["actions"][action]["frames"]]
        assert {Image.open(path).size for path in frame_paths} == {(96, 128)}
        assert (output / manifest["actions"][action]["preview_webp"]).exists()
        assert (output / manifest["actions"][action]["spritesheet"]).exists()

    assert (output / "pack_review" / "all_actions_contact_sheet_fullres.png").exists()
    written = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert written["actions"]["hurt"]["frame_count"] == 5


def _make_pack(root: Path) -> None:
    actions = {}
    for action, count, loop, fps in [("idle", 2, True, 6), ("hurt", 3, False, 6)]:
        action_dir = root / "actions" / action
        frames_dir = action_dir / "frames"
        frames_dir.mkdir(parents=True)
        frames = []
        for index in range(count):
            path = frames_dir / f"{action}_{index:03d}.png"
            _make_frame(path, offset=index * 3)
            frames.append(f"actions/{action}/frames/{path.name}")
        actions[action] = {
            "action": action,
            "frame_count": count,
            "frame_size": {"width": 48, "height": 64},
            "production_ready": True,
            "status": "production_ready",
            "phase_names": [f"{action}_{index}" for index in range(count)],
            "frames": frames,
            "spritesheet": f"actions/{action}/spritesheet.png",
            "preview_gif": f"actions/{action}/preview.gif",
            "contact_sheet": f"actions/{action}/contact_sheet.png",
            "production_ready_report": f"actions/{action}/production_ready_report.json",
            "runtime": {
                "fps": fps,
                "loop": loop,
                "source_frame_count": count,
                "playback_frame_count": count,
                "playback_frame_indices": list(range(count)),
                "origin": {"x": 24, "y": 60},
                "visible_bbox": {"x": 14, "y": 8, "width": 20, "height": 52},
                "collision_box": {"x": 16, "y": 12, "width": 12, "height": 44},
                "hit_frames": [],
            },
        }
    manifest = {
        "route": "character_sprite_asset_pack",
        "asset_kind": "2d_game_sprite_asset_pack",
        "asset_name": "source_test_pack",
        "actions": actions,
        "pack_review": {},
        "production_gate": {"production_ready": True},
        "production_ready": True,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _make_frame(path: Path, offset: int) -> None:
    image = Image.new("RGBA", (48, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((18 + offset, 8, 30 + offset, 20), fill=(240, 220, 200, 255))
    draw.rectangle((16 + offset, 20, 32 + offset, 52), fill=(30, 30, 38, 255))
    draw.rectangle((18 + offset, 52, 24 + offset, 60), fill=(30, 30, 38, 255))
    draw.rectangle((26 + offset, 52, 32 + offset, 60), fill=(30, 30, 38, 255))
    image.save(path)
