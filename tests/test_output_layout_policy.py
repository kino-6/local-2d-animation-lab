from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

from natural_sprite_lab.utils.paths import build_timestamped_run_dir


def test_build_timestamped_run_dir_uses_outputs_timestamp_root() -> None:
    run_dir = build_timestamped_run_dir(
        Path("outputs"),
        "Wan Walk I2V",
        "Walk Len121 Strict",
        now=datetime(2026, 6, 13, 12, 34, 56),
    )

    assert run_dir == Path("outputs") / "20260613_123456" / "wan_walk_i2v" / "walk_len121_strict"


def test_build_timestamped_run_dir_keeps_existing_session() -> None:
    run_dir = build_timestamped_run_dir(
        Path("outputs") / "20260613_123456" / "quality_flow" / "main",
        "Local VL",
        "Eval",
        now=datetime(2026, 6, 13, 12, 35, 0),
    )

    assert run_dir == Path("outputs") / "20260613_123456" / "quality_flow" / "main" / "local_vl" / "eval"


def test_scripts_do_not_default_to_scattered_output_roots() -> None:
    offenders: list[str] = []
    for script in Path("scripts").glob("*.py"):
        text = script.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value != "--output-root":
                continue
            default = next((keyword.value for keyword in node.keywords if keyword.arg == "default"), None)
            if _path_constant(default) in {"review_packages", "source_probe_packages"}:
                offenders.append(f"{script}:{_path_constant(default)}")
            path_default = _path_constant(default)
            if path_default and path_default.startswith("outputs_"):
                offenders.append(f"{script}:{path_default}")

    assert offenders == []


def test_scripts_do_not_append_timestamp_to_label_at_output_root() -> None:
    offenders: list[str] = []
    for script in Path("scripts").glob("*.py"):
        text = script.read_text(encoding="utf-8")
        if "output_root / time.strftime" in text or "args.output_root / time.strftime" in text:
            offenders.append(str(script))

    assert offenders == []


def _path_constant(node: ast.AST | None) -> str | None:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Path"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    return None
