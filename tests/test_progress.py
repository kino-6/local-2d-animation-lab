from __future__ import annotations

from natural_sprite_lab.progress import ProgressTimer
from natural_sprite_lab.progress import progress_iter


def test_progress_iter_preserves_items() -> None:
    assert list(progress_iter([1, 2, 3], total=3, desc="test")) == [1, 2, 3]


def test_progress_timer_tracks_elapsed_without_bar() -> None:
    timer = ProgressTimer(total_seconds=3.1, desc="wait")
    with timer:
        timer.update_elapsed(1.2)
        timer.update_elapsed(2.8)

    assert timer._shown == 2
