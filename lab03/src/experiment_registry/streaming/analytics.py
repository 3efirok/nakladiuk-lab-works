"""Streaming aggregation: one pass, O(1) memory."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import accumulate, groupby, pairwise

from experiment_registry.models import Experiment


@dataclass
class RunningStats:
    """Streaming average / minimum / maximum (no list of values is stored)."""

    count: int = 0
    total: float = 0.0
    minimum: Experiment | None = None
    maximum: Experiment | None = None

    def add(self, item: Experiment) -> None:
        self.count += 1
        self.total += item.result
        if self.minimum is None or item.result < self.minimum.result:
            self.minimum = item
        if self.maximum is None or item.result > self.maximum.result:
            self.maximum = item

    @property
    def average(self) -> float | None:
        return self.total / self.count if self.count else None


def aggregate(experiments: Iterable[Experiment]) -> RunningStats:
    """Aggregation stage: consumes the whole stream."""
    stats = RunningStats()
    for item in experiments:
        stats.add(item)
    return stats


def pairwise_differences(experiments: Iterable[Experiment]) -> Iterator[tuple[int, int, float]]:
    """Difference between consecutive results: (previous_id, current_id, delta)."""
    for previous, current in pairwise(experiments):
        yield previous.experiment_id, current.experiment_id, round(current.result - previous.result, 3)


def running_average(values: Iterable[float]) -> Iterator[float]:
    """Cumulative average computed with itertools.accumulate."""
    for index, total in enumerate(accumulate(values), start=1):
        yield total / index


def count_consecutive_by_researcher(experiments: Iterable[Experiment]) -> Iterator[tuple[str, int]]:
    """itertools.groupby: lengths of consecutive runs of the same researcher."""
    for researcher, group in groupby(experiments, key=lambda item: item.researcher):
        yield researcher, sum(1 for _ in group)
