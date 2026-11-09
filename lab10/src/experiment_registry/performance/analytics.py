"""The same statistics implemented with Python loops (baseline) and with NumPy."""

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Statistics:
    count: int
    mean: float
    minimum: float
    maximum: float
    std: float
    outliers: int  # |z| > 3

    def close_to(self, other: "Statistics", rel: float = 1e-9) -> bool:
        return (
            self.count == other.count
            and self.outliers == other.outliers
            and all(
                math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)
                for a, b in (
                    (self.mean, other.mean),
                    (self.minimum, other.minimum),
                    (self.maximum, other.maximum),
                    (self.std, other.std),
                )
            )
        )


@dataclass(frozen=True)
class Dataset:
    """Large synthetic set of experiment results (columns as Python lists)."""

    researchers: list[int]
    results: list[float]

    def as_numpy(self) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
        return np.asarray(self.researchers, dtype=np.int64), np.asarray(self.results, dtype=np.float64)


def generate_dataset(size: int, researchers: int = 8, seed: int = 15) -> Dataset:
    rng = random.Random(seed)
    return Dataset(
        researchers=[rng.randrange(researchers) for _ in range(size)],
        results=[rng.gauss(300.0, 25.0) for _ in range(size)],
    )


# ------------------------------------------------------------- Python baseline
def python_mean(values: Sequence[float]) -> float:
    total = 0.0
    for value in values:
        total += value
    return total / len(values)


def python_min_max(values: Sequence[float]) -> tuple[float, float]:
    minimum = maximum = values[0]
    for value in values:
        if value < minimum:
            minimum = value
        elif value > maximum:
            maximum = value
    return minimum, maximum


def python_std(values: Sequence[float], mean: float) -> float:
    squares = 0.0
    for value in values:
        squares += (value - mean) ** 2
    return math.sqrt(squares / (len(values) - 1))


def python_outliers(values: Sequence[float], mean: float, std: float) -> int:
    count = 0
    for value in values:
        if abs((value - mean) / std) > 3:
            count += 1
    return count


def python_statistics(values: Sequence[float]) -> Statistics:
    """Baseline: several passes over the data with Python loops."""
    if len(values) < 2:
        raise ValueError("at least two values are required")
    mean = python_mean(values)
    minimum, maximum = python_min_max(values)
    std = python_std(values, mean)
    return Statistics(len(values), mean, minimum, maximum, std, python_outliers(values, mean, std))


def python_range_filter(values: Sequence[float], low: float, high: float) -> list[float]:
    return [value for value in values if low <= value <= high]


def python_researcher_stats(
    researchers: Sequence[int], values: Sequence[float]
) -> dict[int, tuple[int, float]]:
    """researcher -> (count, mean)."""
    totals: dict[int, list[float]] = {}
    for researcher, value in zip(researchers, values, strict=True):
        entry = totals.setdefault(researcher, [0.0, 0.0])
        entry[0] += 1
        entry[1] += value
    return {key: (int(count), total / count) for key, (count, total) in sorted(totals.items())}


# ------------------------------------------------------------------- NumPy
def numpy_statistics(values: NDArray[np.float64]) -> Statistics:
    """Vectorized: every loop runs in optimized C code inside NumPy."""
    if values.size < 2:
        raise ValueError("at least two values are required")
    mean = float(values.mean())
    std = float(values.std(ddof=1))
    outliers = int(np.count_nonzero(np.abs((values - mean) / std) > 3))
    return Statistics(int(values.size), mean, float(np.min(values)), float(np.max(values)), std, outliers)


def numpy_range_filter(values: NDArray[np.float64], low: float, high: float) -> NDArray[np.float64]:
    return values[(values >= low) & (values <= high)]


def numpy_researcher_stats(
    researchers: NDArray[np.int64], values: NDArray[np.float64]
) -> dict[int, tuple[int, float]]:
    counts = np.bincount(researchers)
    sums = np.bincount(researchers, weights=values)
    return {int(i): (int(counts[i]), float(sums[i] / counts[i])) for i in np.flatnonzero(counts)}


def analyze_dataset(dataset: Dataset, low: float = 250.0, high: float = 350.0) -> dict[str, object]:
    """Full baseline analysis used for profiling."""
    return {
        "statistics": python_statistics(dataset.results),
        "in_range": len(python_range_filter(dataset.results, low, high)),
        "by_researcher": python_researcher_stats(dataset.researchers, dataset.results),
    }
