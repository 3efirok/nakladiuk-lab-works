"""Caching of repeated statistics for an unchanged dataset, with invalidation."""

from collections.abc import Iterable

import numpy as np

from experiment_registry.performance.analytics import Statistics, numpy_statistics


class CachedStatistics:
    """Keeps results in a NumPy array; statistics are recomputed only after a change.

    Every modification increments `version`; the cache key is the version, so a stale
    result can never be returned (cache invalidation).
    """

    def __init__(self, values: Iterable[float]) -> None:
        self._values = np.fromiter(values, dtype=np.float64)
        self.version = 0
        self._cache: dict[int, Statistics] = {}
        self.hits = 0
        self.misses = 0

    def statistics(self) -> Statistics:
        cached = self._cache.get(self.version)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        result = numpy_statistics(self._values)
        self._cache = {self.version: result}  # keep only the current version
        return result

    def add(self, value: float) -> None:
        self._values = np.append(self._values, value)
        self.version += 1

    def update(self, index: int, value: float) -> None:
        self._values[index] = value
        self.version += 1

    def __len__(self) -> int:
        return int(self._values.size)
