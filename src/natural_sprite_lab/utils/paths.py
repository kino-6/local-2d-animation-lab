from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def make_run_id(retake: int, now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"{now:%Y%m%d_%H%M%S}_r{retake:02d}"


def frame_filename(character_id: str, action: str, index: int, retake: int = 1) -> str:
    character = normalize_name(character_id) or "character"
    action_name = normalize_name(action) or "action"
    return f"{character}_{action_name}_r{retake:02d}_{index:03d}.png"


def build_run_dir(output_root: Path, character_id: str, action: str, run_id: str) -> Path:
    return output_root / normalize_name(character_id) / normalize_name(action) / run_id
