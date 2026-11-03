"""Small in-process sliding-window rate limiter.

Limitation (documented in the TDD): state is per process, so with N API instances the
effective limit is N times higher. Fine for one instance; swap for a shared store (Redis)
before scaling out.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException


class RateLimiter:
    def __init__(self, max_events: int, window_seconds: float) -> None:
        self._max = max_events
        self._window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        """Record an event for `key`; raise 429 with Retry-After when over the limit."""
        now = time.monotonic()
        q = self._events[key]
        while q and now - q[0] > self._window:
            q.popleft()
        if len(q) >= self._max:
            retry_after = max(1, int(self._window - (now - q[0])))
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        q.append(now)

    def reset(self) -> None:
        self._events.clear()
