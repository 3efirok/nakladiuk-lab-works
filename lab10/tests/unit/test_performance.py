"""Correctness of optimized implementations (lab 9): every variant must give the same result."""

from pathlib import Path

import pytest

from experiment_registry.performance.analytics import (
    Dataset,
    generate_dataset,
    numpy_range_filter,
    numpy_researcher_stats,
    numpy_statistics,
    python_range_filter,
    python_researcher_stats,
    python_statistics,
)
from experiment_registry.performance.caching import CachedStatistics
from experiment_registry.performance.parallel import (
    ProgressCounter,
    chunk,
    hammer,
    load_sequential,
    load_threaded,
    merge_moments,
    partial_moments,
    process_statistics,
    threaded_statistics,
    write_dataset_files,
)
from experiment_registry.performance.profiling import mean_time, peak_memory_mb, profile_call, time_runs


@pytest.fixture(scope="module")
def dataset() -> Dataset:
    return generate_dataset(20_000, seed=7)


def test_numpy_statistics_equal_python_baseline(dataset: Dataset) -> None:
    _, values = dataset.as_numpy()

    assert numpy_statistics(values).close_to(python_statistics(dataset.results))


@pytest.mark.parametrize("workers", [1, 3, 4])
def test_threaded_statistics_equal_baseline(dataset: Dataset, workers: int) -> None:
    assert threaded_statistics(dataset.results, workers).close_to(
        python_statistics(dataset.results), rel=1e-9
    )


def test_process_statistics_equal_baseline(dataset: Dataset) -> None:
    assert process_statistics(dataset.results, 2).close_to(python_statistics(dataset.results), rel=1e-9)


def test_merging_partial_moments_equals_single_pass() -> None:
    values = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
    merged = merge_moments([partial_moments(part) for part in chunk(values, 3)])

    assert merged[0] == len(values)
    assert merged[1:] == pytest.approx(partial_moments(values)[1:])


@pytest.mark.parametrize(
    ("size", "parts", "expected"), [(10, 3, [4, 4, 2]), (4, 4, [1, 1, 1, 1]), (3, 5, [1, 1, 1])]
)
def test_chunk_sizes(size: int, parts: int, expected: list[int]) -> None:
    assert [len(part) for part in chunk([0.0] * size, parts)] == expected


def test_range_filter_and_researcher_stats_match(dataset: Dataset) -> None:
    researchers, values = dataset.as_numpy()

    assert numpy_range_filter(values, 280, 320).tolist() == python_range_filter(dataset.results, 280, 320)
    py_stats = python_researcher_stats(dataset.researchers, dataset.results)
    np_stats = numpy_researcher_stats(researchers, values)
    assert py_stats.keys() == np_stats.keys()
    assert all(
        py_stats[k][0] == np_stats[k][0] and py_stats[k][1] == pytest.approx(np_stats[k][1]) for k in py_stats
    )


def test_statistics_require_two_values() -> None:
    with pytest.raises(ValueError):
        python_statistics([1.0])


def test_cache_returns_same_object_until_invalidated() -> None:
    cached = CachedStatistics([1.0, 2.0, 3.0])
    first = cached.statistics()

    assert cached.statistics() is first and (cached.hits, cached.misses) == (1, 1)
    cached.add(10.0)
    assert cached.statistics().maximum == 10.0 and cached.version == 1
    cached.update(0, -5.0)
    assert cached.statistics().minimum == -5.0 and cached.misses == 3 and len(cached) == 4


def test_lock_prevents_lost_updates() -> None:
    assert hammer(ProgressCounter(), threads=4, increments=200) == 800


def test_threaded_loading_returns_same_data(tmp_path: Path) -> None:
    paths = write_dataset_files(tmp_path, files=3, rows=100)
    counter = ProgressCounter()

    assert load_threaded(paths, workers=3, progress=counter) == load_sequential(paths)
    assert counter.value == 3


def test_profiling_helpers() -> None:
    result, report = profile_call(sum, [1, 2, 3])
    _, peak = peak_memory_mb(lambda: [0] * 10_000)

    assert result == 6 and "function calls" in report
    assert peak > 0
    assert len(time_runs(lambda: None, 3)) == 3 and mean_time([1.0, 3.0]) == 2.0
