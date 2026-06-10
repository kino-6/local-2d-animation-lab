from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import base64
from dataclasses import replace
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from natural_sprite_lab.models import Action
from natural_sprite_lab.models import AnimationSpec


class WalkCycleDirector:
    """Interpret a reference character and build frame prompts before generation."""

    def __init__(
        self,
        use_ollama: bool = False,
        ollama_model: str | None = None,
        ollama_url: str = "http://127.0.0.1:11434/api/chat",
        timeout_seconds: float = 8.0,
    ) -> None:
        self.use_ollama = use_ollama
        self.ollama_model = ollama_model or os.environ.get("OLLAMA_MODEL") or "huihui_ai/qwen3-vl-abliterated:8b"
        self.ollama_url = ollama_url
        self.timeout_seconds = timeout_seconds
        self.last_error: str | None = None

    def plan(self, source_image: Path, prompt: str, spec: AnimationSpec) -> AnimationSpec:
        image_report = _analyze_image(source_image)
        fallback = _fallback_plan(image_report, prompt, spec)
        llm_plan = self._ollama_plan(source_image, image_report, prompt, spec, fallback) if self.use_ollama else None
        plan = _merge_plan(fallback, llm_plan)
        if self.use_ollama and not llm_plan and self.last_error:
            plan["director_metadata"]["ollama_error"] = self.last_error
        return replace(
            spec,
            identity_features=plan["identity_features"],
            negative_prompts=plan["negative_prompts"],
            frame_plan=plan["frame_plan"][: spec.frame_count],
            character_profile=plan["character_profile"],
            prompt_pack=plan["prompt_pack"][: spec.frame_count],
            director_metadata=plan["director_metadata"],
        )

    def _ollama_plan(
        self,
        source_image: Path,
        image_report: dict[str, Any],
        prompt: str,
        spec: AnimationSpec,
        fallback: dict[str, Any],
    ) -> dict[str, Any] | None:
        director_prompt = (
            "Return JSON only. Interpret the attached anime reference image as a character design "
            "for generating new full-body animation frames. Do not describe pixel warping. "
            "Use keys: character_profile, identity_features, negative_prompts. "
            "character_profile should include hair, eyes, outfit, accessories, expression, style. "
            f"Motion request: {prompt}. "
            f"Image summary: {json.dumps(image_report, ensure_ascii=False)}"
        )
        payload = {
            "model": self.ollama_model,
            "messages": [
                {
                    "role": "user",
                    "content": director_prompt,
                    "images": [_image_b64(source_image)],
                }
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 220},
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                self.ollama_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
            content = raw.get("response") or raw.get("message", {}).get("content") or "{}"
            return json.loads(content)
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as error:
            self.last_error = str(error)
            return None


def _analyze_image(source_image: Path) -> dict[str, Any]:
    image = Image.open(source_image).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    visible = image.crop(bbox) if bbox else image
    stat = ImageStat.Stat(visible.convert("RGB"))
    mean = [round(channel) for channel in stat.mean]
    view = "full_body_candidate"
    if bbox:
        visible_width = bbox[2] - bbox[0]
        visible_height = bbox[3] - bbox[1]
        if visible_height < image.height * 0.78 or visible_width > visible_height * 0.75:
            view = "upper_body_or_bust"
    return {
        "file_name": source_image.name,
        "size": {"width": image.width, "height": image.height},
        "visible_bbox": bbox,
        "estimated_view": view,
        "dominant_rgb": mean,
        "identity_summary": (
            "Generate new images of the same character. Preserve visual identity, proportions, color "
            "palette, silhouette, face, hair, costume, accessories, and anime illustration style."
        ),
    }


def _fallback_plan(image_report: dict[str, Any], prompt: str, spec: AnimationSpec) -> dict[str, Any]:
    character_profile = {
        "source": image_report["file_name"],
        "visual_identity": [
            "anime girl character",
            "medium warm brown hair, brown hair, not pink hair",
            "large amber eyes",
            "small pink hair clip on one side",
            "white sailor-style school uniform with dark collar",
            "red necktie",
            "dark pleated skirt, navy socks, brown loafers",
            "cheerful open-mouth expression",
            "clean anime line art and soft cel shading",
        ],
        "style": "anime game sprite, clean line art, soft cel shading",
        "view_note": image_report["estimated_view"],
        "generation_intent": "Generate new full-body frames that match this reference character design.",
    }
    frame_plan = _frame_plan_for_action(spec.action, prompt)
    return {
        "character_profile": character_profile,
        "identity_features": [
            image_report["identity_summary"],
            f"Use source image {image_report['file_name']} as the visual identity reference.",
            f"Keep dominant RGB palette {image_report['dominant_rgb']}.",
            f"Source view estimate: {image_report['estimated_view']}.",
        ],
        "negative_prompts": [
            "whole-image shake only",
            "identity drift",
            "extra limbs",
            "missing feet",
            "costume color changes",
            "foot sliding without contact poses",
        ],
        "frame_plan": frame_plan[: spec.frame_count],
        "prompt_pack": _make_prompt_pack(character_profile, frame_plan[: spec.frame_count], prompt),
        "director_metadata": {
            "director": "fallback_walk_cycle_director",
            "ollama_used": False,
            "input_prompt": prompt,
            "image_report": image_report,
            "prototype_limitation": (
                "This director can interpret the reference and create prompts, but identity consistency "
                "depends on the image-generation backend and available reference/pose guidance."
            ),
        },
    }


def _frame(
    label: str,
    planted_foot: str,
    body_y: int,
    front_leg_angle: int,
    back_leg_angle: int,
    note: str,
) -> dict[str, Any]:
    return {
        "label": label,
        "planted_foot": planted_foot,
        "body_y": body_y,
        "front_leg_angle": front_leg_angle,
        "back_leg_angle": back_leg_angle,
        "arm_swing": "opposes legs",
        "note": note,
    }


def _frame_plan_for_action(action: Action, prompt: str = "") -> list[dict[str, Any]]:
    attack_variant = _attack_variant(prompt)
    hit_variant = _hit_variant(prompt)
    if action == Action.IDLE:
        return [
            _frame("idle_neutral", "both", 0, 0, 0, "relaxed standing pose, both feet planted"),
            _frame("idle_breathe_in", "both", -3, 1, -1, "subtle inhale, shoulders rise slightly"),
            _frame("idle_neutral_2", "both", 0, 0, 0, "relaxed standing pose, eyes forward"),
            _frame("idle_breathe_out", "both", 3, -1, 1, "subtle exhale, shoulders settle"),
            _frame("idle_blink", "both", 0, 0, 0, "relaxed standing pose with a small blink"),
            _frame("idle_sway_left", "both", 1, -2, 2, "tiny weight shift to the left foot"),
            _frame("idle_neutral_3", "both", 0, 0, 0, "relaxed standing pose, hands steady"),
            _frame("idle_sway_right", "both", 1, 2, -2, "tiny weight shift to the right foot"),
        ]
    if action == Action.ATTACK:
        if attack_variant == "bow":
            return [
                _frame("attack_bow_ready", "back", 0, -8, 12, "archer stance, bow held forward, arrow ready"),
                _frame("attack_bow_draw", "back", -2, -12, 14, "draw bowstring, rear elbow pulled back strongly"),
                _frame("attack_bow_aim", "both", -1, -6, 8, "aim forward, torso steady, bow arm extended"),
                _frame("attack_bow_release", "front", 0, 4, -4, "release arrow, bow arm extended, string hand snaps forward"),
                _frame("attack_bow_follow", "front", 2, 8, -6, "follow through after arrow release"),
                _frame("attack_bow_recover", "both", 3, 2, -2, "lower bow slightly, regain balance"),
                _frame("attack_bow_return", "both", 1, 0, 0, "return to archer ready stance"),
                _frame("attack_bow_ready_loop", "back", 0, -8, 12, "archer ready stance for loop transition"),
            ]
        if attack_variant == "axe":
            return [
                _frame("attack_axe_ready", "back", 2, -18, 18, "heavy axe ready stance, wide footing"),
                _frame("attack_axe_windup", "back", -5, -24, 20, "large overhead windup, axe raised behind head"),
                _frame("attack_axe_lift", "back", -7, -20, 18, "lift heavy axe high, shoulders tense"),
                _frame("attack_axe_overhead", "front", -2, 10, -12, "start overhead chop, weight shifts forward"),
                _frame("attack_axe_impact", "front", 5, 28, -22, "heavy downward axe impact pose, strong squash"),
                _frame("attack_axe_follow", "front", 7, 20, -16, "follow through low after heavy chop"),
                _frame("attack_axe_recover", "both", 4, 6, -6, "recover slowly from axe swing"),
                _frame("attack_axe_ready_loop", "back", 2, -16, 16, "wide ready stance for loop transition"),
            ]
        return [
            _frame("attack_sword_ready", "back", 0, -12, 16, "sword combat ready stance, weight on back foot"),
            _frame("attack_sword_windup", "back", -3, -20, 18, "wind up for a quick sword slash, torso twists back"),
            _frame("attack_sword_start", "front", 1, 12, -10, "step forward and begin the sword slash"),
            _frame("attack_sword_impact", "front", -2, 24, -18, "fast forward sword slash pose, action line implied"),
            _frame("attack_sword_follow", "front", 2, 18, -14, "follow through after the sword slash"),
            _frame("attack_sword_recover", "front", 4, 6, -6, "recover from the sword attack, weapon arm lowers"),
            _frame("attack_sword_return", "both", 1, 0, 0, "return toward sword ready stance"),
            _frame("attack_sword_ready_loop", "back", 0, -10, 14, "sword ready stance for loop transition"),
        ]
    if action == Action.HIT:
        if hit_variant == "knockback":
            return [
                _frame("hit_knockback_neutral", "both", 0, 0, 0, "neutral stance before a strong knockback impact"),
                _frame("hit_knockback_impact", "back", -6, -16, 18, "impact launches body backward, shocked expression"),
                _frame("hit_knockback_airborne", "none", -18, -26, 26, "body lifted off the ground, limbs trailing backward"),
                _frame("hit_knockback_peak", "none", -24, -30, 28, "peak airborne knockback, torso arched backward"),
                _frame("hit_knockback_fall", "back", -10, -22, 22, "falling backward, preparing to land"),
                _frame("hit_knockback_land", "back", 8, -18, 18, "hard landing after knockback, knees bent"),
                _frame("hit_knockback_recover", "both", 6, -6, 6, "push back up from knockback"),
                _frame("hit_knockback_settle", "both", 1, 0, 0, "settle back toward neutral"),
            ]
        if hit_variant == "heavy":
            return [
                _frame("hit_heavy_neutral", "both", 0, 0, 0, "neutral stance before heavy damage"),
                _frame("hit_heavy_impact", "back", -5, -14, 16, "heavy damage impact, torso crumples backward"),
                _frame("hit_heavy_recoil", "back", -10, -22, 22, "strong recoil, arms raised defensively"),
                _frame("hit_heavy_peak", "back", -8, -26, 24, "peak heavy damage reaction, body curled"),
                _frame("hit_heavy_collapse", "both", 8, -14, 14, "collapse downward from heavy damage, knees bend deeply"),
                _frame("hit_heavy_recover", "both", 10, -6, 6, "slow recovery, still hurt"),
                _frame("hit_heavy_stand", "both", 4, -2, 2, "standing back up from heavy damage"),
                _frame("hit_heavy_neutral_loop", "both", 0, 0, 0, "neutral stance for loop transition"),
            ]
        return [
            _frame("hit_light_neutral", "both", 0, 0, 0, "neutral stance before a light hit"),
            _frame("hit_light_impact", "back", -3, -8, 10, "small hit impact, startled expression"),
            _frame("hit_light_recoil", "back", -5, -12, 12, "small backward stagger, arms raised slightly"),
            _frame("hit_light_peak", "back", -4, -14, 14, "peak light stagger, torso leaned back"),
            _frame("hit_light_falloff", "both", 2, -6, 6, "recovering balance after small hit"),
            _frame("hit_light_recover", "both", 4, -2, 2, "knees bent slightly, regaining stance"),
            _frame("hit_light_settle", "both", 2, 0, 0, "settling back to neutral after light stagger"),
            _frame("hit_light_neutral_loop", "both", 0, 0, 0, "neutral stance for loop transition"),
        ]
    return [
        _frame("contact_right", "right", 0, 18, -18, "right foot planted forward; left foot back"),
        _frame("down_right", "right", 7, 10, -10, "weight settles over the planted right foot"),
        _frame("passing_right", "right", 2, -4, 8, "left foot passes under the hip"),
        _frame("up_right", "right", -7, -18, 18, "body rises as the left foot swings forward"),
        _frame("contact_left", "left", 0, -18, 18, "left foot planted forward; right foot back"),
        _frame("down_left", "left", 7, -10, 10, "weight settles over the planted left foot"),
        _frame("passing_left", "left", 2, 4, -8, "right foot passes under the hip"),
        _frame("up_left", "left", -7, 18, -18, "body rises as the right foot swings forward"),
    ]


def _attack_variant(prompt: str) -> str:
    text = prompt.lower()
    if any(token in text for token in ("bow", "arrow", "archer", "弓", "矢")):
        return "bow"
    if any(token in text for token in ("axe", "hatchet", "斧")):
        return "axe"
    return "sword"


def _hit_variant(prompt: str) -> str:
    text = prompt.lower()
    if any(token in text for token in ("knockback", "blown away", "launch", "吹き飛ばし", "吹き飛ぶ")):
        return "knockback"
    if any(token in text for token in ("heavy", "big damage", "large damage", "大ダメージ", "強攻撃")):
        return "heavy"
    return "light"


def _merge_plan(fallback: dict[str, Any], llm_plan: dict[str, Any] | None) -> dict[str, Any]:
    if not llm_plan:
        return fallback

    character_profile = llm_plan.get("character_profile") or fallback["character_profile"]
    identity_features = llm_plan.get("identity_features") or fallback["identity_features"]
    negative_prompts = llm_plan.get("negative_prompts") or fallback["negative_prompts"]
    frame_notes = llm_plan.get("frame_notes") or []
    frame_plan = []
    for index, frame in enumerate(fallback["frame_plan"]):
        enriched = dict(frame)
        if index < len(frame_notes):
            enriched["llm_note"] = str(frame_notes[index])
        frame_plan.append(enriched)

    prompt_pack = _make_prompt_pack(character_profile, frame_plan, fallback["director_metadata"]["input_prompt"])
    metadata = dict(fallback["director_metadata"])
    metadata.update({"director": "ollama_walk_cycle_director", "ollama_used": True})
    return {
        "character_profile": character_profile,
        "identity_features": [str(item) for item in identity_features],
        "negative_prompts": [str(item) for item in negative_prompts],
        "frame_plan": frame_plan,
        "prompt_pack": prompt_pack,
        "director_metadata": metadata,
    }


def _make_prompt_pack(
    character_profile: dict[str, Any],
    frame_plan: list[dict[str, Any]],
    prompt: str,
) -> list[dict[str, Any]]:
    identity = _profile_to_prompt(character_profile)
    negative = (
        "low quality, blurry, bad anatomy, extra arms, extra legs, missing limbs, duplicate character, "
        "wrong outfit, changed hair color, pink hair, changed eye color, cropped feet, text, watermark, logo, "
        "multiple panels, sprite sheet, contact sheet, comic layout, UI frame, dialogue box, close-up, bust shot, "
        "rope, swing set, playground, holding rope, cane, staff, prop, multiple girls, two girls, group, barefoot, "
        "pose reference sheet, turnaround sheet, multiple poses in one image"
    )
    prompts = []
    for index, frame in enumerate(frame_plan):
        action_phrase = _action_phrase(str(frame["label"]))
        pose = (
            f"{frame['label']} {action_phrase}, {frame['note']}, side view, full body, "
            "feet visible, clear game animation pose, one character only"
        )
        prompts.append(
            {
                "frame": index,
                "label": frame["label"],
                "positive": (
                    f"score_9, score_8_up, score_7_up, source_anime, masterpiece, best quality, "
                    f"1girl, solo, one girl only, exactly one full-body character, single animation frame, "
                    f"standing, single character, full body, centered, white background, "
                    f"{identity}, {pose}, consistent character design"
                ),
                "negative": negative,
                "pose_note": pose,
                "source_instruction": prompt,
            }
        )
    return prompts


def _action_phrase(label: str) -> str:
    if label.startswith("idle"):
        return "idle animation pose"
    if label.startswith("attack"):
        return "attack animation pose"
    if label.startswith("hit"):
        return "hit reaction animation pose"
    return "walk-cycle pose"


def _profile_to_prompt(character_profile: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("visual_identity", "style", "generation_intent"):
        value = character_profile.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    if not parts:
        for value in character_profile.values():
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif isinstance(value, dict):
                parts.extend(str(item) for item in value.values())
            elif value:
                parts.append(str(value))
    return ", ".join(parts)


def _image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
