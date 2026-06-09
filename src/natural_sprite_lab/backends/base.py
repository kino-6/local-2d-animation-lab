from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from natural_sprite_lab.models import AnimationSpec, GeneratedFrames


class AnimationBackend(ABC):
    """Backend interface for frame generation."""

    name = "base"

    @abstractmethod
    def generate_frames(
        self,
        source_image: Path,
        spec: AnimationSpec,
        frames_dir: Path,
        retake: int = 1,
    ) -> GeneratedFrames:
        """Generate transparent PNG frames for an animation spec."""
