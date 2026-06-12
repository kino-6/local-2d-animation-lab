from __future__ import annotations

import math
import sys
from collections.abc import Iterable, Iterator
from types import TracebackType
from typing import TypeVar

T = TypeVar("T")

try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover - fallback for minimal environments
    tqdm = None  # type: ignore[assignment]


def progress_iter(
    iterable: Iterable[T],
    *,
    total: int | None = None,
    desc: str,
    unit: str = "it",
) -> Iterator[T]:
    if tqdm is None or not sys.stderr.isatty():
        yield from iterable
        return
    yield from tqdm(iterable, total=total, desc=desc, unit=unit, dynamic_ncols=True)


class ProgressTimer:
    def __init__(self, *, total_seconds: float, desc: str) -> None:
        self.total_seconds = max(1, int(math.ceil(total_seconds)))
        self.desc = desc
        self._bar = None
        self._shown = 0

    def __enter__(self) -> ProgressTimer:
        if tqdm is not None and sys.stderr.isatty():
            self._bar = tqdm(total=self.total_seconds, desc=self.desc, unit="s", dynamic_ncols=True)
        return self

    def update_elapsed(self, elapsed_seconds: float) -> None:
        shown = min(self.total_seconds, int(elapsed_seconds))
        delta = shown - self._shown
        if delta <= 0:
            return
        self._shown = shown
        if self._bar is not None:
            self._bar.update(delta)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._bar is not None:
            self._bar.close()
