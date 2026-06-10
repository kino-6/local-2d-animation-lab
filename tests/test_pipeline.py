from pathlib import Path
import json

from PIL import Image

from natural_sprite_lab.backends import CutoutWalkBackend, DummyBackend, RiggedSpriteBackend
from natural_sprite_lab.evaluation import evaluate_animation
from natural_sprite_lab.pipeline import run_pipeline
from natural_sprite_lab.planning import WalkCycleDirector


def test_pipeline_writes_expected_outputs(tmp_path: Path) -> None:
    source = tmp_path / "hero.png"
    Image.new("RGBA", (64, 96), (255, 0, 0, 255)).save(source)

    outputs = run_pipeline(
        source_image=source,
        prompt="Create an 8-frame walking animation facing right with transparent background.",
        backend=DummyBackend(),
        output_root=tmp_path / "outputs",
        retake=2,
        run_id="test_run",
    )

    assert outputs.run_dir.exists()
    assert len(outputs.frame_paths) == 8
    assert all(path.exists() for path in outputs.frame_paths)
    assert outputs.sprite_sheet_path is not None and outputs.sprite_sheet_path.exists()
    assert outputs.gif_path is not None and outputs.gif_path.exists()
    assert outputs.contact_sheet_path is not None and outputs.contact_sheet_path.exists()
    assert outputs.spec_path.exists()
    assert outputs.manifest_path.exists()
    assert (outputs.run_dir / "evaluation_report.json").exists()


def test_cutout_walk_pipeline_writes_directed_plan(tmp_path: Path) -> None:
    source = tmp_path / "hero.png"
    image = Image.new("RGBA", (96, 160), (0, 0, 0, 0))
    for y in range(160):
        color = (220, 80 + y // 3, 120, 255)
        for x in range(28, 68):
            image.putpixel((x, y), color)
    image.save(source)

    outputs = run_pipeline(
        source_image=source,
        prompt="Create an 8-frame side-view walking animation facing right with transparent background.",
        backend=CutoutWalkBackend(),
        output_root=tmp_path / "outputs",
        retake=1,
        run_id="cutout_run",
        director=WalkCycleDirector(use_ollama=False),
    )

    assert len(outputs.frame_paths) == 8
    assert outputs.contact_sheet_path is not None and outputs.contact_sheet_path.exists()
    spec_text = outputs.spec_path.read_text(encoding="utf-8")
    assert "frame_plan" in spec_text
    assert "contact_right" in spec_text
    assert "prompt_pack" in spec_text


def test_director_builds_character_profile_and_prompt_pack(tmp_path: Path) -> None:
    source = tmp_path / "hero.png"
    Image.new("RGBA", (128, 128), (210, 120, 80, 255)).save(source)

    outputs = run_pipeline(
        source_image=source,
        prompt="Create an 8-frame walking animation preserving this character design.",
        backend=DummyBackend(),
        output_root=tmp_path / "outputs",
        run_id="directed_run",
        director=WalkCycleDirector(use_ollama=False),
    )

    spec_text = outputs.spec_path.read_text(encoding="utf-8")
    assert "character_profile" in spec_text
    assert "Generate new full-body frames" in spec_text
    assert "prompt_pack" in spec_text


def test_director_resamples_frame_plan_to_120_frames(tmp_path: Path) -> None:
    source = tmp_path / "hero.png"
    Image.new("RGBA", (128, 128), (210, 120, 80, 255)).save(source)

    outputs = run_pipeline(
        source_image=source,
        prompt="Create a 120-frame quick sword slash attack animation preserving this character design.",
        backend=DummyBackend(),
        output_root=tmp_path / "outputs",
        run_id="directed_120_run",
        director=WalkCycleDirector(use_ollama=False),
    )

    spec = json.loads(outputs.spec_path.read_text(encoding="utf-8"))
    assert spec["frame_count"] == 120
    assert len(spec["frame_plan"]) == 120
    assert len(spec["prompt_pack"]) == 120
    assert spec["frame_plan"][0]["source_keyframe_count"] == 8


def test_attack_pipeline_writes_effect_layers(tmp_path: Path) -> None:
    source = tmp_path / "hero.png"
    Image.new("RGBA", (96, 128), (210, 120, 80, 255)).save(source)

    outputs = run_pipeline(
        source_image=source,
        prompt="Create an 8-frame quick sword slash attack animation facing right.",
        backend=DummyBackend(),
        output_root=tmp_path / "outputs",
        run_id="attack_run",
        director=WalkCycleDirector(use_ollama=False),
    )

    assert len(outputs.effect_frame_paths) == 8
    assert all(path.exists() for path in outputs.effect_frame_paths)
    assert len(outputs.composited_frame_paths) == 8
    assert all(path.exists() for path in outputs.composited_frame_paths)
    assert outputs.effect_contact_sheet_path is not None and outputs.effect_contact_sheet_path.exists()
    assert outputs.composited_contact_sheet_path is not None and outputs.composited_contact_sheet_path.exists()
    spec_text = outputs.spec_path.read_text(encoding="utf-8")
    assert "effect_anchor" in spec_text
    assert "semantic_tags" in spec_text
    report_text = (outputs.run_dir / "evaluation_report.json").read_text(encoding="utf-8")
    assert '"semantic"' in report_text
    assert "active_frames" in report_text
    manifest = json.loads(outputs.manifest_path.read_text(encoding="utf-8"))
    assert manifest["game_engine_metadata"]["frame_width"] > 0
    assert manifest["game_engine_metadata"]["frame_events"]
    assert manifest["game_engine_metadata"]["hitboxes"]
    assert manifest["evaluation"]["semantic"]["action"] == "attack"


def test_rigged_sprite_backend_writes_animation_viability(tmp_path: Path) -> None:
    source = tmp_path / "hero.png"
    image = Image.new("RGBA", (96, 160), (0, 0, 0, 0))
    for y in range(16, 150):
        for x in range(32, 64):
            image.putpixel((x, y), (210, 100 + y // 4, 72, 255))
    image.save(source)

    outputs = run_pipeline(
        source_image=source,
        prompt="Create an 8-frame bow attack animation facing right with a clear draw, release, and recovery.",
        backend=RiggedSpriteBackend(width=256, height=256),
        output_root=tmp_path / "outputs",
        run_id="rigged_attack_run",
        director=WalkCycleDirector(use_ollama=False),
    )

    report = json.loads((outputs.run_dir / "evaluation_report.json").read_text(encoding="utf-8"))
    viability = report["animation_viability"]
    manifest = json.loads(outputs.manifest_path.read_text(encoding="utf-8"))

    assert viability["score"] >= 0.75
    assert viability["summary"]["rigged_like"] is True
    assert viability["summary"]["motion_economy"]["style"] == "sfc"
    assert viability["summary"]["motion_economy"]["source_frame_count"] == 120
    assert manifest["evaluation"]["animation_viability"]["score"] == viability["score"]
    assert len(outputs.frame_paths) == 8


def test_evaluation_scores_consistent_frames(tmp_path: Path) -> None:
    paths = []
    for index in range(3):
        path = tmp_path / f"frame_{index}.png"
        image = Image.new("RGBA", (64, 64), (250, 250, 250, 255))
        for y in range(12, 56):
            for x in range(24 + index, 40 + index):
                image.putpixel((x, y), (120, 60, 40, 255))
        image.save(path)
        paths.append(path)

    report = evaluate_animation(paths)

    assert report["score"] > 0.5
    assert "summary" in report
