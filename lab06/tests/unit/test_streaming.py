"""Tests for the lab 3 streaming pipeline."""

from itertools import islice
from pathlib import Path

import pytest

from experiment_registry.streaming.analytics import aggregate, pairwise_differences, running_average
from experiment_registry.streaming.filters import StreamStats
from experiment_registry.streaming.iterators import ExperimentRecordIterator, experiment_ids, flatten
from experiment_registry.streaming.pipeline import batched, build_pipeline, find_first, take


def test_pipeline_validates_and_aggregates_stream(csv_file: Path) -> None:
    stats = StreamStats()

    summary = aggregate(build_pipeline(csv_file, stats=stats))

    assert (stats.read, stats.valid, stats.invalid) == (4, 3, 1)
    assert summary.count == 3
    assert summary.maximum is not None and summary.maximum.result == 301.8


def test_pipeline_filters_by_researcher_and_range(csv_file: Path) -> None:
    items = list(build_pipeline(csv_file, researcher="olena kovalenko", low=300, high=310))

    assert [item.result for item in items] == [301.8]


def test_pipeline_is_lazy(tmp_path: Path) -> None:
    pipeline = build_pipeline(tmp_path / "does_not_exist.csv")  # nothing is read yet

    with pytest.raises(FileNotFoundError):
        next(pipeline)


@pytest.mark.parametrize(("size", "expected"), [(1, [1, 1, 1, 1, 1]), (2, [2, 2, 1]), (5, [5]), (10, [5])])
def test_batched_splits_stream(size: int, expected: list[int]) -> None:
    assert [len(batch) for batch in batched(range(5), size)] == expected


def test_batched_rejects_zero_size() -> None:
    with pytest.raises(ValueError):
        list(batched([1], 0))


def test_infinite_generator_with_take_and_find_first() -> None:
    assert take(experiment_ids(), 2) == ["EXP-000001", "EXP-000002"]
    assert find_first(experiment_ids(), lambda code: code.endswith("10")) == "EXP-000010"
    assert find_first(iter([]), bool) is None


def test_iterators_and_itertools_helpers(csv_file: Path) -> None:
    experiments = list(build_pipeline(csv_file))
    iterator = ExperimentRecordIterator(experiments, 290, 300)

    assert [item.result for item in iterator] == [293.4]
    assert list(iterator) == []  # exhausted
    assert list(flatten([1, [2, [3, 4]], 5])) == [1, 2, 3, 4, 5]
    assert [d for *_, d in pairwise_differences(experiments)] == [8.4, -200.5]
    assert list(islice(running_average([2.0, 4.0, 6.0]), 3)) == [2.0, 3.0, 4.0]
