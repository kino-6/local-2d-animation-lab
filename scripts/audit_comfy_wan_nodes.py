from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any


INTERESTING_NODES = (
    "WanAnimateToVideo",
    "WanFirstLastFrameToVideo",
    "WanFunControlToVideo",
    "Wan22FunControlToVideo",
    "WanFunInpaintToVideo",
    "WanImageToVideo",
    "WanVaceToVideo",
    "WanPhantomSubjectToVideo",
    "WanTrackToVideo",
    "WanMoveTrackToVideo",
    "TrimVideoLatent",
    "ReplaceVideoLatentFrames",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit local ComfyUI Wan video node inputs.")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--output-root", type=Path, default=Path("outputs_comfy_audit"))
    parser.add_argument("--pattern", default=r"wan|video|control|inpaint|animate")
    args = parser.parse_args()

    object_info = _fetch_object_info(args.comfy_url.rstrip("/"))
    audit = build_audit(object_info, pattern=args.pattern)

    run_dir = args.output_root / time.strftime("wan_node_audit_%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    audit_path = run_dir / "wan_node_audit.json"
    summary_path = run_dir / "wan_node_audit_summary.md"
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_path.write_text(render_markdown_summary(audit), encoding="utf-8")

    print(summary_path)
    print(json.dumps(audit["capability_summary"], indent=2, ensure_ascii=False))


def build_audit(object_info: dict[str, Any], *, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    matched_nodes = sorted(name for name in object_info if regex.search(name))
    interesting = {name: summarize_node(object_info.get(name)) for name in INTERESTING_NODES}
    available_unets = summarize_available_unets(object_info)
    return {
        "interesting_nodes": interesting,
        "available_unets": available_unets,
        "matched_node_count": len(matched_nodes),
        "matched_nodes": matched_nodes,
        "capability_summary": summarize_capabilities(interesting, available_unets=available_unets),
    }


def summarize_node(node_info: dict[str, Any] | None) -> dict[str, Any]:
    if not node_info:
        return {"available": False, "required": [], "optional": []}
    inputs = node_info.get("input", {})
    return {
        "available": True,
        "required": sorted(inputs.get("required", {}).keys()),
        "optional": sorted(inputs.get("optional", {}).keys()),
    }


def summarize_available_unets(object_info: dict[str, Any]) -> list[str]:
    unet_info = object_info.get("UNETLoader", {}).get("input", {}).get("required", {}).get("unet_name")
    if not unet_info or not isinstance(unet_info, list) or not unet_info:
        return []
    names = unet_info[0]
    return sorted(str(name) for name in names) if isinstance(names, list) else []


def summarize_capabilities(nodes: dict[str, dict[str, Any]], *, available_unets: list[str]) -> dict[str, Any]:
    animate = nodes["WanAnimateToVideo"]
    fun_control = nodes["WanFunControlToVideo"]
    wan22_fun_control = nodes["Wan22FunControlToVideo"]
    first_last = nodes["WanFirstLastFrameToVideo"]
    vace = nodes["WanVaceToVideo"]
    phantom = nodes["WanPhantomSubjectToVideo"]
    track = nodes["WanTrackToVideo"]
    move_track = nodes["WanMoveTrackToVideo"]

    animate_optional = set(animate.get("optional", []))
    fun_optional = set(fun_control.get("optional", []))
    wan22_optional = set(wan22_fun_control.get("optional", []))
    first_last_optional = set(first_last.get("optional", []))
    vace_optional = set(vace.get("optional", []))
    phantom_optional = set(phantom.get("optional", []))
    track_required = set(track.get("required", []))
    move_track_optional = set(move_track.get("optional", []))

    return {
        "wan_animate_has_pose_video": "pose_video" in animate_optional,
        "wan_animate_has_reference_image": "reference_image" in animate_optional,
        "wan_animate_has_character_mask": "character_mask" in animate_optional,
        "wan_animate_has_end_image": "end_image" in animate_optional,
        "wan_first_last_has_start_end": {"start_image", "end_image"}.issubset(first_last_optional),
        "wan_fun_control_has_start_and_control": {"start_image", "control_video"}.issubset(fun_optional),
        "wan22_fun_control_has_ref_and_control": {"ref_image", "control_video"}.issubset(wan22_optional),
        "wan_vace_has_reference_and_control": {"reference_image", "control_video"}.issubset(vace_optional),
        "wan_phantom_has_subject_images": "images" in phantom_optional,
        "wan_track_has_start_and_tracks": {"start_image", "tracks"}.issubset(track_required),
        "wan_move_track_has_start_and_tracks": "tracks" in move_track_optional,
        "wan_fun_control_unet_available": any(
            "wan" in name.lower() and "fun" in name.lower() and "control" in name.lower() for name in available_unets
        ),
        "wan_vace_unet_available": any("wan" in name.lower() and "vace" in name.lower() for name in available_unets),
        "recommended_next_route": _recommended_route(
            animate_optional=animate_optional,
            fun_optional=fun_optional,
            wan22_optional=wan22_optional,
            vace_optional=vace_optional,
            available_unets=available_unets,
        ),
    }


def _recommended_route(
    *,
    animate_optional: set[str],
    fun_optional: set[str],
    wan22_optional: set[str],
    vace_optional: set[str],
    available_unets: list[str],
) -> str:
    has_fun_control_unet = any(
        "wan" in name.lower() and "fun" in name.lower() and "control" in name.lower() for name in available_unets
    )
    if ({"ref_image", "control_video"}.issubset(wan22_optional) or {"start_image", "control_video"}.issubset(fun_optional)) and not has_fun_control_unet:
        return "Install a Wan Fun-Control diffusion model before judging FunControl routes."
    has_vace_unet = any("wan" in name.lower() and "vace" in name.lower() for name in available_unets)
    if {"reference_image", "control_video"}.issubset(vace_optional) and has_vace_unet:
        return "Try WanVaceToVideo for reference-image plus control-video subject/motion split."
    if {"ref_image", "control_video"}.issubset(wan22_optional):
        return "Try Wan22FunControlToVideo for reference-image plus control-video comparison."
    if {"start_image", "control_video"}.issubset(fun_optional):
        return "Try WanFunControlToVideo for start-image plus control-video comparison."
    if {"reference_image", "pose_video"}.issubset(animate_optional):
        return "Stay on WanAnimateToVideo; no stronger local control route was detected."
    return "No compatible Wan pose/control route was detected."


def render_markdown_summary(audit: dict[str, Any]) -> str:
    lines = [
        "# ComfyUI Wan Node Audit",
        "",
        "## Capability Summary",
        "",
    ]
    for key, value in audit["capability_summary"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Interesting Nodes", ""])
    for name, node in audit["interesting_nodes"].items():
        lines.append(f"### {name}")
        lines.append(f"- available: `{node['available']}`")
        lines.append(f"- required: `{', '.join(node['required']) if node['required'] else '-'}`")
        lines.append(f"- optional: `{', '.join(node['optional']) if node['optional'] else '-'}`")
        lines.append("")
    lines.extend(["## Available UNets", ""])
    for name in audit["available_unets"]:
        lines.append(f"- `{name}`")
    lines.append("")
    lines.append(f"Matched node count: `{audit['matched_node_count']}`")
    return "\n".join(lines) + "\n"


def _fetch_object_info(server_url: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{server_url}/object_info", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
