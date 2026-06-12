from __future__ import annotations

import argparse
import json
import time
import urllib.request
from collections.abc import Callable
from typing import Any

from natural_sprite_lab.progress import ProgressTimer


def add_queue_wait_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-queue-size", default=2, type=int)
    parser.add_argument("--queue-wait-timeout-seconds", default=1800.0, type=float)


def wait_for_queue_capacity_from_args(server_url: str, args: argparse.Namespace) -> dict[str, Any]:
    return wait_for_queue_capacity(
        server_url,
        max_queue_size=args.max_queue_size,
        timeout_seconds=args.queue_wait_timeout_seconds,
    )


def wait_for_queue_capacity(
    server_url: str,
    *,
    max_queue_size: int,
    timeout_seconds: float,
    poll_seconds: float = 5.0,
    get_queue: Callable[[str], dict[str, Any]] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if max_queue_size < 0:
        return {"status": "skipped", "queue_size": None}

    fetch_queue = get_queue or _get_queue
    started = clock()
    deadline = started + timeout_seconds
    latest: dict[str, Any] = {}
    with ProgressTimer(total_seconds=timeout_seconds, desc="ComfyUI queue wait") as progress:
        while clock() < deadline:
            latest = fetch_queue(server_url)
            queue_size = queue_item_count(latest)
            if queue_size <= max_queue_size:
                return {
                    "status": "ready",
                    "queue_size": queue_size,
                    "queue_running": len(latest.get("queue_running", [])),
                    "queue_pending": len(latest.get("queue_pending", [])),
                    "max_queue_size": max_queue_size,
                }
            progress.update_elapsed(clock() - started)
            sleep(poll_seconds)

    raise TimeoutError(
        "Timed out waiting for ComfyUI queue capacity: "
        + json.dumps(
            {
                "queue_size": queue_item_count(latest),
                "queue_running": len(latest.get("queue_running", [])),
                "queue_pending": len(latest.get("queue_pending", [])),
                "max_queue_size": max_queue_size,
            },
            ensure_ascii=False,
        )
    )


def queue_item_count(queue: dict[str, Any]) -> int:
    return len(queue.get("queue_running", [])) + len(queue.get("queue_pending", []))


def _get_queue(server_url: str) -> dict[str, Any]:
    request = urllib.request.Request(f"{server_url.rstrip('/')}/queue", method="GET")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))
