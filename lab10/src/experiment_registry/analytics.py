"""Aggregation and statistics built from small higher-order functions."""

import json
from collections.abc import Callable, Iterable
from datetime import date
from typing import Any

from experiment_registry.decorators import (
    OPERATION_HISTORY,
    measure_time,
    record_operation,
    require_non_empty,
)
from experiment_registry.models import Experiment
from experiment_registry.processors import group_by_researcher

# (researcher, count, average, minimum, maximum)
ResearcherStats = tuple[str, int, float, float, float]


@record_operation(OPERATION_HISTORY, "average")
@measure_time
@require_non_empty
def average_result(experiments: list[Experiment]) -> float:
    """Mean result of experiments (None for an empty list)."""
    return sum(item.result for item in experiments) / len(experiments)


@record_operation(OPERATION_HISTORY, "min/max")
@require_non_empty
def min_max_result(experiments: list[Experiment]) -> tuple[float, float]:
    """Return (minimum, maximum) result as a tuple."""
    results = [item.result for item in experiments]
    return min(results), max(results)


def average_of(*values: float) -> float:
    """Average of any number of positional values (*args)."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def create_experiment(**fields: Any) -> Experiment:
    """Create an Experiment from keyword arguments (**kwargs)."""
    if isinstance(fields.get("date"), str):
        fields["date"] = date.fromisoformat(fields["date"])
    return Experiment(**fields)


def make_range_filter(low: float, high: float) -> Callable[[Experiment], bool]:
    """Closure: predicate that remembers `low` and `high`."""
    if low > high:
        raise ValueError(f"Invalid range: {low} > {high}")

    def in_range(item: Experiment) -> bool:
        return low <= item.result <= high

    return in_range


def make_parameter_filter(parameter: str) -> Callable[[Experiment], bool]:
    """Closure: predicate for a measured parameter."""
    wanted = parameter.lower()
    return lambda item: item.parameter.lower() == wanted


def make_counter() -> Callable[[], int]:
    """Closure with mutable state via nonlocal: counts calls."""
    calls = 0

    def increment() -> int:
        nonlocal calls
        calls += 1
        return calls

    return increment


@record_operation(OPERATION_HISTORY, "ranking")
def rank_results(
    experiments: Iterable[Experiment], top: int | None = None, descending: bool = True
) -> list[tuple[int, Experiment]]:
    """Ranking of results: list of (place, experiment) tuples."""
    ordered = sorted(experiments, key=lambda item: item.result, reverse=descending)
    ranking = list(enumerate(ordered, start=1))
    return ranking[:top] if top else ranking


@record_operation(OPERATION_HISTORY, "researcher stats")
def researcher_statistics(experiments: Iterable[Experiment]) -> dict[str, ResearcherStats]:
    """Dict comprehension over groups: researcher -> (name, count, avg, min, max)."""
    groups = group_by_researcher(experiments)
    return {
        name: (
            name,
            len(items),
            average_of(*(item.result for item in items)),
            min(item.result for item in items),
            max(item.result for item in items),
        )
        for name, items in groups.items()
    }


def export_summary(experiments: list[Experiment], **options: Any) -> str:
    """Build a JSON summary; options: indent, top (size of ranking)."""
    indent = options.get("indent", 2)
    top = options.get("top", 3)
    bounds = min_max_result(experiments)
    summary = {
        "count": len(experiments),
        "researchers": sorted({item.researcher for item in experiments}),
        "average": round(sum(item.result for item in experiments) / len(experiments), 3)
        if experiments
        else None,
        "min_max": list(bounds) if bounds else None,
        "top": [
            {"place": place, "id": item.experiment_id, "result": item.result}
            for place, item in rank_results(experiments, top=top)
        ],
    }
    return json.dumps(summary, indent=indent, ensure_ascii=False)
