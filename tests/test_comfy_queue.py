from __future__ import annotations

import pytest

from natural_sprite_lab.comfy_queue import queue_item_count
from natural_sprite_lab.comfy_queue import wait_for_queue_capacity


def test_queue_item_count_counts_running_and_pending() -> None:
    queue = {"queue_running": [1], "queue_pending": [2, 3]}

    assert queue_item_count(queue) == 3


def test_wait_for_queue_capacity_returns_when_queue_is_small() -> None:
    result = wait_for_queue_capacity(
        "http://example.invalid",
        max_queue_size=2,
        timeout_seconds=1,
        get_queue=lambda _server: {"queue_running": [1], "queue_pending": []},
        sleep=lambda _seconds: None,
    )

    assert result["status"] == "ready"
    assert result["queue_size"] == 1


def test_wait_for_queue_capacity_waits_until_queue_shrinks() -> None:
    queues = [
        {"queue_running": [1], "queue_pending": [2, 3]},
        {"queue_running": [1], "queue_pending": []},
    ]

    def get_queue(_server: str) -> dict[str, list[int]]:
        return queues.pop(0)

    result = wait_for_queue_capacity(
        "http://example.invalid",
        max_queue_size=1,
        timeout_seconds=10,
        get_queue=get_queue,
        sleep=lambda _seconds: None,
    )

    assert result["queue_size"] == 1
    assert queues == []


def test_wait_for_queue_capacity_can_skip() -> None:
    result = wait_for_queue_capacity(
        "http://example.invalid",
        max_queue_size=-1,
        timeout_seconds=1,
        get_queue=lambda _server: pytest.fail("queue should not be fetched"),
    )

    assert result["status"] == "skipped"
