"""Measurement helpers: timeit/perf_counter, cProfile and tracemalloc."""

import cProfile
import io
import pstats
import statistics
import time
import tracemalloc
from collections.abc import Callable
from typing import Any


def time_runs(func: Callable[[], Any], repeat: int = 5) -> list[float]:
    """Wall-clock time of several runs (seconds)."""
    runs = []
    for _ in range(repeat):
        start = time.perf_counter()
        func()
        runs.append(time.perf_counter() - start)
    return runs


def mean_time(runs: list[float]) -> float:
    return statistics.fmean(runs)


def profile_call(func: Callable[..., Any], *args: Any, top: int = 12,
                 sort: str = "tottime") -> tuple[Any, str]:
    """Run func under cProfile and return (result, formatted statistics)."""
    profiler = cProfile.Profile()
    result = profiler.runcall(func, *args)
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats(sort).print_stats(top)
    return result, stream.getvalue()


def peak_memory_mb(func: Callable[..., Any], *args: Any) -> tuple[Any, float]:
    """Peak memory allocated by Python objects during the call (tracemalloc)."""
    tracemalloc.start()
    try:
        result = func(*args)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak / 1024 / 1024
