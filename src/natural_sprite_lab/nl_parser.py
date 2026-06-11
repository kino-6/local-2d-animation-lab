from __future__ import annotations

import re
from pathlib import Path
from typing import TypeVar

from natural_sprite_lab.models import (
    Action,
    AnimationSpec,
    Background,
    Direction,
    OutputFormat,
    Tone,
)
from natural_sprite_lab.utils.paths import normalize_name


ACTION_PATTERNS: list[tuple[Action, tuple[str, ...]]] = [
    (Action.ATTACK, ("attack", "slash", "strike", "battle")),
    (Action.IDLE, ("idle", "breathing", "breathe")),
    (Action.HIT, ("hit", "damage", "hurt", "reaction")),
    (Action.RUN, ("run", "running", "sprint", "sprinting")),
    (Action.WALK, ("walk", "walking", "side-view walking")),
]

DIRECTION_PATTERNS: list[tuple[Direction, tuple[str, ...]]] = [
    (Direction.LEFT, ("left", "facing left", "to the left")),
    (Direction.RIGHT, ("right", "facing right", "to the right")),
    (Direction.FRONT, ("front", "forward", "facing camera", "facing front")),
]

TONE_PATTERNS: list[tuple[Tone, tuple[str, ...]]] = [
    (Tone.ENERGETIC, ("energetic", "lively", "quick", "snappy")),
    (Tone.CALM, ("calm", "gentle", "subtle", "relaxed")),
    (Tone.HEAVY, ("heavy", "weighty", "slow", "stomping")),
    (Tone.CUTE, ("cute", "adorable", "chibi", "sweet")),
]

T = TypeVar("T")


def parse_prompt(prompt: str, input_path: str | Path | None = None) -> AnimationSpec:
    text = prompt.lower()
    action = _first_match(text, ACTION_PATTERNS, Action.WALK)
    direction = _first_match(text, DIRECTION_PATTERNS, Direction.RIGHT)
    tone = _first_match(text, TONE_PATTERNS, Tone.NEUTRAL)
    frame_count = _parse_frame_count(text, default=8)
    loop = not any(word in text for word in ("non-loop", "non loop", "once", "one-shot", "one shot"))
    background = Background.TRANSPARENT if "transparent" in text or "alpha" in text else Background.TRANSPARENT
    output_formats = _parse_output_formats(text)
    character_id = _character_id_from_path(input_path)

    return AnimationSpec(
        character_id=character_id,
        action=action,
        direction=direction,
        frame_count=frame_count,
        loop=loop,
        tone=tone,
        preserve_identity=True,
        background=background,
        output_formats=output_formats,
    )


def _first_match(text: str, patterns: list[tuple[T, tuple[str, ...]]], default: T) -> T:
    for value, keywords in patterns:
        if any(keyword in text for keyword in keywords):
            return value
    return default


def _parse_frame_count(text: str, default: int) -> int:
    match = re.search(r"(\d+)\s*[- ]?\s*frames?", text)
    if not match:
        return default
    frame_count = int(match.group(1))
    return min(max(frame_count, 1), 240)


def _parse_output_formats(text: str) -> list[OutputFormat]:
    formats = [OutputFormat.PNG_SEQUENCE]
    if "sprite sheet" in text or "spritesheet" in text:
        formats.append(OutputFormat.SPRITE_SHEET)
    if "gif" in text or "preview" in text:
        formats.append(OutputFormat.GIF_PREVIEW)
    if "contact sheet" in text:
        formats.append(OutputFormat.CONTACT_SHEET)
    if len(formats) == 1:
        formats.extend(
            [
                OutputFormat.SPRITE_SHEET,
                OutputFormat.GIF_PREVIEW,
                OutputFormat.CONTACT_SHEET,
            ]
        )
    return formats


def _character_id_from_path(input_path: str | Path | None) -> str:
    if input_path is None:
        return "character"
    return normalize_name(Path(input_path).stem) or "character"
