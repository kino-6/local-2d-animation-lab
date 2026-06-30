from __future__ import annotations

import argparse
import html
import json
import os
import shutil
from pathlib import Path
from typing import Any

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a game-ready sprite pack showcase bundle.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    bundle = export_showcase(args.manifest, args.output_dir, clean=args.clean)
    print(json.dumps(bundle, indent=2, ensure_ascii=False))


def export_showcase(
    manifest_path: Path,
    output_dir: Path | None = None,
    clean: bool = True,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    pack_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("route") != "character_sprite_asset_pack":
        raise ValueError(f"unsupported manifest route: {manifest.get('route')}")

    output_dir = output_dir or pack_dir / "export" / "game_ready_showcase"
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    atlas = _build_atlas(pack_dir, manifest)
    deliverables = _build_deliverables(pack_dir, output_dir, manifest, atlas)
    _write_json(output_dir / "atlas.json", atlas)
    _write_json(output_dir / "deliverables.json", deliverables)
    (output_dir / "README.md").write_text(_readme(deliverables), encoding="utf-8", newline="\n")
    (output_dir / "index.html").write_text(_html(deliverables), encoding="utf-8", newline="\n")
    return {
        "export_dir": _display_path(output_dir),
        "index_html": _display_path(output_dir / "index.html"),
        "deliverables": _display_path(output_dir / "deliverables.json"),
        "atlas": _display_path(output_dir / "atlas.json"),
        "production_ready": bool(manifest.get("production_ready")),
        "action_count": len(manifest.get("actions", {})),
    }


def _build_atlas(pack_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    actions = {}
    for action, info in manifest.get("actions", {}).items():
        frame_size = info.get("frame_size", {})
        frame_width = int(frame_size.get("width", 0))
        frame_height = int(frame_size.get("height", 0))
        spritesheet_rel = info.get("spritesheet", "")
        spritesheet_path = pack_dir / spritesheet_rel
        sheet_width = frame_width * max(1, len(info.get("frames", [])))
        sheet_height = frame_height
        if spritesheet_path.exists():
            with Image.open(spritesheet_path) as image:
                sheet_width, sheet_height = image.size
        columns = max(1, sheet_width // max(1, frame_width))
        frames = []
        for index, frame in enumerate(info.get("frames", [])):
            frames.append(
                {
                    "name": Path(frame).name,
                    "index": index,
                    "path": frame,
                    "x": (index % columns) * frame_width,
                    "y": (index // columns) * frame_height,
                    "width": frame_width,
                    "height": frame_height,
                    "duration_ms": round(1000 / float(info.get("runtime", {}).get("fps", 8.0))),
                }
            )
        actions[action] = {
            "spritesheet": spritesheet_rel,
            "frame_count": len(frames),
            "frame_size": {"width": frame_width, "height": frame_height},
            "columns": columns,
            "loop": bool(info.get("runtime", {}).get("loop", True)),
            "fps": float(info.get("runtime", {}).get("fps", 8.0)),
            "origin": info.get("runtime", {}).get("origin", {}),
            "collision_box": info.get("runtime", {}).get("collision_box", {}),
            "hit_frames": info.get("runtime", {}).get("hit_frames", []),
            "frames": frames,
        }
    return {
        "route": "sprite_pack_atlas",
        "source_manifest": "manifest.json",
        "asset_name": manifest.get("asset_name", "sprite_pack"),
        "production_ready": bool(manifest.get("production_ready")),
        "actions": actions,
    }


def _build_deliverables(
    pack_dir: Path,
    output_dir: Path,
    manifest: dict[str, Any],
    atlas: dict[str, Any],
) -> dict[str, Any]:
    actions = {}
    for action, info in manifest.get("actions", {}).items():
        actions[action] = {
            "frame_count": info.get("frame_count"),
            "frame_size": info.get("frame_size"),
            "fps": info.get("runtime", {}).get("fps"),
            "loop": info.get("runtime", {}).get("loop"),
            "spritesheet_png": _relative_from(output_dir, pack_dir / info.get("spritesheet", "")),
            "preview_gif": _relative_from(output_dir, pack_dir / info.get("preview_gif", "")),
            "preview_webp": _relative_from(output_dir, pack_dir / info.get("preview_webp", "")),
            "contact_sheet_png": _relative_from(output_dir, pack_dir / info.get("contact_sheet", "")),
            "frames_dir": _relative_from(output_dir, pack_dir / "actions" / action / "frames"),
            "origin": atlas["actions"][action]["origin"],
            "collision_box": atlas["actions"][action]["collision_box"],
            "hit_frames": atlas["actions"][action]["hit_frames"],
        }
    review_dir = pack_dir / "pack_review"
    return {
        "route": "game_ready_sprite_pack_delivery",
        "asset_name": manifest.get("asset_name", "sprite_pack"),
        "production_ready": bool(manifest.get("production_ready")),
        "source_manifest": _relative_from(output_dir, pack_dir / "manifest.json"),
        "runtime_manifest": _relative_from(output_dir, pack_dir / "runtime_manifest.json"),
        "visual_gate_report": _relative_from(output_dir, review_dir / "visual_gate_report.json"),
        "all_actions_contact_sheet": _relative_from(output_dir, review_dir / "all_actions_contact_sheet_fullres.png"),
        "atlas_json": "atlas.json",
        "actions": actions,
        "engine_notes": {
            "godot": "Use atlas.json or runtime_manifest.json with AnimatedSprite2D/SpriteFrames import tooling.",
            "unity": "Use per-action spritesheet_png with frame_size and atlas frame rectangles.",
            "aseprite": "Open per-action spritesheet_png or contact_sheet_png for manual review/editing.",
        },
    }


def _html(deliverables: dict[str, Any]) -> str:
    actions = deliverables["actions"]
    first_action = next(iter(actions), "")
    action_buttons = "\n".join(
        f'<button class="action-button" data-action="{html.escape(action)}">{html.escape(action)}</button>'
        for action in actions
    )
    action_data = json.dumps(actions, ensure_ascii=False)
    title = html.escape(str(deliverables.get("asset_name", "Sprite Pack")))
    ready = "production ready" if deliverables.get("production_ready") else "needs review"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #202124;
      --muted: #666b73;
      --line: #d8dde5;
      --panel: #f7f8fa;
      --accent: #256f6c;
      --bg: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      letter-spacing: 0;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 22px;
      border-bottom: 1px solid var(--line);
      background: #fbfbfc;
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    h1 {{
      margin: 0;
      font-size: 18px;
      font-weight: 700;
    }}
    .status {{
      font-size: 13px;
      color: var(--accent);
      font-weight: 700;
      white-space: nowrap;
    }}
    main {{
      display: grid;
      grid-template-columns: 240px minmax(0, 1fr);
      min-height: calc(100vh - 58px);
    }}
    nav {{
      border-right: 1px solid var(--line);
      background: var(--panel);
      padding: 14px;
    }}
    .action-button {{
      display: block;
      width: 100%;
      padding: 10px 12px;
      border: 1px solid transparent;
      background: transparent;
      color: var(--ink);
      text-align: left;
      font-size: 14px;
      cursor: pointer;
      border-radius: 6px;
    }}
    .action-button.active {{
      background: #e9f2f1;
      border-color: #bed7d5;
      color: #15514f;
      font-weight: 700;
    }}
    .workspace {{
      padding: 18px 22px 28px;
      display: grid;
      grid-template-columns: minmax(300px, 440px) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }}
    .preview {{
      border: 1px solid var(--line);
      background:
        linear-gradient(45deg, #f3f5f7 25%, transparent 25%),
        linear-gradient(-45deg, #f3f5f7 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #f3f5f7 75%),
        linear-gradient(-45deg, transparent 75%, #f3f5f7 75%);
      background-size: 24px 24px;
      background-position: 0 0, 0 12px, 12px -12px, -12px 0;
      min-height: 440px;
      display: grid;
      place-items: center;
      overflow: hidden;
    }}
    .preview img {{
      width: min(80%, 360px);
      height: auto;
      image-rendering: auto;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
      font-size: 13px;
    }}
    .meta div {{
      border-bottom: 1px solid var(--line);
      padding: 8px 0;
    }}
    .meta span {{
      display: block;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .links {{
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .links a {{
      color: #15514f;
      border: 1px solid #bed7d5;
      background: #f1f7f6;
      padding: 8px 10px;
      border-radius: 6px;
      text-decoration: none;
      font-size: 13px;
    }}
    .sheet {{
      border: 1px solid var(--line);
      overflow: auto;
      max-height: calc(100vh - 112px);
      background: #f5f5f5;
    }}
    .sheet img {{
      display: block;
      max-width: none;
      width: 100%;
      min-width: 760px;
      height: auto;
    }}
    @media (max-width: 860px) {{
      main {{ grid-template-columns: 1fr; }}
      nav {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .workspace {{ grid-template-columns: 1fr; padding: 14px; }}
      .preview {{ min-height: 320px; }}
      header {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="status">{html.escape(ready)}</div>
  </header>
  <main>
    <nav>{action_buttons}</nav>
    <section class="workspace">
      <div>
        <div class="preview"><img id="preview" alt="action preview"></div>
        <div class="meta">
          <div><span>Action</span><strong id="actionName"></strong></div>
          <div><span>Frames</span><strong id="frameCount"></strong></div>
          <div><span>Frame Size</span><strong id="frameSize"></strong></div>
          <div><span>Playback</span><strong id="playback"></strong></div>
        </div>
        <div class="links">
          <a id="gifLink">GIF</a>
          <a id="webpLink">WebP</a>
          <a id="sheetLink">Spritesheet</a>
          <a href="atlas.json">Atlas JSON</a>
          <a href="deliverables.json">Deliverables JSON</a>
        </div>
      </div>
      <div class="sheet"><img id="sheet" alt="action spritesheet"></div>
    </section>
  </main>
  <script>
    const actions = {action_data};
    const initialAction = {json.dumps(first_action)};
    const buttons = Array.from(document.querySelectorAll(".action-button"));
    function setAction(name) {{
      const data = actions[name];
      if (!data) return;
      document.getElementById("preview").src = data.preview_webp || data.preview_gif;
      document.getElementById("sheet").src = data.spritesheet_png;
      document.getElementById("actionName").textContent = name;
      document.getElementById("frameCount").textContent = data.frame_count;
      document.getElementById("frameSize").textContent = `${{data.frame_size.width}} x ${{data.frame_size.height}}`;
      document.getElementById("playback").textContent = `${{data.fps}} fps / ${{data.loop ? "loop" : "one-shot"}}`;
      document.getElementById("gifLink").href = data.preview_gif;
      document.getElementById("webpLink").href = data.preview_webp;
      document.getElementById("sheetLink").href = data.spritesheet_png;
      buttons.forEach((button) => button.classList.toggle("active", button.dataset.action === name));
    }}
    buttons.forEach((button) => button.addEventListener("click", () => setAction(button.dataset.action)));
    setAction(initialAction);
  </script>
</body>
</html>
"""


def _readme(deliverables: dict[str, Any]) -> str:
    lines = [
        f"# {deliverables.get('asset_name', 'Sprite Pack')} Delivery",
        "",
        f"- production_ready: `{str(deliverables.get('production_ready')).lower()}`",
        f"- source_manifest: `{deliverables.get('source_manifest')}`",
        f"- atlas_json: `{deliverables.get('atlas_json')}`",
        f"- visual_gate_report: `{deliverables.get('visual_gate_report')}`",
        "",
        "## Actions",
        "",
    ]
    for action, info in deliverables.get("actions", {}).items():
        lines.extend(
            [
                f"### {action}",
                "",
                f"- frames: `{info['frame_count']}`",
                f"- size: `{info['frame_size']['width']}x{info['frame_size']['height']}`",
                f"- fps: `{info['fps']}`",
                f"- loop: `{str(info['loop']).lower()}`",
                f"- spritesheet: `{info['spritesheet_png']}`",
                f"- preview: `{info['preview_webp']}`",
                "",
            ]
        )
    return "\n".join(lines)


def _relative_from(base: Path, target: Path) -> str:
    return os.path.relpath(target.resolve(), start=base.resolve()).replace("\\", "/")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


if __name__ == "__main__":
    main()
