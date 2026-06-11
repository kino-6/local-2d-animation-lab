from pathlib import Path

from PIL import Image, ImageDraw

from natural_sprite_lab.quality import FrameQuality, analyze_frame_quality, foreground_normalized_delta, select_best_span


def test_analyze_frame_quality_flags_duplicate_silhouette(tmp_path: Path) -> None:
    clean = tmp_path / "clean.png"
    broken = tmp_path / "broken.png"
    _draw_character(clean)
    _draw_character(broken, ghost=True)

    clean_quality = analyze_frame_quality(clean, index=0)
    broken_quality = analyze_frame_quality(broken, index=1, previous_path=clean)

    assert not clean_quality.hard_failure
    assert broken_quality.duplicate_silhouette_area > clean_quality.duplicate_silhouette_area
    assert broken_quality.upper_body_center_shift >= 0
    assert "duplicate_silhouette_area_high" in broken_quality.issue_codes


def test_select_best_span_prefers_contiguous_clean_frames(tmp_path: Path) -> None:
    paths = []
    for index in range(6):
        path = tmp_path / f"frame_{index:03d}.png"
        _draw_character(path, ghost=index in {2, 3})
        paths.append(path)

    qualities = [
        analyze_frame_quality(path, index=index, previous_path=paths[index - 1] if index else None)
        for index, path in enumerate(paths)
    ]
    selection = select_best_span(qualities, span_length=2)

    assert selection.frame_indices in {(0, 1), (4, 5)}
    assert selection.hard_failures == 0


def test_select_best_span_can_penalize_low_motion_spans() -> None:
    qualities = [
        _quality(0, score=0.95, motion=0.0),
        _quality(1, score=0.95, motion=1.0),
        _quality(2, score=0.88, motion=7.0),
        _quality(3, score=0.88, motion=7.0),
    ]

    selection = select_best_span(qualities, span_length=2, min_mean_motion_delta=4.0)

    assert selection.frame_indices != (0, 1)
    assert selection.mean_motion_delta >= 4.0
    assert selection.selection_penalties == ()


def test_select_best_span_reports_foreground_mask_delta_penalty() -> None:
    qualities = [
        _quality(0, score=0.95, motion=0.0, mask_delta=0.0),
        _quality(1, score=0.95, motion=5.0, mask_delta=0.4),
    ]

    selection = select_best_span(qualities, span_length=2, max_mean_foreground_mask_delta=0.2)

    assert selection.selection_penalties == ("foreground_mask_temporal_delta_high",)


def test_select_best_span_reports_penalty_in_hard_failure_fallback() -> None:
    qualities = [
        _quality(0, score=0.6, motion=0.0, hard_failure=True),
        _quality(1, score=0.6, motion=1.0, hard_failure=True),
        _quality(2, score=0.6, motion=1.0, hard_failure=True),
    ]

    selection = select_best_span(qualities, span_length=2, min_mean_motion_delta=4.0)

    assert selection.hard_failures == 2
    assert selection.selection_penalties == ("mean_motion_delta_too_low",)


def test_foreground_motion_delta_normalizes_small_subject_motion(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _draw_tiny_subject(first, offset=0)
    _draw_tiny_subject(second, offset=8)

    first_quality = analyze_frame_quality(first, index=0)
    second_quality = analyze_frame_quality(second, index=1, previous_path=first)

    assert foreground_normalized_delta(first, second) > second_quality.motion_delta_prev
    assert second_quality.foreground_motion_delta_prev > second_quality.motion_delta_prev


def test_select_best_span_can_use_foreground_motion_metric() -> None:
    qualities = [
        _quality(0, score=0.95, motion=0.0, foreground_motion=0.0),
        _quality(1, score=0.95, motion=1.0, foreground_motion=8.0),
        _quality(2, score=0.88, motion=2.0, foreground_motion=2.0),
    ]

    global_selection = select_best_span(qualities, span_length=2, min_mean_motion_delta=4.0)
    foreground_selection = select_best_span(
        qualities,
        span_length=2,
        min_mean_motion_delta=4.0,
        motion_metric="foreground",
    )

    assert global_selection.selection_penalties == ("mean_motion_delta_too_low",)
    assert foreground_selection.frame_indices == (0, 1)
    assert foreground_selection.selection_penalties == ()


def test_analyze_frame_quality_reports_background_and_lower_body_issues(tmp_path: Path) -> None:
    dirty = tmp_path / "dirty.png"
    _draw_character(dirty, extra_leg=True, dirty_background=True)

    quality = analyze_frame_quality(dirty, index=0)

    assert quality.background_contamination_ratio > 0
    assert quality.lower_body_blob_count > 2
    assert "lower_body_blob_count_high" in quality.issue_codes


def test_analyze_frame_quality_does_not_count_skirt_as_extra_foot(tmp_path: Path) -> None:
    normal = tmp_path / "normal_walk.png"
    _draw_skirt_walk_frame(normal)

    quality = analyze_frame_quality(normal, index=0)

    assert quality.lower_body_blob_count <= 2
    assert "lower_body_blob_count_high" not in quality.issue_codes


def test_analyze_frame_quality_protects_light_skin_from_duplicate_mask(tmp_path: Path) -> None:
    frame = tmp_path / "light_skin.png"
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((114, 28, 142, 56), fill=(150, 95, 55))
    draw.rectangle((108, 56, 148, 132), fill=(20, 40, 95))
    draw.rectangle((112, 132, 124, 210), fill=(248, 207, 194))
    draw.rectangle((136, 132, 148, 210), fill=(248, 207, 194))
    draw.ellipse((96, 204, 126, 224), fill=(28, 24, 28))
    draw.ellipse((132, 204, 162, 224), fill=(28, 24, 28))
    image.save(frame)

    quality = analyze_frame_quality(frame, index=0)

    assert quality.duplicate_silhouette_area < 0.02
    assert "duplicate_silhouette_area_high" not in quality.issue_codes


def _quality(
    index: int,
    *,
    score: float,
    motion: float,
    foreground_motion: float | None = None,
    mask_delta: float = 0.0,
    hard_failure: bool = False,
) -> FrameQuality:
    return FrameQuality(
        index=index,
        path=f"frame_{index:03d}.png",
        foreground_coverage=0.1,
        background_contamination_ratio=0.0,
        dark_ratio=0.0,
        duplicate_silhouette_area=0.0,
        lower_body_blob_count=2,
        mask_coverage=0.0,
        upper_body_center_shift=0.0,
        motion_delta_prev=motion,
        score=score,
        hard_failure=hard_failure,
        issue_codes=(),
        foreground_motion_delta_prev=motion if foreground_motion is None else foreground_motion,
        foreground_mask_delta_prev=mask_delta,
    )


def _draw_character(
    path: Path,
    ghost: bool = False,
    extra_leg: bool = False,
    dirty_background: bool = False,
) -> None:
    image = Image.new("RGB", (128, 128), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    if dirty_background:
        draw.rectangle((8, 8, 24, 120), fill=(210, 210, 225))
    draw.ellipse((54, 12, 74, 32), fill=(40, 30, 25))
    draw.rectangle((50, 32, 78, 78), fill=(20, 40, 85))
    draw.line((56, 78, 44, 116), fill=(20, 20, 25), width=7)
    draw.line((72, 78, 84, 116), fill=(20, 20, 25), width=7)
    if extra_leg:
        draw.line((104, 78, 112, 116), fill=(20, 20, 25), width=7)
    if ghost:
        draw.rectangle((78, 34, 104, 80), fill=(180, 185, 205))
        draw.line((86, 80, 104, 116), fill=(170, 175, 200), width=7)
    image.save(path)


def _draw_tiny_subject(path: Path, offset: int) -> None:
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    x = 112 + offset
    draw.ellipse((x, 84, x + 16, 100), fill=(40, 30, 25))
    draw.rectangle((x - 2, 100, x + 18, 138), fill=(20, 40, 85))
    draw.line((x + 2, 138, x - 8, 174), fill=(20, 20, 25), width=5)
    draw.line((x + 14, 138, x + 24, 174), fill=(20, 20, 25), width=5)
    image.save(path)


def _draw_skirt_walk_frame(path: Path) -> None:
    image = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((114, 28, 142, 56), fill=(58, 38, 28))
    draw.rectangle((108, 56, 148, 126), fill=(20, 40, 95))
    draw.polygon(((106, 126), (150, 126), (162, 162), (94, 162)), fill=(20, 40, 95))
    draw.rectangle((110, 162, 122, 212), fill=(245, 205, 190))
    draw.rectangle((136, 162, 148, 212), fill=(245, 205, 190))
    draw.ellipse((96, 204, 126, 224), fill=(28, 24, 28))
    draw.ellipse((132, 204, 162, 224), fill=(28, 24, 28))
    image.save(path)
