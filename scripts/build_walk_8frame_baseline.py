from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

try:
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
    from natural_sprite_lab.postprocess.gif_preview import make_preview_gif
    from natural_sprite_lab.postprocess.spritesheet import make_contact_sheet, make_sprite_sheet


ROUTE = "walk_8frame_sideview_baseline"
ROUTE_STATUS = "baseline_not_production"
VISUAL_DECISION = "review_worthy_mvp_not_production"
DEFAULT_REFERENCE = Path("assets/reference/generated/anima_00013_sidecar_walk_start_source_20260614.png")
DEFAULT_OUTPUT = Path("outputs/adoptable/walk_8frame_sideview_baseline")
PHASE_NAMES = [
    "contact",
    "down",
    "passing",
    "up",
    "opposite_contact",
    "opposite_down",
    "opposite_passing",
    "opposite_up",
]
ACTION_SPEC = {
    "action": "walk",
    "direction": "right",
    "frame_count": 8,
    "view": "side",
    "loop": True,
    "background": "transparent",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic 8-frame side-view walk MVP package from one character reference."
    )
    parser.add_argument("--input", default=DEFAULT_REFERENCE, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--instruction", default="Create an 8-frame side-view walk cycle facing right.")
    parser.add_argument("--frame-width", default=512, type=int)
    parser.add_argument("--frame-height", default=512, type=int)
    parser.add_argument("--target-height", default=430, type=int)
    parser.add_argument("--fps", default=8, type=int)
    parser.add_argument("--background-threshold", default=88, type=int)
    parser.add_argument("--background-min-channel", default=205, type=int)
    parser.add_argument("--pad", default=24, type=int)
    parser.add_argument("--mirror-to-right", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--renderer",
        choices=["stylized_sprite_cycle", "cutout_synthetic_legs"],
        default="stylized_sprite_cycle",
    )
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    manifest = build_walk_8frame_baseline(
        source_path=args.input,
        output_dir=args.output_dir,
        instruction=args.instruction,
        frame_width=args.frame_width,
        frame_height=args.frame_height,
        target_height=args.target_height,
        fps=args.fps,
        background_threshold=args.background_threshold,
        background_min_channel=args.background_min_channel,
        pad=args.pad,
        mirror_to_right=args.mirror_to_right,
        renderer=args.renderer,
        clean=args.clean,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def build_walk_8frame_baseline(
    source_path: Path,
    output_dir: Path = DEFAULT_OUTPUT,
    instruction: str = "Create an 8-frame side-view walk cycle facing right.",
    frame_width: int = 512,
    frame_height: int = 512,
    target_height: int = 430,
    fps: int = 8,
    background_threshold: int = 88,
    background_min_channel: int = 205,
    pad: int = 24,
    mirror_to_right: bool = True,
    renderer: str = "stylized_sprite_cycle",
    clean: bool = True,
) -> dict[str, Any]:
    if ACTION_SPEC["frame_count"] != 8:
        raise RuntimeError("This route is fixed to exactly 8 frames.")
    if not source_path.exists():
        raise FileNotFoundError(f"Reference image not found: {source_path}")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cutout, cutout_report = _load_reference_cutout(
        source_path,
        background_threshold=background_threshold,
        background_min_channel=background_min_channel,
        pad=pad,
    )
    if mirror_to_right:
        cutout = ImageOps.mirror(cutout)
    cutout_report["mirror_to_direction_right"] = mirror_to_right
    fitted = _fit_cutout_to_canvas(cutout, frame_width, frame_height, target_height)
    palette = _derive_character_palette(fitted)
    walk_readability: dict[str, Any] | None = None
    if renderer == "stylized_sprite_cycle":
        frame_paths, walk_readability = _write_stylized_walk_frames(frames_dir, frame_width, frame_height, palette)
        motion_description = "stylized reference-derived 8-phase sprite walk cycle"
    elif renderer == "cutout_synthetic_legs":
        frame_paths = _write_walk_frames(fitted, frames_dir, palette)
        motion_description = "reference-preserving upper body plus deterministic 8-phase synthetic leg walk cycle"
    else:
        raise ValueError(f"Unsupported renderer: {renderer}")
    motion_metrics = _measure_motion(frame_paths)

    spritesheet = make_sprite_sheet(frame_paths, output_dir / "spritesheet.png", columns=8)
    preview = make_preview_gif(frame_paths, output_dir / "preview.gif", duration_ms=round(1000 / fps), loop=True)
    contact_sheet = make_contact_sheet(frame_paths, output_dir / "contact_sheet.png", columns=4)

    manifest = {
        "route": ROUTE,
        "route_status": ROUTE_STATUS,
        "asset_kind": "2d_game_sprite",
        "output_status": "adoptable_mvp_baseline",
        "instruction": instruction,
        "action_spec": ACTION_SPEC,
        "frame_count": 8,
        "fps": fps,
        "loop": True,
        "frame_size": {"width": frame_width, "height": frame_height},
        "pivot": {"x": 0.5, "y": 1.0},
        "background": "transparent",
        "source_reference": str(source_path).replace("\\", "/"),
        "outputs": {
            "frames": [str(path.relative_to(output_dir)).replace("\\", "/") for path in frame_paths],
            "spritesheet": str(spritesheet.relative_to(output_dir)).replace("\\", "/"),
            "preview_gif": str(preview.relative_to(output_dir)).replace("\\", "/"),
            "contact_sheet": str(contact_sheet.relative_to(output_dir)).replace("\\", "/"),
        },
        "method": {
            "type": "deterministic_cutout_baseline",
            "uses_comfyui": False,
            "uses_wan_video": False,
            "uses_120_frame_generation": False,
            "renderer": renderer,
            "motion": motion_description,
            "style_polish": {
                "limb_renderer": "tapered_filled_segments",
                "arm_model": "upper_lower_segments_with_elbow",
                "leg_model": "thigh_and_sock_segments_with_knee",
                "shoe_model": "compact_right_facing_heel_toe",
                "torso_hip_connection": "waist_block_under_sailor_top",
            },
            "palette": palette,
            "cutout": cutout_report,
        },
        "motion_metrics": motion_metrics,
        "walk_readability": walk_readability,
        "visual_review": {
            "agent_decision": VISUAL_DECISION,
            "notes": [
                "The first cutout-shift preview was not evaluation-worthy.",
                "The default renderer now uses a small deterministic skeleton with foot-lock metadata.",
                "The current shape pass uses tapered filled limb segments to reduce the stick-puppet look.",
                "This is a stylized reference-derived game sprite, not production art and not a faithful redraw of the source image.",
            ],
        },
        "quality_bar": {
            "exactly_one_character_expected": True,
            "canvas_size_consistent": True,
            "transparent_frames": True,
            "production_grade_art": False,
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "notes.md").write_text(_notes(manifest), encoding="utf-8")
    return manifest


def _load_reference_cutout(
    source_path: Path,
    background_threshold: int,
    background_min_channel: int,
    pad: int,
) -> tuple[Image.Image, dict[str, Any]]:
    image = Image.open(source_path).convert("RGBA")
    alpha = image.getchannel("A")
    alpha_min, alpha_max = alpha.getextrema()
    if alpha_min < 255 and alpha_max > 0:
        rgba = image
        mask_mode = "existing_alpha"
    else:
        rgb = _flatten(image).convert("RGB")
        background = _estimate_background(rgb)
        mask = _connected_background_mask(rgb, background, background_threshold, background_min_channel)
        rgba = rgb.convert("RGBA")
        pixels = rgba.load()
        bg_pixels = mask.load()
        for y in range(rgba.height):
            for x in range(rgba.width):
                red, green, blue, _ = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0 if bg_pixels[x, y] else 255)
        alpha = rgba.getchannel("A").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
        rgba.putalpha(alpha)
        mask_mode = "connected_background"

    bbox = rgba.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError(f"No foreground detected in reference: {source_path}")
    bbox = _pad_bbox(bbox, rgba.size, pad)
    cutout = rgba.crop(bbox)
    return cutout, {
        "mask_mode": mask_mode,
        "source_size": {"width": image.width, "height": image.height},
        "alpha_bbox": list(bbox),
        "pad": pad,
    }


def _fit_cutout_to_canvas(
    cutout: Image.Image,
    frame_width: int,
    frame_height: int,
    target_height: int,
) -> Image.Image:
    bbox = cutout.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError("Cutout has no alpha foreground.")
    subject = cutout.crop(bbox)
    max_width = int(frame_width * 0.86)
    scale = min(max_width / subject.width, target_height / subject.height)
    resized = subject.resize(
        (max(1, round(subject.width * scale)), max(1, round(subject.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    x = (frame_width - resized.width) // 2
    y = frame_height - resized.height
    canvas.alpha_composite(resized, (x, y))
    return canvas


def _write_stylized_walk_frames(
    frames_dir: Path,
    frame_width: int,
    frame_height: int,
    palette: dict[str, list[int]],
) -> tuple[list[Path], dict[str, Any]]:
    skeleton = _stylized_walk_skeleton(frame_width, frame_height)
    frame_paths: list[Path] = []
    for index, motion in enumerate(skeleton["frames"]):
        frame = _compose_stylized_walk_frame(frame_width, frame_height, palette, motion, skeleton["ground_y"])
        path = frames_dir / f"walk_{index:03d}.png"
        frame.save(path)
        frame_paths.append(path)
    return frame_paths, _walk_readability_from_skeleton(skeleton)


def _stylized_walk_skeleton(frame_width: int, frame_height: int) -> dict[str, Any]:
    ground_y = round(frame_height * 0.89)
    hip_base_y = round(frame_height * 0.56)
    head_base_y = round(frame_height * 0.235)
    knee_y = round(frame_height * 0.705)
    return {
        "ground_y": ground_y,
        "frames": [
            _walk_pose("contact", 0, 0, "front", 44, 0, 16, -34, 0, -22, -13),
            _walk_pose("down", 4, 1, "front", 44, 0, 20, -21, 0, -10, -8),
            _walk_pose("passing", -2, 0, "none", 5, -18, 0, 20, -28, 16, 1),
            _walk_pose("up", -5, -1, "none", -24, -9, -16, 34, -18, 20, 9),
            _walk_pose("opposite_contact", 0, 0, "rear", -34, 0, -22, 44, 0, 16, 13),
            _walk_pose("opposite_down", 4, 1, "rear", -21, 0, -10, 44, 0, 20, 8),
            _walk_pose("opposite_passing", -2, 0, "none", 20, -28, 16, 5, -18, 0, -1),
            _walk_pose("opposite_up", -5, -1, "none", 34, -18, 20, -24, -9, -16, -9),
        ],
        "hip_base_y": hip_base_y,
        "head_base_y": head_base_y,
        "knee_y": knee_y,
    }


def _walk_pose(
    phase: str,
    hip_bob: int,
    head_bob: int,
    contact_foot: str,
    front_foot_x: int,
    front_foot_lift: int,
    front_knee_x: int,
    rear_foot_x: int,
    rear_foot_lift: int,
    rear_knee_x: int,
    arm_swing: int,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "hip_bob": hip_bob,
        "head_bob": head_bob,
        "contact_foot": contact_foot,
        "front": {"foot_x": front_foot_x, "foot_lift": front_foot_lift, "knee_x": front_knee_x},
        "rear": {"foot_x": rear_foot_x, "foot_lift": rear_foot_lift, "knee_x": rear_knee_x},
        "arm_swing": arm_swing,
    }


def _walk_readability_from_skeleton(skeleton: dict[str, Any]) -> dict[str, Any]:
    frames = skeleton["frames"]
    head_y_values = [skeleton["head_base_y"] + int(frame["head_bob"]) for frame in frames]
    hip_y_values = [skeleton["hip_base_y"] + int(frame["hip_bob"]) for frame in frames]
    return {
        "frame_count": len(frames),
        "phase_names": [frame["phase"] for frame in frames],
        "ground_y": skeleton["ground_y"],
        "contact_foot_by_frame": [frame["contact_foot"] for frame in frames],
        "estimated_head_y_range": [min(head_y_values), max(head_y_values)],
        "estimated_hip_y_range": [min(hip_y_values), max(hip_y_values)],
        "foot_lock_expected": True,
        "loop_expected": True,
        "route_status": ROUTE_STATUS,
        "visual_decision": VISUAL_DECISION,
    }


def _compose_stylized_walk_frame(
    width: int,
    height: int,
    palette: dict[str, list[int]],
    motion: dict[str, Any],
    ground_y: int,
) -> Image.Image:
    scale = 3
    canvas = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    p = {name: tuple(value) for name, value in palette.items()}
    cx = width * scale // 2
    ground = ground_y * scale
    hip_y = (round(height * 0.56) + int(motion["hip_bob"])) * scale
    body_y = (round(height * 0.325) + round(int(motion["hip_bob"]) * 0.55)) * scale
    head_y = (round(height * 0.235) + int(motion["head_bob"])) * scale
    knee_y = round(height * 0.705) * scale

    _draw_stylized_leg(
        draw,
        hip=(cx - 10 * scale, hip_y),
        knee=(cx + int(motion["rear"]["knee_x"]) * scale, knee_y),
        foot=(
            cx + int(motion["rear"]["foot_x"]) * scale,
            ground + int(motion["rear"]["foot_lift"]) * scale,
        ),
        palette=p,
        rear=True,
        scale=scale,
    )
    _draw_stylized_arm(draw, (cx - 29 * scale, body_y + 38 * scale), int(motion["arm_swing"]) * scale, p, scale, rear=True)
    _draw_stylized_body(draw, cx, body_y, hip_y, p, scale)
    _draw_stylized_head(draw, cx, head_y, p, scale)
    _draw_stylized_leg(
        draw,
        hip=(cx + 8 * scale, hip_y),
        knee=(cx + int(motion["front"]["knee_x"]) * scale, knee_y),
        foot=(
            cx + int(motion["front"]["foot_x"]) * scale,
            ground + int(motion["front"]["foot_lift"]) * scale,
        ),
        palette=p,
        rear=False,
        scale=scale,
    )
    _draw_stylized_arm(draw, (cx - 17 * scale, body_y + 40 * scale), -int(motion["arm_swing"]) * scale, p, scale, rear=False)

    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def _draw_stylized_body(
    draw: ImageDraw.ImageDraw,
    cx: int,
    body_y: int,
    hip_y: int,
    palette: dict[str, tuple[int, int, int, int]],
    scale: int,
) -> None:
    outline = palette["outline"]
    blouse = palette["blouse"]
    shadow = palette["uniform_shadow"]
    tie = palette["tie"]
    skirt = palette["skirt"]
    trim = palette["trim"]
    skin = palette["skin"]
    draw.rounded_rectangle(
        (cx - 10 * scale, body_y - 20 * scale, cx + 12 * scale, body_y + 10 * scale),
        radius=4 * scale,
        fill=outline,
    )
    draw.rounded_rectangle(
        (cx - 7 * scale, body_y - 20 * scale, cx + 10 * scale, body_y + 12 * scale),
        radius=4 * scale,
        fill=skin,
    )
    body = [
        (cx - 30 * scale, body_y),
        (cx + 28 * scale, body_y + 4 * scale),
        (cx + 38 * scale, hip_y - 20 * scale),
        (cx - 38 * scale, hip_y - 18 * scale),
    ]
    draw.polygon([(x, y + 2 * scale) for x, y in body], fill=outline)
    draw.polygon(body, fill=blouse)
    draw.line((cx - 24 * scale, body_y + 16 * scale, cx + 28 * scale, body_y + 18 * scale), fill=shadow, width=3 * scale)
    draw.polygon(
        [
            (cx - 10 * scale, body_y + 4 * scale),
            (cx + 22 * scale, body_y + 8 * scale),
            (cx + 4 * scale, body_y + 25 * scale),
        ],
        fill=shadow,
    )
    draw.polygon(
        [
            (cx + 4 * scale, body_y + 8 * scale),
            (cx + 15 * scale, body_y + 30 * scale),
            (cx + 4 * scale, body_y + 56 * scale),
            (cx - 5 * scale, body_y + 28 * scale),
        ],
        fill=tie,
    )
    skirt_poly = [
        (cx - 40 * scale, hip_y - 24 * scale),
        (cx + 42 * scale, hip_y - 24 * scale),
        (cx + 56 * scale, hip_y + 38 * scale),
        (cx - 52 * scale, hip_y + 38 * scale),
    ]
    waist_poly = [
        (cx - 35 * scale, hip_y - 34 * scale),
        (cx + 36 * scale, hip_y - 34 * scale),
        (cx + 43 * scale, hip_y - 14 * scale),
        (cx - 42 * scale, hip_y - 14 * scale),
    ]
    draw.polygon([(x, y + 2 * scale) for x, y in waist_poly], fill=outline)
    draw.polygon(waist_poly, fill=blouse)
    draw.polygon([(x, y + 2 * scale) for x, y in skirt_poly], fill=outline)
    draw.polygon(skirt_poly, fill=skirt)
    for offset in (-34, -12, 10, 32):
        draw.line((cx + offset * scale, hip_y - 20 * scale, cx + (offset - 8) * scale, hip_y + 34 * scale), fill=shadow, width=2 * scale)
    draw.line((cx - 50 * scale, hip_y + 31 * scale, cx + 54 * scale, hip_y + 31 * scale), fill=trim, width=3 * scale)


def _draw_stylized_head(
    draw: ImageDraw.ImageDraw,
    cx: int,
    head_y: int,
    palette: dict[str, tuple[int, int, int, int]],
    scale: int,
) -> None:
    outline = palette["outline"]
    skin = palette["skin"]
    hair = palette["hair"]
    hair_shadow = palette["hair_shadow"]
    eye = palette["eye"]
    draw.ellipse((cx - 30 * scale, head_y - 28 * scale, cx + 36 * scale, head_y + 38 * scale), fill=outline)
    draw.ellipse((cx - 24 * scale, head_y - 22 * scale, cx + 34 * scale, head_y + 36 * scale), fill=skin)
    draw.pieslice((cx - 48 * scale, head_y - 42 * scale, cx + 36 * scale, head_y + 44 * scale), 98, 348, fill=hair)
    draw.pieslice((cx - 48 * scale, head_y - 42 * scale, cx + 36 * scale, head_y + 44 * scale), 125, 235, fill=hair_shadow)
    draw.rectangle((cx - 42 * scale, head_y + 6 * scale, cx - 18 * scale, head_y + 48 * scale), fill=hair)
    draw.polygon(
        [
            (cx + 28 * scale, head_y + 4 * scale),
            (cx + 44 * scale, head_y + 12 * scale),
            (cx + 28 * scale, head_y + 18 * scale),
        ],
        fill=skin,
    )
    draw.line((cx + 12 * scale, head_y + 4 * scale, cx + 24 * scale, head_y + 4 * scale), fill=eye, width=2 * scale)
    draw.arc((cx - 26 * scale, head_y - 18 * scale, cx + 20 * scale, head_y + 20 * scale), 220, 315, fill=(255, 235, 235, 210), width=2 * scale)


def _draw_stylized_arm(
    draw: ImageDraw.ImageDraw,
    shoulder: tuple[int, int],
    swing: int,
    palette: dict[str, tuple[int, int, int, int]],
    scale: int,
    rear: bool,
) -> None:
    outline = palette["outline"]
    sleeve = palette["blouse"]
    skin = palette["skin_shadow"] if rear else palette["skin"]
    x, y = shoulder
    elbow = (x + swing // 2, y + 38 * scale)
    hand = (x + swing, y + 72 * scale)
    _draw_tapered_segment(draw, shoulder, elbow, 8 * scale, 6 * scale, sleeve, outline)
    _draw_tapered_segment(draw, elbow, hand, 5 * scale, 4 * scale, skin, outline)
    draw.ellipse((elbow[0] - 4 * scale, elbow[1] - 4 * scale, elbow[0] + 4 * scale, elbow[1] + 4 * scale), fill=outline)
    draw.ellipse((elbow[0] - 3 * scale, elbow[1] - 3 * scale, elbow[0] + 3 * scale, elbow[1] + 3 * scale), fill=skin)
    draw.ellipse((hand[0] - 4 * scale, hand[1] - 2 * scale, hand[0] + 5 * scale, hand[1] + 7 * scale), fill=skin)


def _draw_stylized_leg(
    draw: ImageDraw.ImageDraw,
    hip: tuple[int, int],
    knee: tuple[int, int],
    foot: tuple[int, int],
    palette: dict[str, tuple[int, int, int, int]],
    rear: bool,
    scale: int,
) -> None:
    outline = palette["outline"]
    skin = palette["skin_shadow"] if rear else palette["skin"]
    sock = palette["sock_shadow"] if rear else palette["sock"]
    shoe = palette["shoe_shadow"] if rear else palette["shoe"]
    thigh_width = (11 if rear else 12) * scale
    calf_width = (10 if rear else 11) * scale
    ankle = (foot[0], foot[1] - 7 * scale)
    _draw_tapered_segment(draw, hip, knee, thigh_width, max(thigh_width - 3 * scale, 5 * scale), skin, outline)
    draw.ellipse((knee[0] - 5 * scale, knee[1] - 5 * scale, knee[0] + 5 * scale, knee[1] + 5 * scale), fill=outline)
    draw.ellipse((knee[0] - 3 * scale, knee[1] - 3 * scale, knee[0] + 3 * scale, knee[1] + 3 * scale), fill=skin)
    _draw_tapered_segment(draw, knee, ankle, calf_width, max(calf_width - 4 * scale, 5 * scale), sock, outline)
    shoe_poly = [
        (foot[0] - 10 * scale, foot[1] - 6 * scale),
        (foot[0] + 22 * scale, foot[1] - 7 * scale),
        (foot[0] + 29 * scale, foot[1] - 1 * scale),
        (foot[0] + 9 * scale, foot[1] + 5 * scale),
        (foot[0] - 12 * scale, foot[1] + 3 * scale),
    ]
    draw.polygon(shoe_poly, fill=outline)
    inner = [(round(x * 0.92 + foot[0] * 0.08), round(y * 0.86 + foot[1] * 0.14)) for x, y in shoe_poly]
    draw.polygon(inner, fill=shoe)


def _draw_tapered_segment(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    start_width: int,
    end_width: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
) -> None:
    outline_poly = _tapered_polygon(start, end, start_width + 4, end_width + 4)
    fill_poly = _tapered_polygon(start, end, start_width, end_width)
    draw.polygon(outline_poly, fill=outline)
    draw.polygon(fill_poly, fill=fill)


def _tapered_polygon(
    start: tuple[int, int],
    end: tuple[int, int],
    start_width: int,
    end_width: int,
) -> list[tuple[int, int]]:
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length = math.hypot(dx, dy) or 1.0
    nx = -dy / length
    ny = dx / length
    sw = start_width / 2
    ew = end_width / 2
    return [
        (round(sx + nx * sw), round(sy + ny * sw)),
        (round(ex + nx * ew), round(ey + ny * ew)),
        (round(ex - nx * ew), round(ey - ny * ew)),
        (round(sx - nx * sw), round(sy - ny * sw)),
    ]


def _write_walk_frames(base: Image.Image, frames_dir: Path, palette: dict[str, list[int]]) -> list[Path]:
    cycle = [
        {
            "phase": "contact",
            "bob": 0,
            "front": ((0.07, 0.02), (0.20, 0.46), (0.38, 0.95)),
            "rear": ((-0.07, 0.02), (-0.18, 0.50), (-0.34, 0.95)),
        },
        {
            "phase": "down",
            "bob": 3,
            "front": ((0.07, 0.02), (0.16, 0.48), (0.25, 0.95)),
            "rear": ((-0.07, 0.02), (-0.08, 0.52), (-0.18, 0.95)),
        },
        {
            "phase": "passing",
            "bob": -2,
            "front": ((0.07, 0.02), (0.03, 0.45), (-0.03, 0.88)),
            "rear": ((-0.07, 0.02), (0.02, 0.43), (0.15, 0.86)),
        },
        {
            "phase": "up",
            "bob": -4,
            "front": ((0.07, 0.02), (-0.08, 0.48), (-0.23, 0.95)),
            "rear": ((-0.07, 0.02), (0.12, 0.46), (0.24, 0.90)),
        },
        {
            "phase": "opposite_contact",
            "bob": 0,
            "front": ((0.07, 0.02), (-0.18, 0.50), (-0.34, 0.95)),
            "rear": ((-0.07, 0.02), (0.20, 0.46), (0.38, 0.95)),
        },
        {
            "phase": "opposite_down",
            "bob": 3,
            "front": ((0.07, 0.02), (-0.08, 0.52), (-0.18, 0.95)),
            "rear": ((-0.07, 0.02), (0.16, 0.48), (0.25, 0.95)),
        },
        {
            "phase": "opposite_passing",
            "bob": -2,
            "front": ((0.07, 0.02), (0.02, 0.43), (0.15, 0.86)),
            "rear": ((-0.07, 0.02), (0.03, 0.45), (-0.03, 0.88)),
        },
        {
            "phase": "opposite_up",
            "bob": -4,
            "front": ((0.07, 0.02), (0.12, 0.46), (0.24, 0.90)),
            "rear": ((-0.07, 0.02), (-0.08, 0.48), (-0.23, 0.95)),
        },
    ]
    frame_paths: list[Path] = []
    for index, motion in enumerate(cycle):
        frame = _compose_walk_frame(base, motion, palette)
        path = frames_dir / f"walk_{index:03d}.png"
        frame.save(path)
        frame_paths.append(path)
    return frame_paths


def _compose_walk_frame(base: Image.Image, motion: dict[str, Any], palette: dict[str, list[int]]) -> Image.Image:
    bbox = base.getchannel("A").getbbox()
    if bbox is None:
        return Image.new("RGBA", base.size, (0, 0, 0, 0))

    left, top, right, bottom = bbox
    subject_width = right - left
    subject_height = bottom - top
    hem_y = top + round(subject_height * 0.59)
    ground_y = bottom
    center_x = left + subject_width // 2
    leg_span = max(66, round(subject_width * 0.42))
    leg_width = max(8, round(subject_width * 0.046))
    outline_width = leg_width + 4
    shoe_width = max(28, round(subject_width * 0.15))
    shoe_height = max(10, round(subject_height * 0.026))
    bob = int(motion["bob"])

    upper = base.crop((left, top, right, min(bottom, hem_y + 18)))
    frame = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    leg_hem_y = hem_y + bob
    rear = [_resolve_leg_point(point, center_x, leg_hem_y, ground_y, leg_span) for point in motion["rear"]]
    front = [_resolve_leg_point(point, center_x, leg_hem_y, ground_y, leg_span) for point in motion["front"]]

    _draw_leg(draw, rear, palette, outline_width, leg_width, shoe_width, shoe_height, rear=True)
    _draw_leg(draw, front, palette, outline_width, leg_width, shoe_width, shoe_height, rear=False)
    frame.alpha_composite(upper, (left, top + bob))
    return frame


def _resolve_leg_point(
    point: tuple[float, float],
    center_x: int,
    hem_y: int,
    ground_y: int,
    leg_span: int,
) -> tuple[int, int]:
    x_norm, y_norm = point
    return (center_x + round(x_norm * leg_span), hem_y + round(y_norm * (ground_y - hem_y)))


def _draw_leg(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    palette: dict[str, list[int]],
    outline_width: int,
    leg_width: int,
    shoe_width: int,
    shoe_height: int,
    rear: bool,
) -> None:
    hip, knee, foot = points
    outline = tuple(palette["outline"])
    skin = tuple(palette["skin_shadow"] if rear else palette["skin"])
    sock = tuple(palette["sock_shadow"] if rear else palette["sock"])
    shoe = tuple(palette["shoe_shadow"] if rear else palette["shoe"])
    draw.line([hip, knee, foot], fill=outline, width=outline_width, joint="curve")
    draw.line([hip, knee], fill=skin, width=leg_width, joint="curve")
    draw.line([knee, foot], fill=sock, width=max(leg_width - 1, 4), joint="curve")
    _draw_shoe(draw, foot, shoe, outline, shoe_width, shoe_height)


def _draw_shoe(
    draw: ImageDraw.ImageDraw,
    foot: tuple[int, int],
    shoe: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    width: int,
    height: int,
) -> None:
    x, y = foot
    outline_poly = [
        (x - round(width * 0.35), y - height),
        (x + round(width * 0.42), y - height),
        (x + round(width * 0.55), y - round(height * 0.25)),
        (x + round(width * 0.15), y + round(height * 0.2)),
        (x - round(width * 0.42), y + round(height * 0.1)),
    ]
    fill_poly = [
        (x - round(width * 0.30), y - height + 2),
        (x + round(width * 0.36), y - height + 2),
        (x + round(width * 0.47), y - round(height * 0.18)),
        (x + round(width * 0.10), y - 1),
        (x - round(width * 0.36), y - 1),
    ]
    draw.polygon(outline_poly, fill=outline)
    draw.polygon(fill_poly, fill=shoe)


def _derive_character_palette(image: Image.Image) -> dict[str, list[int]]:
    opaque = _opaque_pixels(image)
    skin_candidates = [
        pixel
        for pixel in opaque
        if pixel[0] > 160 and pixel[1] > 95 and pixel[2] > 70 and pixel[0] > pixel[2] + 35
    ]
    dark_candidates = [pixel for pixel in opaque if max(pixel[:3]) < 95]
    brown_candidates = [
        pixel
        for pixel in opaque
        if pixel[0] > 55 and pixel[1] < 95 and pixel[2] < 85 and pixel[0] > pixel[2] + 15
    ]
    hair_candidates = [
        pixel
        for pixel in opaque
        if pixel[0] > 170 and 70 < pixel[1] < 190 and 80 < pixel[2] < 190 and pixel[0] > pixel[2] + 20
    ]
    outline_candidates = [pixel for pixel in opaque if max(pixel[:3]) < 60]
    skin = _average_rgba(skin_candidates, (232, 164, 128, 255))
    sock = _average_rgba(dark_candidates, (24, 30, 50, 255))
    shoe = _average_rgba(brown_candidates, (96, 42, 28, 255))
    hair = _average_rgba(hair_candidates, (230, 126, 122, 255))
    outline = _average_rgba(outline_candidates, (28, 24, 24, 255))
    return {
        "skin": list(skin),
        "skin_shadow": list(_shade(skin, 0.82)),
        "sock": list(sock),
        "sock_shadow": list(_shade(sock, 0.76)),
        "shoe": list(shoe),
        "shoe_shadow": list(_shade(shoe, 0.72)),
        "hair": list(hair),
        "hair_shadow": list(_shade(hair, 0.78)),
        "blouse": [244, 248, 250, 255],
        "uniform_shadow": [183, 194, 208, 255],
        "skirt": [246, 248, 250, 255],
        "trim": [206, 45, 38, 255],
        "tie": [220, 47, 38, 255],
        "eye": [38, 35, 35, 255],
        "outline": list(outline),
    }


def _opaque_pixels(image: Image.Image) -> list[tuple[int, int, int, int]]:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    out: list[tuple[int, int, int, int]] = []
    for y in range(rgba.height):
        for x in range(rgba.width):
            pixel = pixels[x, y]
            if pixel[3] > 0:
                out.append(pixel)
    return out


def _average_rgba(pixels: list[tuple[int, int, int, int]], fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if not pixels:
        return fallback
    red = round(sum(pixel[0] for pixel in pixels) / len(pixels))
    green = round(sum(pixel[1] for pixel in pixels) / len(pixels))
    blue = round(sum(pixel[2] for pixel in pixels) / len(pixels))
    alpha = round(sum(pixel[3] for pixel in pixels) / len(pixels))
    return (red, green, blue, alpha)


def _shade(color: tuple[int, int, int, int], factor: float) -> tuple[int, int, int, int]:
    return (
        max(0, min(255, round(color[0] * factor))),
        max(0, min(255, round(color[1] * factor))),
        max(0, min(255, round(color[2] * factor))),
        color[3],
    )


def _measure_motion(frame_paths: list[Path]) -> dict[str, Any]:
    frames = [Image.open(path).convert("RGBA") for path in frame_paths]
    first = frames[0]
    diff_scores = []
    alpha_boxes = []
    for frame in frames:
        bbox = frame.getchannel("A").getbbox()
        alpha_boxes.append(list(bbox) if bbox else None)
        diff = ImageChops.difference(first, frame).convert("L")
        diff_scores.append(round(ImageStat.Stat(diff).mean[0], 3))
    unique_alpha_boxes = len({tuple(box) for box in alpha_boxes if box is not None})
    return {
        "mean_diff_from_first": diff_scores,
        "max_mean_diff_from_first": max(diff_scores),
        "unique_alpha_boxes": unique_alpha_boxes,
        "phase_labels": PHASE_NAMES,
    }


def _flatten(image: Image.Image) -> Image.Image:
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    return background


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    pixels = image.load()
    width, height = image.size
    samples = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
        pixels[width // 2, 0],
        pixels[width // 2, height - 1],
    ]
    return tuple(round(sum(sample[channel] for sample in samples) / len(samples)) for channel in range(3))


def _connected_background_mask(
    image: Image.Image,
    background: tuple[int, int, int],
    threshold: int,
    min_channel: int,
) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    candidate = Image.new("L", image.size, 0)
    candidate_pixels = candidate.load()
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            if distance <= threshold and min(red, green, blue) >= min_channel:
                candidate_pixels[x, y] = 255

    out = Image.new("L", image.size, 0)
    out_pixels = out.load()
    stack: list[tuple[int, int]] = []
    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height:
            continue
        if out_pixels[x, y] > 0 or candidate_pixels[x, y] == 0:
            continue
        out_pixels[x, y] = 255
        stack.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    return out


def _pad_bbox(bbox: tuple[int, int, int, int], size: tuple[int, int], pad: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    width, height = size
    return (max(0, left - pad), max(0, top - pad), min(width, right + pad), min(height, bottom + pad))


def _notes(manifest: dict[str, Any]) -> str:
    return f"""# Walk 8-Frame Side-View Baseline

This is a deliberately conservative MVP package for game import review.

- route: `{manifest["route"]}`
- route_status: `{manifest["route_status"]}`
- frame_count: `{manifest["frame_count"]}`
- fps: `{manifest["fps"]}`
- frame_size: `{manifest["frame_size"]["width"]}x{manifest["frame_size"]["height"]}`
- action: `walk`
- direction: `right`
- view: `side`
- loop: `true`
- background: `transparent`

## What This Is

The package starts from one reference image, derives identity colors, and renders a stylized
8-phase side-view walk cycle. The default renderer intentionally favors readable game motion over
direct cutout fidelity, because the cutout-shift preview was not evaluation-worthy.

## What This Is Not

- Not production-grade animation.
- Not Wan/video generation.
- Not a 120-frame candidate.
- Not attack, hit, run, weapon, or broad action generation.
- Not proof that the generative pipeline can make final-quality walk cycles.
- Not a faithful redraw of every reference-image detail.

Use this as the boring concrete artifact route: `frames/*.png`, `spritesheet.png`, and `preview.gif`
are the review targets.
"""


if __name__ == "__main__":
    main()
