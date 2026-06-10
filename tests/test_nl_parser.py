from natural_sprite_lab.models import Action, Background, Direction, OutputFormat, Tone
from natural_sprite_lab.nl_parser import parse_prompt


def test_parse_walk_prompt_with_direction_and_frame_count() -> None:
    spec = parse_prompt(
        "Create an 8-frame side-view walking animation, facing right, with transparent background.",
        "assets/reference/Hero Knight.png",
    )

    assert spec.character_id == "hero_knight"
    assert spec.action == Action.WALK
    assert spec.direction == Direction.RIGHT
    assert spec.frame_count == 8
    assert spec.loop is True
    assert spec.background == Background.TRANSPARENT
    assert OutputFormat.SPRITE_SHEET in spec.output_formats
    assert OutputFormat.GIF_PREVIEW in spec.output_formats


def test_parse_attack_non_loop_tone() -> None:
    spec = parse_prompt("Make a heavy 12 frame battle attack once, facing left.")

    assert spec.action == Action.ATTACK
    assert spec.direction == Direction.LEFT
    assert spec.frame_count == 12
    assert spec.loop is False
    assert spec.tone == Tone.HEAVY


def test_parse_defaults_are_mvp_friendly() -> None:
    spec = parse_prompt("walk")

    assert spec.action == Action.WALK
    assert spec.direction == Direction.RIGHT
    assert spec.frame_count == 8
    assert spec.background == Background.TRANSPARENT


def test_parse_120_frame_controlnet_prompt() -> None:
    spec = parse_prompt("Create a 120-frame quick sword slash attack animation, facing right.")

    assert spec.action == Action.ATTACK
    assert spec.frame_count == 120
