from __future__ import annotations

import argparse
import base64
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from natural_sprite_lab.utils.paths import build_timestamped_run_dir, write_run_profile


DEFAULT_PROMPT = """You are a strict local visual evaluator for 2D game sprite animation assets.
Evaluate the image for the requested action: {action}.
Return compact JSON if possible. Be conservative.
Keys:
still_image_quality_0_5, game_sprite_asset_fit_0_5, action_readability_0_5,
identity_consistency_0_5, background_cleanliness_0_5,
is_readable_{action_key}_action, is_adoptable_as_still_sprite_proof,
is_adoptable_as_animation_or_{action_key}_endpoint, visible_issues,
recommended_next_step.
If the character is mostly standing or neutral, action_readability_0_5 must be 2 or lower.
Specifically inspect lower-body afterimages, foot sliding/contact smears,
silhouette redraw jitter, and brightness/saturation drift between frames.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate sprite assets with local Ollama vision and normalize output.")
    parser.add_argument("--image", action="append", required=True, type=Path)
    parser.add_argument("--action", default="run")
    parser.add_argument("--output-root", default=Path("outputs"), type=Path)
    parser.add_argument("--run-label", default=None)
    parser.add_argument("--vision-model", default="huihui_ai/qwen3-vl-abliterated:8b")
    parser.add_argument("--normalizer-model", default="huihui_ai/qwen3-abliterated:8b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout-seconds", default=240.0, type=float)
    parser.add_argument("--deterministic-report", action="append", default=[], type=Path)
    args = parser.parse_args()

    label = _safe_label(args.run_label or f"{args.action}_local_vl_eval")
    run_dir = build_timestamped_run_dir(args.output_root, "local_vl_eval", label)
    write_run_profile(
        run_dir,
        category="local_vl_eval",
        label=label,
        args=args,
        memo="Local visual-language evaluation output. Keep raw model notes and normalized JSON together.",
    )

    action_key = _safe_label(args.action).lower()
    prompt = DEFAULT_PROMPT.format(action=args.action, action_key=action_key)
    raw = _ollama_generate(
        args.ollama_url,
        args.vision_model,
        prompt,
        images=args.image,
        timeout=args.timeout_seconds,
    )
    (run_dir / "local_vl_raw.txt").write_text(raw, encoding="utf-8")

    parsed = _extract_json(raw)
    normalized_source = "vision_json"
    if parsed is None:
        normalized_source = "local_llm_normalizer"
        normalizer_raw = _normalize_with_llm(
            args.ollama_url,
            args.normalizer_model,
            raw,
            action_key,
            timeout=args.timeout_seconds,
        )
        (run_dir / "local_llm_normalize_raw.txt").write_text(normalizer_raw, encoding="utf-8")
        parsed = _extract_json(normalizer_raw)

    if parsed is None:
        parsed = {
            "action_readability_0_5": 0,
            f"is_readable_{action_key}_action": False,
            f"is_adoptable_as_animation_or_{action_key}_endpoint": False,
            "visible_issues": ["local_vl_json_parse_failed"],
            "recommended_next_step": "Review local_vl_raw.txt manually.",
        }
        normalized_source = "parse_failed_fallback"

    final = _apply_consistency_rules(parsed, action_key)
    final = _apply_deterministic_gate_rules(
        final,
        action_key,
        [_read_json(path) for path in args.deterministic_report],
    )
    final["normalization_source"] = normalized_source
    final["vision_model"] = args.vision_model
    final["normalizer_model"] = args.normalizer_model if normalized_source == "local_llm_normalizer" else None
    final["images"] = [str(path) for path in args.image]
    final["deterministic_reports"] = [str(path) for path in args.deterministic_report]
    (run_dir / "local_vl_eval.json").write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "evaluation": final}, indent=2, ensure_ascii=False))


def _normalize_with_llm(
    ollama_url: str,
    model: str,
    notes: str,
    action_key: str,
    timeout: float,
) -> str:
    prompt = f"""/no_think
Convert these visual-evaluation notes into ONLY valid JSON, no markdown.
Use this schema:
{{"still_image_quality_0_5":number,"game_sprite_asset_fit_0_5":number,"action_readability_0_5":number,"identity_consistency_0_5":number,"background_cleanliness_0_5":number,"is_readable_{action_key}_action":boolean,"is_adoptable_as_still_sprite_proof":boolean,"is_adoptable_as_animation_or_{action_key}_endpoint":boolean,"visible_issues":[string],"recommended_next_step":string}}
Notes:
{notes}
"""
    return _ollama_generate(ollama_url, model, prompt, images=[], timeout=timeout)


def _ollama_generate(
    ollama_url: str,
    model: str,
    prompt: str,
    *,
    images: list[Path],
    timeout: float,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 1600},
    }
    if images:
        payload["images"] = [base64.b64encode(path.read_bytes()).decode("ascii") for path in images]
    request = urllib.request.Request(
        f"{ollama_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc
    return f"{data.get('response') or ''}\n{data.get('thinking') or ''}".strip()


def _extract_json(text: str) -> dict[str, Any] | None:
    for match in re.finditer(r"\{.*?\}", text, flags=re.S):
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _apply_consistency_rules(payload: dict[str, Any], action_key: str) -> dict[str, Any]:
    result = dict(payload)
    readable_key = f"is_readable_{action_key}_action"
    endpoint_key = f"is_adoptable_as_animation_or_{action_key}_endpoint"
    still_key = "is_adoptable_as_still_sprite_proof"
    action_score = float(result.get("action_readability_0_5") or 0)
    readable = bool(result.get(readable_key))
    if not readable or action_score <= 2:
        result[readable_key] = False
        result[endpoint_key] = False
    result.setdefault(still_key, False)
    issues = _coerce_issue_list(result.get("visible_issues"))
    if result.get(still_key) and not result.get(endpoint_key) and not any("action" in issue.lower() for issue in issues):
        issues.append(f"Still image may be usable, but {action_key} action readability is insufficient.")
    result["visible_issues"] = issues
    return result


def _apply_deterministic_gate_rules(
    payload: dict[str, Any],
    action_key: str,
    deterministic_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    result = dict(payload)
    endpoint_key = f"is_adoptable_as_animation_or_{action_key}_endpoint"
    readable_key = f"is_readable_{action_key}_action"
    issues = _coerce_issue_list(result.get("visible_issues"))
    gate_statuses = [_deterministic_status(report) for report in deterministic_reports]
    blocking = [status for status in gate_statuses if status["blocking"]]
    result["deterministic_gate_statuses"] = gate_statuses
    if blocking:
        result[endpoint_key] = False
        result["local_vl_role"] = "secondary_only"
        result["deterministic_override_applied"] = True
        if not any("deterministic" in issue.lower() for issue in issues):
            issues.append("Deterministic artifact/region gate blocks adoption despite LocalVL output.")
        for status in blocking:
            issues.extend(status["blocking_reasons"])
        result["visible_issues"] = sorted(dict.fromkeys(issues))
        if float(result.get("action_readability_0_5") or 0) <= 2:
            result[readable_key] = False
    else:
        result.setdefault("local_vl_role", "semantic_signal")
        result["deterministic_override_applied"] = False
        result["visible_issues"] = issues
    return result


def _deterministic_status(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {}) if isinstance(report, dict) else {}
    gate_counts = summary.get("gate_counts", {})
    action_counts = summary.get("action_counts", {})
    candidate_status = summary.get("candidate_status") or report.get("candidate_status")
    label_counts = summary.get("review_label_counts") or summary.get("issue_label_counts") or summary.get("label_counts") or {}
    blocking_reasons: list[str] = []
    if candidate_status == "rejected":
        blocking_reasons.append("deterministic_candidate_status_rejected")
    if int(gate_counts.get("retake_required", 0) or 0) > 0:
        blocking_reasons.append("deterministic_retake_required_frames")
    if int(action_counts.get("retake_required", 0) or 0) > 0:
        blocking_reasons.append("masked_plan_retake_required_frames")
    for label in (
        "lower_body_pale_afterimage_review",
        "foot_shadow_or_contact_artifact_review",
        "silhouette_redraw_jitter_review",
    ):
        if int(label_counts.get(label, 0) or 0) > 0:
            blocking_reasons.append(label)
    return {
        "candidate_status": candidate_status,
        "gate_counts": gate_counts,
        "action_counts": action_counts,
        "label_counts": label_counts,
        "blocking": bool(blocking_reasons),
        "blocking_reasons": sorted(dict.fromkeys(blocking_reasons)),
    }


def _coerce_issue_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _safe_label(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "local_vl_eval"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
