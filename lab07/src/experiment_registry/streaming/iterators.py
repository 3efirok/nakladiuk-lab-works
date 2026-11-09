"""Iterator protocol examples: custom iterator classes and recursive generators."""

from collections.abc import Iterable, Iterator, Sequence
from itertools import count
from typing import Any

from experiment_registry.models import Experiment


class ExperimentRecordIterator:
    """Iterator over experiments that skips results outside [low, high].

    Implements the iterator protocol directly: __iter__ returns self, __next__ returns
    the next suitable element or raises StopIteration. It can be consumed only once.
    """

    def __init__(self, experiments: Sequence[Experiment], low: float, high: float) -> None:
        self._experiments = experiments
        self._low = low
        self._high = high
        self._index = 0

    def __iter__(self) -> "ExperimentRecordIterator":
        return self

    def __next__(self) -> Experiment:
        while self._index < len(self._experiments):
            item = self._experiments[self._index]
            self._index += 1
            if self._low <= item.result <= self._high:
                return item
        raise StopIteration


class ResultSeries:
    """Iterable (not an iterator): every for-loop gets a fresh ResultSeriesIterator."""

    def __init__(self, results: Sequence[float]) -> None:
        self._results = list(results)

    def __iter__(self) -> "ResultSeriesIterator":
        return ResultSeriesIterator(self._results)

    def __len__(self) -> int:
        return len(self._results)


class ResultSeriesIterator:
    def __init__(self, results: list[float]) -> None:
        self._results = results
        self._position = 0

    def __iter__(self) -> "ResultSeriesIterator":
        return self

    def __next__(self) -> float:
        if self._position >= len(self._results):
            raise StopIteration
        value = self._results[self._position]
        self._position += 1
        return value


def flatten(values: Iterable[Any]) -> Iterator[Any]:
    """Recursive generator: flattens nested lists of measurement series via yield from."""
    for value in values:
        if isinstance(value, list):
            yield from flatten(value)
        else:
            yield value


def experiment_ids(start: int = 1) -> Iterator[str]:
    """Infinite generator of experiment codes: EXP-000001, EXP-000002, ..."""
    for number in count(start):
        yield f"EXP-{number:06d}"
