"""Eager vs lazy processing: elapsed time, peak memory, time to first result.

Run from the project root:  python benchmarks/benchmark_streaming.py
Test files are generated into data/generated/ (ignored by Git).
"""

import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

from experiment_registry.streaming.analytics import aggregate
from experiment_registry.streaming.datagen import generate_test_file
from experiment_registry.streaming.eager import eager_filter
from experiment_registry.streaming.pipeline import build_pipeline, find_first

DATA_DIR = Path("data/generated")
SIZES = (10_000, 100_000, 500_000)
LOW, HIGH = 100.0, 300.0
REPEATS = 3


def ensure_file(count: int) -> Path:
    path = DATA_DIR / f"experiments_{count}.csv"
    if not path.exists():
        generate_test_file(path, count)
    return path


def eager_average(path: Path) -> tuple[int, float]:
    items = eager_filter(path, LOW, HIGH)
    return len(items), sum(item.result for item in items) / len(items)


def lazy_average(path: Path) -> tuple[int, float]:
    stats = aggregate(build_pipeline(path, low=LOW, high=HIGH))
    return stats.count, stats.average or 0.0


def best_time(func: Callable[[Path], Any], path: Path) -> tuple[float, Any]:
    timings, result = [], None
    for _ in range(REPEATS):
        start = time.perf_counter()
        result = func(path)
        timings.append(time.perf_counter() - start)
    return min(timings), result


def peak_memory(func: Callable[[Path], Any], path: Path) -> float:
    """Peak traced memory in MB; the pipeline is fully consumed inside func."""
    tracemalloc.start()
    func(path)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024 / 1024


def first_result_time(path: Path, lazy: bool) -> float:
    start = time.perf_counter()
    if lazy:
        next(build_pipeline(path, low=LOW, high=HIGH))
    else:
        eager_filter(path, LOW, HIGH)[0]
    return (time.perf_counter() - start) * 1000


def main() -> None:
    print(f"Filter: result in [{LOW}, {HIGH}]; time = best of {REPEATS} runs")
    print(f"{'Records':>8} | {'Eager, s':>8} | {'Lazy, s':>7} | {'Eager peak, MB':>14} | "
          f"{'Lazy peak, MB':>13} | {'Eager 1st, ms':>13} | {'Lazy 1st, ms':>12} | matched")
    for size in SIZES:
        path = ensure_file(size)
        eager_t, eager_res = best_time(eager_average, path)
        lazy_t, lazy_res = best_time(lazy_average, path)
        assert eager_res[0] == lazy_res[0] and abs(eager_res[1] - lazy_res[1]) < 1e-6
        print(f"{size:>8,} | {eager_t:>8.3f} | {lazy_t:>7.3f} | "
              f"{peak_memory(eager_average, path):>14.2f} | {peak_memory(lazy_average, path):>13.3f} | "
              f"{first_result_time(path, False):>13.1f} | {first_result_time(path, True):>12.3f} | "
              f"{lazy_res[0]:,}")

    print("\nEarly termination on 1,000,000 records: first experiment of Sofiia Romaniuk with result > 4990")
    path = ensure_file(1_000_000)

    def predicate(item: Any) -> bool:
        return item.researcher == "Sofiia Romaniuk" and item.result > 4990

    def lazy_search(p: Path) -> Any:
        return find_first(build_pipeline(p), predicate)

    def eager_search(p: Path) -> Any:
        matches = [item for item in eager_filter(p, float("-inf"), float("inf")) if predicate(item)]
        return matches[0] if matches else None

    lazy_t, lazy_found = best_time(lazy_search, path)
    eager_t, eager_found = best_time(eager_search, path)
    assert lazy_found.experiment_id == eager_found.experiment_id
    print(f"  found #{lazy_found.experiment_id} (result {lazy_found.result})")
    print(f"  lazy : {lazy_t * 1000:9.1f} ms, peak {peak_memory(lazy_search, path):8.3f} MB")
    print(f"  eager: {eager_t * 1000:9.1f} ms, peak {peak_memory(eager_search, path):8.2f} MB")


if __name__ == "__main__":
    main()
