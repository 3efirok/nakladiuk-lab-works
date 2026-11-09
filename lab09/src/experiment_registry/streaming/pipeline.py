"""Composition of lazy stages into a pipeline, batching and early termination."""

from collections.abc import Callable, Iterable, Iterator
from itertools import islice
from pathlib import Path
from typing import TypeVar

from experiment_registry.models import Experiment
from experiment_registry.streaming.filters import (
    StreamStats,
    filter_by_parameter,
    filter_by_range,
    filter_by_researcher,
    validate,
)
from experiment_registry.streaming.parsers import clean_lines, normalize, parse_rows
from experiment_registry.streaming.readers import read_data_lines

T = TypeVar("T")


def build_pipeline(
    path: Path,
    researcher: str | None = None,
    parameter: str | None = None,
    low: float | None = None,
    high: float | None = None,
    stats: StreamStats | None = None,
) -> Iterator[Experiment]:
    """CSV -> read -> clean -> parse -> validate -> filter -> transform (all lazy)."""
    lines = read_data_lines(path)
    cleaned = clean_lines(lines)
    rows = parse_rows(cleaned)
    valid = validate(rows, stats)
    by_researcher = filter_by_researcher(valid, researcher)
    by_parameter = filter_by_parameter(by_researcher, parameter)
    in_range = filter_by_range(by_parameter, low, high)
    return normalize(in_range)


def take(items: Iterable[T], n: int) -> list[T]:
    """First n elements of a (possibly infinite) stream via islice."""
    return list(islice(items, n))


def batched(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """Split a stream into lists of `size` elements (the last batch may be shorter)."""
    if size < 1:
        raise ValueError("batch size must be >= 1")
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def find_first(items: Iterable[T], predicate: Callable[[T], bool]) -> T | None:
    """Lazy search with early termination: stops at the first match."""
    for item in items:
        if predicate(item):
            return item
    return None
