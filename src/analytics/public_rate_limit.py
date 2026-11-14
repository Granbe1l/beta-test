"""Thread-safe process-level request budget for uncached public GitHub previews.

A new uncached inspection may issue up to four unauthenticated REST GETs.
A rolling 12-inspection/hour server-process cap leaves headroom against the
common 60-request/hour unauthenticated IP bucket. This cap is *not* a distributed
limit across replicas or a promise of GitHub API availability.
"""
from __future__ import annotations

from collections import deque
from math import ceil
import threading
import time
from typing import Callable


class RollingInspectionBudget:
    def __init__(self, limit: int = 12, window_seconds: int = 3600,
                 clock: Callable[[], float] | None = None):
        if limit < 1 or window_seconds < 1:
            raise ValueError("rate-limit size and window must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock or time.monotonic
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def try_acquire(self) -> tuple[bool, int]:
        """Return (allowed, seconds_to_retry), never negative or unbounded."""
        with self._lock:
            now = self._clock()
            while self._timestamps and (
                now - self._timestamps[0] >= self.window_seconds
            ):
                self._timestamps.popleft()
            if len(self._timestamps) >= self.limit:
                wait = self.window_seconds - (now - self._timestamps[0])
                return False, max(1, ceil(wait))
            self._timestamps.append(now)
            return True, 0

    def used(self) -> int:
        with self._lock:
            now = self._clock()
            while self._timestamps and (
                now - self._timestamps[0] >= self.window_seconds
            ):
                self._timestamps.popleft()
            return len(self._timestamps)
