"""Threads and processes: chunked parallel statistics, parallel file loading, synchronization."""

import csv
import math
import multiprocessing
import multiprocessing.context
import threading
import time
from collections.abc import Sequence
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from experiment_registry.performance.analytics import Statistics

# (count, mean, M2, minimum, maximum) - partial result of Welford's algorithm
Partial = tuple[int, float, float, float, float]


def chunk(values: Sequence[float], parts: int) -> list[list[float]]:
    """Split data into `parts` nearly equal contiguous chunks."""
    size = math.ceil(len(values) / parts)
    return [list(values[i : i + size]) for i in range(0, len(values), size)]


def partial_moments(values: Sequence[float]) -> Partial:
    """One pass over a chunk (runs inside a worker)."""
    count, mean, m2 = 0, 0.0, 0.0
    minimum = maximum = values[0]
    for value in values:
        count += 1
        delta = value - mean
        mean += delta / count
        m2 += delta * (value - mean)
        if value < minimum:
            minimum = value
        elif value > maximum:
            maximum = value
    return count, mean, m2, minimum, maximum


def merge_moments(parts: Sequence[Partial]) -> Partial:
    """Combine partial results (Chan et al. parallel variance)."""
    count, mean, m2, minimum, maximum = parts[0]
    for n, part_mean, part_m2, part_min, part_max in parts[1:]:
        total = count + n
        delta = part_mean - mean
        mean += delta * n / total
        m2 += part_m2 + delta * delta * count * n / total
        count = total
        minimum, maximum = min(minimum, part_min), max(maximum, part_max)
    return count, mean, m2, minimum, maximum


def count_outliers(values: Sequence[float], mean: float, std: float) -> int:
    return sum(1 for value in values if abs((value - mean) / std) > 3)


def parallel_statistics(values: Sequence[float], executor: Executor, workers: int) -> Statistics:
    """Map-reduce over chunks with any executor (threads or processes)."""
    chunks = chunk(values, workers)
    count, mean, m2, minimum, maximum = merge_moments(list(executor.map(partial_moments, chunks)))
    std = math.sqrt(m2 / (count - 1))
    outliers = sum(executor.map(count_outliers, chunks, [mean] * len(chunks), [std] * len(chunks)))
    return Statistics(count, mean, minimum, maximum, std, outliers)


def threaded_statistics(values: Sequence[float], workers: int = 4) -> Statistics:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return parallel_statistics(values, executor, workers)


def process_context() -> multiprocessing.context.BaseContext:
    """forkserver/spawn: fork() in a multi-threaded process (e.g. inside a web server) is unsafe."""
    methods = multiprocessing.get_all_start_methods()
    return multiprocessing.get_context("forkserver" if "forkserver" in methods else "spawn")


def process_statistics(values: Sequence[float], workers: int = 4) -> Statistics:
    with ProcessPoolExecutor(max_workers=workers, mp_context=process_context()) as executor:
        return parallel_statistics(values, executor, workers)


# --------------------------------------------------- I/O-bound: loading files
def write_dataset_files(directory: Path, files: int, rows: int) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for index in range(files):
        path = directory / f"series_{index + 1}.csv"
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["experiment_id", "result"])
            writer.writerows((i, round(290 + (i * 7 + index) % 40 + 0.5, 3)) for i in range(rows))
        paths.append(path)
    return paths


def load_series(path: Path, latency: float = 0.0) -> list[float]:
    """Read one data file; `latency` imitates slow network storage (I/O wait)."""
    if latency:
        time.sleep(latency)
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        next(reader)
        return [float(row[1]) for row in reader]


def load_sequential(paths: Sequence[Path], latency: float = 0.0) -> list[list[float]]:
    return [load_series(path, latency) for path in paths]


def load_threaded(
    paths: Sequence[Path], workers: int = 4, latency: float = 0.0, progress: "ProgressCounter | None" = None
) -> list[list[float]]:
    def task(path: Path) -> list[float]:
        data = load_series(path, latency)
        if progress is not None:
            progress.increment()
        return data

    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(task, paths))


# ------------------------------------------------------------ synchronization
class ProgressCounter:
    """Shared mutable counter protected by a Lock."""

    def __init__(self) -> None:
        self.value = 0
        self._lock = threading.Lock()

    def increment(self) -> None:
        with self._lock:
            current = self.value
            time.sleep(0)  # give other threads a chance to run between read and write
            self.value = current + 1


class UnsafeCounter:
    """The same read-modify-write without a lock: updates can be lost (race condition)."""

    def __init__(self) -> None:
        self.value = 0

    def increment(self) -> None:
        current = self.value
        time.sleep(0)
        self.value = current + 1


def hammer(counter: "ProgressCounter | UnsafeCounter", threads: int = 8, increments: int = 1000) -> int:
    def work() -> None:
        for _ in range(increments):
            counter.increment()

    pool = [threading.Thread(target=work) for _ in range(threads)]
    for thread in pool:
        thread.start()
    for thread in pool:
        thread.join()
    return counter.value
