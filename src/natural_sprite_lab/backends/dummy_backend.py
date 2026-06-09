from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, ImageStat

from natural_sprite_lab.backends.base import AnimationBackend
from natural_sprite_lab.models import AnimationSpec, Direction, GeneratedFrames
from natural_sprite_lab.utils.paths import frame_filename


class DummyBackend(AnimationBackend):
    """Deterministic local backend used to prove the asset pipeline."""

    name = "dummy"

    def generate_frames(
        self,
        source_image: Path,
        spec: AnimationSpec,
        frames_dir: Path,
        retake: int = 1,
    ) -> GeneratedFrames:
        frames_dir.mkdir(parents=True, exist_ok=True)
        source = Image.open(source_image).convert("RGBA")
        palette = _extract_palette(source)
        frame_paths: list[Path] = []

        for index in range(spec.frame_count):
            frame = _make_walk_mock_frame(index, spec.frame_count, spec.direction, palette)
            path = frames_dir / frame_filename(spec.character_id, spec.action.value, index, retake)
            frame.save(path)
            frame_paths.append(path)

        return GeneratedFrames(
            frame_paths=frame_paths,
            backend_name=self.name,
            backend_metadata={
                "description": "Canonical mock 8-frame walk cycle drawn from the source image palette.",
                "walk_cycle": [
                    "contact_right",
                    "down_right",
                    "passing_right",
                    "up_right",
                    "contact_left",
                    "down_left",
                    "passing_left",
                    "up_left",
                ][: spec.frame_count],
                "retake": retake,
            },
        )


def _extract_palette(image: Image.Image) -> dict[str, tuple[int, int, int, int]]:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    visible = image.crop(bbox) if bbox else image
    color = ImageStat.Stat(visible.convert("RGB")).mean
    base = tuple(int(channel) for channel in color)
    accent = tuple(min(255, int(channel * 1.18) + 18) for channel in color)
    shadow = tuple(max(0, int(channel * 0.52)) for channel in color)

    return {
        "skin": (*accent, 255),
        "hair": (*shadow, 255),
        "torso": (*base, 255),
        "torso_dark": (*tuple(max(0, channel - 42) for channel in base), 255),
        "limb": (*tuple(max(0, channel - 18) for channel in base), 255),
        "outline": (42, 44, 52, 255),
        "shoe": (36, 38, 46, 255),
    }


def _make_walk_mock_frame(
    index: int,
    frame_count: int,
    direction: Direction,
    palette: dict[str, tuple[int, int, int, int]],
    canvas_size: tuple[int, int] = (256, 256),
) -> Image.Image:
    pose = _walk_pose(index, frame_count)
    frame = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    ground_y = 220
    hip = (128, ground_y - 84 + pose["bob"])
    chest = (hip[0] + 1, hip[1] - 52)
    head = (chest[0] + 7, chest[1] - 35)

    shadow_width = 82 + abs(pose["front_foot"][0] - pose["back_foot"][0])
    draw.ellipse(
        (
            128 - shadow_width // 2,
            ground_y - 4,
            128 + shadow_width // 2,
            ground_y + 13,
        ),
        fill=(0, 0, 0, 34),
    )

    front_knee = _offset(hip, pose["front_knee"])
    front_foot = _offset(hip, pose["front_foot"])
    back_knee = _offset(hip, pose["back_knee"])
    back_foot = _offset(hip, pose["back_foot"])
    front_hand = _offset(chest, pose["front_hand"])
    back_hand = _offset(chest, pose["back_hand"])

    _draw_limb(draw, chest, back_hand, palette["outline"], palette["limb"], width=9)
    _draw_limb(draw, hip, back_knee, palette["outline"], palette["limb"], width=11)
    _draw_limb(draw, back_knee, back_foot, palette["outline"], palette["limb"], width=11)

    draw.polygon(
        [
            (chest[0] - 23, chest[1] + 2),
            (chest[0] + 19, chest[1] - 1),
            (hip[0] + 20, hip[1] + 6),
            (hip[0] - 17, hip[1] + 8),
        ],
        fill=palette["outline"],
    )
    draw.polygon(
        [
            (chest[0] - 17, chest[1] + 7),
            (chest[0] + 14, chest[1] + 5),
            (hip[0] + 14, hip[1] + 2),
            (hip[0] - 11, hip[1] + 4),
        ],
        fill=palette["torso"],
    )
    draw.polygon(
        [(hip[0] - 18, hip[1] + 2), (hip[0] + 20, hip[1]), (hip[0] + 12, hip[1] + 20), (hip[0] - 13, hip[1] + 21)],
        fill=palette["torso_dark"],
    )

    _draw_limb(draw, hip, front_knee, palette["outline"], palette["limb"], width=12)
    _draw_limb(draw, front_knee, front_foot, palette["outline"], palette["limb"], width=12)
    _draw_limb(draw, chest, front_hand, palette["outline"], palette["limb"], width=10)

    _draw_shoe(draw, back_foot, palette["shoe"])
    _draw_shoe(draw, front_foot, palette["shoe"])
    _draw_head(draw, head, palette)

    if direction == Direction.LEFT:
        frame = ImageOps.mirror(frame)
    return frame


def _walk_pose(index: int, frame_count: int) -> dict[str, int | tuple[int, int]]:
    cycle_index = round((index % frame_count) * 8 / max(frame_count, 1)) % 8
    poses: list[dict[str, int | tuple[int, int]]] = [
        {
            "bob": 0,
            "front_knee": (16, 40),
            "front_foot": (34, 84),
            "back_knee": (-16, 44),
            "back_foot": (-34, 84),
            "front_hand": (-30, 46),
            "back_hand": (30, 36),
        },
        {
            "bob": 7,
            "front_knee": (10, 48),
            "front_foot": (26, 84),
            "back_knee": (-14, 53),
            "back_foot": (-28, 84),
            "front_hand": (-22, 52),
            "back_hand": (27, 40),
        },
        {
            "bob": 2,
            "front_knee": (-3, 42),
            "front_foot": (-4, 84),
            "back_knee": (10, 39),
            "back_foot": (15, 73),
            "front_hand": (4, 48),
            "back_hand": (-6, 42),
        },
        {
            "bob": -7,
            "front_knee": (-18, 35),
            "front_foot": (-27, 75),
            "back_knee": (18, 34),
            "back_foot": (30, 82),
            "front_hand": (26, 39),
            "back_hand": (-26, 33),
        },
        {
            "bob": 0,
            "front_knee": (-16, 40),
            "front_foot": (-34, 84),
            "back_knee": (16, 44),
            "back_foot": (34, 84),
            "front_hand": (30, 46),
            "back_hand": (-30, 36),
        },
        {
            "bob": 7,
            "front_knee": (-10, 48),
            "front_foot": (-26, 84),
            "back_knee": (14, 53),
            "back_foot": (28, 84),
            "front_hand": (22, 52),
            "back_hand": (-27, 40),
        },
        {
            "bob": 2,
            "front_knee": (3, 42),
            "front_foot": (4, 84),
            "back_knee": (-10, 39),
            "back_foot": (-15, 73),
            "front_hand": (-4, 48),
            "back_hand": (6, 42),
        },
        {
            "bob": -7,
            "front_knee": (18, 35),
            "front_foot": (27, 75),
            "back_knee": (-18, 34),
            "back_foot": (-30, 82),
            "front_hand": (-26, 39),
            "back_hand": (26, 33),
        },
    ]
    return poses[cycle_index]


def _offset(point: tuple[int, int], delta: object) -> tuple[int, int]:
    dx, dy = delta
    return point[0] + dx, point[1] + dy


def _draw_limb(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    outline: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    width: int,
) -> None:
    draw.line([start, end], fill=outline, width=width + 4)
    draw.line([start, end], fill=fill, width=width)


def _draw_shoe(draw: ImageDraw.ImageDraw, foot: tuple[int, int], color: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle((foot[0] - 15, foot[1] - 3, foot[0] + 18, foot[1] + 7), radius=3, fill=color)


def _draw_head(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    palette: dict[str, tuple[int, int, int, int]],
) -> None:
    draw.ellipse((center[0] - 20, center[1] - 20, center[0] + 20, center[1] + 20), fill=palette["outline"])
    draw.ellipse((center[0] - 16, center[1] - 15, center[0] + 17, center[1] + 18), fill=palette["skin"])
    draw.pieslice((center[0] - 19, center[1] - 21, center[0] + 18, center[1] + 13), 190, 25, fill=palette["hair"])
    draw.ellipse((center[0] + 8, center[1] - 2, center[0] + 12, center[1] + 2), fill=palette["outline"])
