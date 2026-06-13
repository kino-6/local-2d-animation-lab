from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_sprite_with_ollama_vl import _coerce_issue_list
from evaluate_sprite_with_ollama_vl import _extract_json
from evaluate_sprite_with_ollama_vl import _normalize_with_llm
from evaluate_sprite_with_ollama_vl import _ollama_generate
from evaluate_sprite_with_ollama_vl import _safe_label
from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


DEFAULT_PROMPT = """You are a strict local visual evaluator for 2D game sprite start-reference images.
Evaluate whether the image can be used as the first/source frame for a side-view walk animation.
Return compact JSON if possible. Be conservative.
Keys:
full_body_0_5, side_view_profile_0_5, walk_contact_pose_0_5,
shoe_readability_0_5, single_character_0_5, plain_background_0_5,
is_full_body, is_right_facing_side_view, has_readable_separated_shoes,
is_model_sheet_or_turnaround, has_secondary_character_or_prop,
is_walk_ready_start_reference, visible_issues, recommended_next_step.
If the character is front-facing, bust-up, model-sheet-like, has a bicycle/prop, or shoes are unreadable,
is_walk_ready_start_reference must be false.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate walk start-reference candidates with local Ollama VL.")
    parser.add_argument("--image", action="append", required=True, type=Path)
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--vision-model", default="huihui_ai/qwen3-vl-abliterated:8b")
    parser.add_argument("--normalizer-model", default="huihui_ai/qwen3-abliterated:8b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout-seconds", default=240.0, type=float)
    parser.add_argument("--start-report", default=None, type=Path)
    args = parser.parse_args()

    label = _safe_label(args.run_label or "start_reference_local_vl")
    run_dir = build_timestamped_run_dir(args.output_root, "local_vl_eval", label)
    write_run_profile(
        run_dir,
        category="local_vl_eval",
        label=label,
        args=args,
        memo="LocalVL start-reference semantic review. Secondary signal only.",
    )

    raw = _ollama_generate(
        args.ollama_url,
        args.vision_model,
        DEFAULT_PROMPT,
        images=args.image,
        timeout=args.timeout_seconds,
    )
    (run_dir / "start_reference_vl_raw.txt").write_text(raw, encoding="utf-8")
    parsed = _extract_json(raw)
    normalization_source = "vision_json"
    if parsed is None:
        normalization_source = "local_llm_normalizer"
        normalizer_raw = _normalize_start_reference_with_llm(
            args.ollama_url,
            args.normalizer_model,
            raw,
            timeout=args.timeout_seconds,
        )
        (run_dir / "start_reference_llm_normalize_raw.txt").write_text(normalizer_raw, encoding="utf-8")
        parsed = _extract_json(normalizer_raw)
    if parsed is None:
        parsed = {
            "is_walk_ready_start_reference": False,
            "visible_issues": ["local_vl_json_parse_failed"],
            "recommended_next_step": "Review start_reference_vl_raw.txt manually.",
        }
        normalization_source = "parse_failed_fallback"

    deterministic_report = _read_json(args.start_report) if args.start_report else None
    final = _apply_start_reference_consistency_rules(parsed, deterministic_report)
    final["local_vl_role"] = "secondary_start_reference_review"
    final["normalization_source"] = normalization_source
    final["vision_model"] = args.vision_model
    final["normalizer_model"] = args.normalizer_model if normalization_source == "local_llm_normalizer" else None
    final["images"] = [str(path) for path in args.image]
    final["start_report"] = str(args.start_report) if args.start_report else None
    output = run_dir / "start_reference_vl_eval.json"
    output.write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "evaluation": final}, indent=2, ensure_ascii=False))


def _normalize_start_reference_with_llm(
    ollama_url: str,
    model: str,
    notes: str,
    *,
    timeout: float,
) -> str:
    prompt = f"""/no_think
Convert these start-reference visual-evaluation notes into ONLY valid JSON, no markdown.
Use this schema:
{{"full_body_0_5":number,"side_view_profile_0_5":number,"walk_contact_pose_0_5":number,"shoe_readability_0_5":number,"single_character_0_5":number,"plain_background_0_5":number,"is_full_body":boolean,"is_right_facing_side_view":boolean,"has_readable_separated_shoes":boolean,"is_model_sheet_or_turnaround":boolean,"has_secondary_character_or_prop":boolean,"is_walk_ready_start_reference":boolean,"visible_issues":[string],"recommended_next_step":string}}
Notes:
{notes}
"""
    return _ollama_generate(ollama_url, model, prompt, images=[], timeout=timeout)


def _apply_start_reference_consistency_rules(
    payload: dict[str, Any],
    deterministic_report: dict[str, Any] | None,
) -> dict[str, Any]:
    result = dict(payload)
    issues = _coerce_issue_list(result.get("visible_issues"))
    blocking_reasons: list[str] = []
    if not bool(result.get("is_full_body", False)):
        blocking_reasons.append("local_vl_not_full_body")
    if not bool(result.get("is_right_facing_side_view", False)):
        blocking_reasons.append("local_vl_not_right_facing_side_view")
    if not bool(result.get("has_readable_separated_shoes", False)):
        blocking_reasons.append("local_vl_shoes_not_readable")
    if bool(result.get("is_model_sheet_or_turnaround", False)):
        blocking_reasons.append("local_vl_model_sheet_or_turnaround")
    if bool(result.get("has_secondary_character_or_prop", False)):
        blocking_reasons.append("local_vl_secondary_character_or_prop")
    for key, label in (
        ("side_view_profile_0_5", "local_vl_low_side_view_score"),
        ("shoe_readability_0_5", "local_vl_low_shoe_readability_score"),
        ("walk_contact_pose_0_5", "local_vl_low_walk_contact_score"),
    ):
        if float(result.get(key) or 0) < 3:
            blocking_reasons.append(label)

    deterministic = _deterministic_start_status(deterministic_report or {})
    if deterministic["blocking"]:
        blocking_reasons.extend(deterministic["blocking_reasons"])
    result["deterministic_start_status"] = deterministic
    result["blocking_reasons"] = sorted(dict.fromkeys(blocking_reasons))
    if blocking_reasons:
        result["is_walk_ready_start_reference"] = False
        issues.extend(blocking_reasons)
    else:
        result["is_walk_ready_start_reference"] = bool(result.get("is_walk_ready_start_reference", False))
    result["visible_issues"] = sorted(dict.fromkeys(issues))
    return result


def _deterministic_start_status(report: dict[str, Any]) -> dict[str, Any]:
    selected = report.get("selected", {}) if isinstance(report, dict) else {}
    issue_codes = list(selected.get("issue_codes", []))
    selection_status = selected.get("selection_status")
    blocking_reasons = []
    if selection_status and selection_status != "candidate_ok":
        blocking_reasons.append("deterministic_selection_not_candidate_ok")
    for code in issue_codes:
        if code in {
            "feet_not_separated",
            "shoes_unreadable",
            "lower_legs_occluded",
            "foot_zone_merged",
            "possible_back_view_or_missing_profile_detail",
            "guide_or_panel_residue",
            "background_contamination_high",
            "large_secondary_component",
            "duplicate_silhouette_area_high",
            "foreground_too_wide_for_side_reference",
        }:
            blocking_reasons.append(f"deterministic_{code}")
    return {
        "selection_status": selection_status,
        "selected_name": selected.get("name"),
        "issue_codes": issue_codes,
        "blocking": bool(blocking_reasons),
        "blocking_reasons": sorted(dict.fromkeys(blocking_reasons)),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
