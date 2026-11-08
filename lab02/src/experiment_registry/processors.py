"""Structural operations: indexing, search, filtering, grouping, sorting."""

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from typing import Any

from experiment_registry.models import Experiment

Predicate = Callable[[Experiment], bool]


def get_unique_researchers(experiments: Iterable[Experiment]) -> set[str]:
    """Set comprehension: unique researchers. O(n)."""
    return {item.researcher for item in experiments}


def build_index_by_id(experiments: Iterable[Experiment]) -> dict[int, Experiment]:
    """Dict comprehension: experiment_id -> experiment. Build O(n), lookup O(1)."""
    return {item.experiment_id: item for item in experiments}


def build_index_by_name(experiments: Iterable[Experiment]) -> dict[str, Experiment]:
    """Dict comprehension: lower-case name -> experiment."""
    return {item.name.lower(): item for item in experiments}


def find_by_id_linear(experiments: list[Experiment], experiment_id: int) -> Experiment | None:
    """Linear search in a list. O(n)."""
    for item in experiments:
        if item.experiment_id == experiment_id:
            return item
    return None


def find_by_researcher(experiments: Iterable[Experiment], researcher: str) -> list[Experiment]:
    """List comprehension: all experiments of a researcher."""
    wanted = researcher.lower()
    return [item for item in experiments if item.researcher.lower() == wanted]


def filter_records(experiments: Iterable[Experiment], *predicates: Predicate) -> list[Experiment]:
    """Universal filter: keep records that satisfy all predicates (*args)."""
    return [item for item in experiments if all(check(item) for check in predicates)]


def sort_records(experiments: Iterable[Experiment], *fields: str, reverse: bool = False) -> list[Experiment]:
    """Universal sort by one or several attribute names. O(n log n)."""
    if not fields:
        fields = ("experiment_id",)
    return sorted(experiments, key=lambda item: tuple(getattr(item, f) for f in fields), reverse=reverse)


def group_by_researcher(experiments: Iterable[Experiment]) -> dict[str, list[Experiment]]:
    """Group experiments by researcher using defaultdict(list). O(n)."""
    groups: defaultdict[str, list[Experiment]] = defaultdict(list)
    for item in experiments:
        groups[item.researcher].append(item)
    return dict(groups)


def group_nested(experiments: Iterable[Experiment]) -> dict[str, dict[str, list[float]]]:
    """Nested grouping: researcher -> parameter -> list of results."""
    groups: defaultdict[str, defaultdict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for item in experiments:
        groups[item.researcher][item.parameter].append(item.result)
    return {name: dict(params) for name, params in groups.items()}


def count_by_parameter(experiments: Iterable[Experiment]) -> Counter[str]:
    """Counter: number of experiments for each measured parameter."""
    return Counter(item.parameter for item in experiments)


def pipeline(data: Any, *steps: Callable[[Any], Any]) -> Any:
    """Apply processing steps one after another (functional pipeline)."""
    for step in steps:
        data = step(data)
    return data
