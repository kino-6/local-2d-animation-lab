from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Action(StrEnum):
    WALK = "walk"
    IDLE = "idle"
    ATTACK = "attack"
    HIT = "hit"


class Direction(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    FRONT = "front"


class Tone(StrEnum):
    ENERGETIC = "energetic"
    CALM = "calm"
    HEAVY = "heavy"
    CUTE = "cute"
    NEUTRAL = "neutral"


class Background(StrEnum):
    TRANSPARENT = "transparent"
    SOURCE = "source"


class OutputFormat(StrEnum):
    PNG_SEQUENCE = "png_sequence"
    SPRITE_SHEET = "sprite_sheet"
    GIF_PREVIEW = "gif_preview"
    CONTACT_SHEET = "contact_sheet"


@dataclass(frozen=True)
class AnimationSpec:
    character_id: str
    action: Action = Action.WALK
    direction: Direction = Direction.RIGHT
    frame_count: int = 8
    loop: bool = True
    tone: Tone = Tone.NEUTRAL
    preserve_identity: bool = True
    background: Background = Background.TRANSPARENT
    output_formats: list[OutputFormat] = field(
        default_factory=lambda: [
            OutputFormat.PNG_SEQUENCE,
            OutputFormat.SPRITE_SHEET,
            OutputFormat.GIF_PREVIEW,
            OutputFormat.CONTACT_SHEET,
        ]
    )
    identity_features: list[str] = field(default_factory=list)
    negative_prompts: list[str] = field(default_factory=list)
    frame_plan: list[dict[str, Any]] = field(default_factory=list)
    character_profile: dict[str, Any] = field(default_factory=dict)
    prompt_pack: list[dict[str, Any]] = field(default_factory=list)
    director_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        data["direction"] = self.direction.value
        data["tone"] = self.tone.value
        data["background"] = self.background.value
        data["output_formats"] = [item.value for item in self.output_formats]
        return data


@dataclass(frozen=True)
class GeneratedFrames:
    frame_paths: list[Path]
    backend_name: str
    backend_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineOutputs:
    run_dir: Path
    frames_dir: Path
    frame_paths: list[Path]
    spec_path: Path
    manifest_path: Path
    sprite_sheet_path: Path | None = None
    gif_path: Path | None = None
    contact_sheet_path: Path | None = None
    effect_frame_paths: list[Path] = field(default_factory=list)
    effect_contact_sheet_path: Path | None = None
    composited_frame_paths: list[Path] = field(default_factory=list)
    composited_contact_sheet_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_dir": str(self.run_dir),
            "frames_dir": str(self.frames_dir),
            "frame_paths": [str(path) for path in self.frame_paths],
            "sprite_sheet_path": str(self.sprite_sheet_path) if self.sprite_sheet_path else None,
            "gif_path": str(self.gif_path) if self.gif_path else None,
            "contact_sheet_path": str(self.contact_sheet_path) if self.contact_sheet_path else None,
            "effect_frame_paths": [str(path) for path in self.effect_frame_paths],
            "effect_contact_sheet_path": str(self.effect_contact_sheet_path) if self.effect_contact_sheet_path else None,
            "composited_frame_paths": [str(path) for path in self.composited_frame_paths],
            "composited_contact_sheet_path": (
                str(self.composited_contact_sheet_path) if self.composited_contact_sheet_path else None
            ),
            "spec_path": str(self.spec_path),
            "manifest_path": str(self.manifest_path),
        }
