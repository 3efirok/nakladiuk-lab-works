"""Validation and filtering stages."""

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from experiment_registry.data import PARAMETERS
from experiment_registry.exceptions import ExperimentValidationError
from experiment_registry.models import Experiment
from experiment_registry.streaming.parsers import RawRow, to_experiment


@dataclass
class StreamStats:
    """Counters filled while the stream is being consumed."""

    read: int = 0
    valid: int = 0
    invalid: int = 0
    reasons: Counter[str] = field(default_factory=Counter)


def validate(rows: Iterable[RawRow], stats: StreamStats | None = None) -> Iterator[Experiment]:
    """Streaming validation: yield valid experiments, count and skip invalid rows."""
    stats = stats if stats is not None else StreamStats()
    for row in rows:
        stats.read += 1
        try:
            if len(row) != 6:
                raise ExperimentValidationError("wrong number of fields")
            experiment = to_experiment(row)
            if experiment.parameter not in PARAMETERS:
                raise ExperimentValidationError(f"unknown parameter {experiment.parameter!r}")
        except (ValueError, KeyError, ExperimentValidationError) as error:
            stats.invalid += 1
            stats.reasons[type(error).__name__] += 1
            continue
        stats.valid += 1
        yield experiment


def filter_by_researcher(experiments: Iterable[Experiment], researcher: str | None) -> Iterator[Experiment]:
    """Keep experiments of one researcher (no-op when researcher is None)."""
    if researcher is None:
        yield from experiments
        return
    wanted = researcher.lower()
    yield from (item for item in experiments if item.researcher.lower() == wanted)


def filter_by_parameter(experiments: Iterable[Experiment], parameter: str | None) -> Iterator[Experiment]:
    if parameter is None:
        yield from experiments
        return
    yield from (item for item in experiments if item.parameter == parameter)


def filter_by_range(
    experiments: Iterable[Experiment], low: float | None, high: float | None
) -> Iterator[Experiment]:
    """Keep results inside [low, high]; open bounds are allowed."""
    lower = float("-inf") if low is None else low
    upper = float("inf") if high is None else high
    for item in experiments:
        if lower <= item.result <= upper:
            yield item
