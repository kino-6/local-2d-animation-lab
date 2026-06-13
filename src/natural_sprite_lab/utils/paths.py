from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = Path("outputs")
TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")


def normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def make_run_id(retake: int, now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"{now:%Y%m%d_%H%M%S}_r{retake:02d}"


def timestamp_id(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"{now:%Y%m%d_%H%M%S}"


def frame_filename(character_id: str, action: str, index: int, retake: int = 1) -> str:
    character = normalize_name(character_id) or "character"
    action_name = normalize_name(action) or "action"
    return f"{character}_{action_name}_r{retake:02d}_{index:03d}.png"


def build_run_dir(output_root: Path, character_id: str, action: str, run_id: str) -> Path:
    return output_root / normalize_name(character_id) / normalize_name(action) / run_id


def build_timestamped_run_dir(
    output_root: Path,
    category: str,
    label: str,
    now: datetime | None = None,
) -> Path:
    """Build a run directory under outputs/<timestamp>/<category>/<label>.

    If a caller already passes a path inside outputs/<timestamp>, keep that session
    and append only category/label. This keeps orchestrated child tools grouped in
    the same top-level timestamp instead of scattering sibling output roots.
    """

    root = Path(output_root)
    category_name = normalize_name(category) or "run"
    label_name = normalize_name(label) or "run"
    parts = root.parts
    if len(parts) >= 2 and parts[0] == DEFAULT_OUTPUT_ROOT.name and TIMESTAMP_RE.match(parts[1]):
        return root / category_name / label_name
    if parts and parts[0].startswith("outputs_"):
        legacy_category = normalize_name(parts[0].removeprefix("outputs_")) or "legacy"
        return DEFAULT_OUTPUT_ROOT / timestamp_id(now) / legacy_category / category_name / label_name
    if root == DEFAULT_OUTPUT_ROOT:
        return root / timestamp_id(now) / category_name / label_name
    return root / timestamp_id(now) / category_name / label_name


def write_run_profile(
    run_dir: Path,
    *,
    category: str,
    label: str,
    args: Any | None = None,
    memo: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": _timestamp_from_run_dir(run_dir),
        "category": normalize_name(category) or category,
        "label": label,
        "run_dir": str(run_dir),
    }
    if args is not None:
        payload["args"] = _jsonable(vars(args) if hasattr(args, "__dict__") else args)
    if extra:
        payload.update(_jsonable(extra))
    (run_dir / "run_profile.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    memo_text = memo or "Run memo placeholder. Add observations, selection notes, and quality decisions here."
    (run_dir / "memo.md").write_text(
        f"# Run Memo\n\n- category: `{payload['category']}`\n- label: `{label}`\n\n{memo_text}\n",
        encoding="utf-8",
    )


def _timestamp_from_run_dir(run_dir: Path) -> str | None:
    for part in run_dir.parts:
        if TIMESTAMP_RE.match(part):
            return part
    return None


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
