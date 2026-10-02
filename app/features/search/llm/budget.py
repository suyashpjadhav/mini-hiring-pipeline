"""Sliding-window budget limiter and LRU cache for LLM fallback (SYSTEM_DESIGN §12)."""

import time
from collections import OrderedDict

from app.features.search.llm.interpreter import LLMResult


class LLMBudget:
    """In-process sliding-window rate limiter for LLM calls."""

    def __init__(self, max_calls_per_min: int = 30) -> None:
        self.max_calls_per_min = max_calls_per_min
        self.timestamps: list[float] = []

    def allow_call(self, now_ts: float | None = None) -> bool:
        """Check if a call is allowed within the 60s sliding window."""
        if now_ts is None:
            now_ts = time.time()

        window_start = now_ts - 60.0
        self.timestamps = [t for t in self.timestamps if t > window_start]

        if len(self.timestamps) < self.max_calls_per_min:
            self.timestamps.append(now_ts)
            return True
        return False


class LLMCache:
    """LRU cache for LLM interpretation results (capacity = 256)."""

    def __init__(self, capacity: int = 256) -> None:
        self.capacity = capacity
        self.cache: OrderedDict[tuple[str, str, str], LLMResult] = OrderedDict()

    def get(self, key: tuple[str, str, str]) -> LLMResult | None:
        """Get cached result if key exists, updating LRU order."""
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: tuple[str, str, str], result: LLMResult) -> None:
        """Put result into cache, evicting oldest item if capacity is exceeded."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = result
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clear cache contents."""
        self.cache.clear()
