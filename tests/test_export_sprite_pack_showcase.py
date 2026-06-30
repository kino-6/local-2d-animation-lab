from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_sprite_pack_showcase.py"
_SPEC = importlib.util.spec_from_file_location("export_sprite_pack_showcase", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
export_showcase = _MODULE.export_showcase


def test_export_showcase_writes_html_deliverables_and_atlas(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    _make_pack(pack)

    result = export_showcase(pack / "manifest.json", output_dir=pack / "export" / "showcase")

    export_dir = pack / "export" / "showcase"
    assert result["production_ready"] is True
    assert (export_dir / "index.html").exists()
    assert (export_dir / "deliverables.json").exists()
    assert (export_dir / "atlas.json").exists()
    assert (export_dir / "README.md").exists()

    html = (export_dir / "index.html").read_text(encoding="utf-8")
    assert "idle" in html
    assert "Atlas JSON" in html

    deliverables = json.loads((export_dir / "deliverables.json").read_text(encoding="utf-8"))
    assert deliverables["route"] == "game_ready_sprite_pack_delivery"
    assert deliverables["actions"]["idle"]["frame_count"] == 2
    assert deliverables["actions"]["idle"]["spritesheet_png"] == "../../actions/idle/spritesheet.png"

    atlas = json.loads((export_dir / "atlas.json").read_text(encoding="utf-8"))
    assert atlas["route"] == "sprite_pack_atlas"
    assert atlas["actions"]["idle"]["frames"][1]["x"] == 32
    assert atlas["actions"]["idle"]["frames"][1]["duration_ms"] == 167


def _make_pack(root: Path) -> None:
    frames_dir = root / "actions" / "idle" / "frames"
    frames_dir.mkdir(parents=True)
    frame_paths = []
    for index in range(2):
        frame = frames_dir / f"idle_{index:03d}.png"
        Image.new("RGBA", (32, 48), (20 + index * 20, 20, 24, 255)).save(frame)
        frame_paths.append(frame)
    sheet = Image.new("RGBA", (64, 48), (0, 0, 0, 0))
    for index, frame in enumerate(frame_paths):
        sheet.alpha_composite(Image.open(frame).convert("RGBA"), (index * 32, 0))
    sheet.save(root / "actions" / "idle" / "spritesheet.png")
    Image.new("RGBA", (32, 48), (30, 30, 36, 255)).save(root / "actions" / "idle" / "contact_sheet.png")
    Image.new("P", (32, 48)).save(root / "actions" / "idle" / "preview.gif")
    Image.new("RGB", (32, 48), (30, 30, 36)).save(root / "actions" / "idle" / "preview.webp")
    (root / "runtime_manifest.json").write_text('{"actions": {}}\n', encoding="utf-8")
    review = root / "pack_review"
    review.mkdir()
    (review / "visual_gate_report.json").write_text('{"production_ready": true}\n', encoding="utf-8")
    manifest = {
        "route": "character_sprite_asset_pack",
        "asset_name": "test_pack",
        "production_ready": True,
        "actions": {
            "idle": {
                "action": "idle",
                "frame_count": 2,
                "frame_size": {"width": 32, "height": 48},
                "frames": [f"actions/idle/frames/idle_{index:03d}.png" for index in range(2)],
                "spritesheet": "actions/idle/spritesheet.png",
                "preview_gif": "actions/idle/preview.gif",
                "preview_webp": "actions/idle/preview.webp",
                "contact_sheet": "actions/idle/contact_sheet.png",
                "runtime": {
                    "fps": 6,
                    "loop": True,
                    "origin": {"x": 16, "y": 46},
                    "collision_box": {"x": 10, "y": 8, "width": 12, "height": 38},
                    "hit_frames": [],
                },
            }
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
