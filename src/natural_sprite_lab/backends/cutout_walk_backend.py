from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from natural_sprite_lab.backends.base import AnimationBackend
from natural_sprite_lab.models import AnimationSpec, Direction, GeneratedFrames
from natural_sprite_lab.utils.paths import frame_filename


class CutoutWalkBackend(AnimationBackend):
    """Prototype backend that preserves source pixels while applying a simple walk rig."""

    name = "cutout-walk"

    def generate_frames(
        self,
        source_image: Path,
        spec: AnimationSpec,
        frames_dir: Path,
        retake: int = 1,
    ) -> GeneratedFrames:
        frames_dir.mkdir(parents=True, exist_ok=True)
        rig = _make_cutout_rig(Image.open(source_image).convert("RGBA"))
        frame_paths: list[Path] = []

        for index in range(spec.frame_count):
            plan = _plan_for_frame(spec, index)
            frame = _render_cutout_walk_frame(rig, plan, spec.direction)
            path = frames_dir / frame_filename(spec.character_id, spec.action.value, index, retake)
            frame.save(path)
            frame_paths.append(path)

        return GeneratedFrames(
            frame_paths=frame_paths,
            backend_name=self.name,
            backend_metadata={
                "description": "Prototype cutout walk rig using source image pixels and director frame_plan.",
                "retake": retake,
                "rig": {
                    "canvas_size": rig["canvas_size"],
                    "body_bbox": rig["body_bbox"],
                    "lower_body_split": "left/right lower image halves with rotated leg cutouts",
                },
            },
        )


def _make_cutout_rig(source: Image.Image, canvas_size: tuple[int, int] = (256, 256)) -> dict[str, object]:
    source = _remove_flat_background(source)
    source_bbox = source.getchannel("A").getbbox()
    if source_bbox:
        source = source.crop(source_bbox)
    source.thumbnail((190, 226), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    x = (canvas.width - source.width) // 2
    y = canvas.height - source.height - 16
    canvas.alpha_composite(source, (x, y))

    bbox = canvas.getchannel("A").getbbox() or (64, 24, 192, 240)
    left, top, right, bottom = bbox
    width = right - left
    height = bottom - top
    hip_y = top + int(height * 0.55)
    leg_top_y = top + int(height * 0.47)
    center_x = left + width // 2
    overlap = max(5, width // 11)

    upper = _crop(canvas, (left, top, right, hip_y + overlap))
    skirt = _crop(canvas, (left, hip_y - overlap, right, min(bottom, hip_y + int(height * 0.22))))
    left_leg = _crop(canvas, (left, leg_top_y, center_x + overlap, bottom))
    right_leg = _crop(canvas, (center_x - overlap, leg_top_y, right, bottom))

    return {
        "canvas_size": canvas_size,
        "body_bbox": bbox,
        "upper": upper,
        "skirt": skirt,
        "left_leg": left_leg,
        "right_leg": right_leg,
        "upper_pos": (left, top),
        "skirt_pos": (left, hip_y - overlap),
        "left_leg_pos": (left, leg_top_y),
        "right_leg_pos": (center_x - overlap, leg_top_y),
        "hip": (center_x, hip_y),
        "ground_y": bottom,
    }


def _remove_flat_background(image: Image.Image, threshold: int = 52) -> Image.Image:
    image = image.convert("RGBA")
    width, height = image.size
    pixels = image.load()
    samples = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
    ]
    background = tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))

    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    cleaned_pixels = cleaned.load()
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            if alpha and distance > threshold:
                cleaned_pixels[x, y] = (red, green, blue, alpha)
    return cleaned


def _crop(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    return image.crop(box)


def _plan_for_frame(spec: AnimationSpec, index: int) -> dict[str, object]:
    if spec.frame_plan:
        return spec.frame_plan[index % len(spec.frame_plan)]

    fallback = [
        {"body_y": 0, "front_leg_angle": 18, "back_leg_angle": -18},
        {"body_y": 7, "front_leg_angle": 10, "back_leg_angle": -10},
        {"body_y": 2, "front_leg_angle": -4, "back_leg_angle": 8},
        {"body_y": -7, "front_leg_angle": -18, "back_leg_angle": 18},
        {"body_y": 0, "front_leg_angle": -18, "back_leg_angle": 18},
        {"body_y": 7, "front_leg_angle": -10, "back_leg_angle": 10},
        {"body_y": 2, "front_leg_angle": 4, "back_leg_angle": -8},
        {"body_y": -7, "front_leg_angle": 18, "back_leg_angle": -18},
    ]
    return fallback[index % len(fallback)]


def _render_cutout_walk_frame(
    rig: dict[str, object],
    plan: dict[str, object],
    direction: Direction,
) -> Image.Image:
    canvas_size = rig["canvas_size"]
    frame = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    body_y = int(plan.get("body_y", 0))
    front_angle = float(plan.get("front_leg_angle", 0))
    back_angle = float(plan.get("back_leg_angle", 0))
    hip_x, hip_y = rig["hip"]
    ground_y = int(rig["ground_y"])

    draw.ellipse((hip_x - 58, ground_y - 6, hip_x + 58, ground_y + 10), fill=(0, 0, 0, 36))

    left_leg_forward = front_angle < back_angle
    left_angle = front_angle if left_leg_forward else back_angle
    right_angle = back_angle if left_leg_forward else front_angle

    _paste_rotated(frame, rig["right_leg"], rig["right_leg_pos"], right_angle, body_y // 2)
    _paste_rotated(frame, rig["left_leg"], rig["left_leg_pos"], left_angle, body_y // 2)
    _paste_at(frame, rig["upper"], rig["upper_pos"], dy=body_y)
    _paste_at(frame, rig["skirt"], rig["skirt_pos"], dy=body_y)

    if direction == Direction.LEFT:
        frame = ImageOps.mirror(frame)
    return frame


def _paste_at(
    frame: Image.Image,
    piece: object,
    position: object,
    dx: int = 0,
    dy: int = 0,
) -> None:
    image = piece
    x, y = position
    frame.alpha_composite(image, (x + dx, y + dy))


def _paste_rotated(
    frame: Image.Image,
    piece: object,
    position: object,
    angle: float,
    dy: int,
) -> None:
    image = piece
    x, y = position
    rotated = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    dx = int(angle * 0.35)
    frame.alpha_composite(rotated, (x - (rotated.width - image.width) // 2 + dx, y + dy))
