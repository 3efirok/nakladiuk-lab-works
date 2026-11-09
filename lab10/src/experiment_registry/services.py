"""Business logic of the experiment registry."""

from experiment_registry.exceptions import (
    DuplicateExperimentError,
    ExperimentValidationError,
)
from experiment_registry.models import Experiment, ResultStatistics


def add_experiment(experiments: list[Experiment], experiment: Experiment) -> None:
    """Add an experiment to the registry, rejecting duplicate IDs."""
    if any(item.experiment_id == experiment.experiment_id for item in experiments):
        raise DuplicateExperimentError(f"Experiment with ID {experiment.experiment_id} already exists.")
    experiments.append(experiment)


def next_experiment_id(experiments: list[Experiment]) -> int:
    """Return the next free experiment ID."""
    return max((item.experiment_id for item in experiments), default=0) + 1


def find_by_researcher(experiments: list[Experiment], researcher: str) -> list[Experiment]:
    """Return experiments of a researcher (case-insensitive match)."""
    wanted = researcher.strip().lower()
    return [item for item in experiments if item.researcher.lower() == wanted]


def filter_by_parameter(experiments: list[Experiment], parameter: str) -> list[Experiment]:
    """Return experiments that measured the given parameter."""
    wanted = parameter.strip().lower()
    return [item for item in experiments if item.parameter.lower() == wanted]


def calculate_average_result(experiments: list[Experiment]) -> float | None:
    """Return the mean result or None for an empty list."""
    if not experiments:
        return None
    return sum(item.result for item in experiments) / len(experiments)


def find_min_max(experiments: list[Experiment]) -> tuple[Experiment, Experiment] | None:
    """Return experiments with the minimum and the maximum result."""
    if not experiments:
        return None
    minimum = min(experiments, key=lambda item: item.result)
    maximum = max(experiments, key=lambda item: item.result)
    return minimum, maximum


def filter_by_result_range(
    experiments: list[Experiment],
    low: float,
    high: float,
) -> list[Experiment]:
    """Return experiments whose result lies in the closed range [low, high]."""
    if low > high:
        raise ExperimentValidationError(f"Invalid range: {low} > {high}.")
    return [item for item in experiments if low <= item.result <= high]


def search(
    experiments: list[Experiment],
    researcher: str | None = None,
    parameter: str | None = None,
) -> list[Experiment]:
    """Search experiments by several optional criteria."""
    result = experiments
    if researcher:
        result = find_by_researcher(result, researcher)
    if parameter:
        result = filter_by_parameter(result, parameter)
    return result


def sort_experiments(
    experiments: list[Experiment],
    key: str = "date",
    reverse: bool = False,
) -> list[Experiment]:
    """Return experiments sorted by date, result or name."""
    if key not in {"date", "result", "name"}:
        raise ExperimentValidationError(f"Unknown sort key: {key}.")
    return sorted(experiments, key=lambda item: getattr(item, key), reverse=reverse)


def calculate_statistics(experiments: list[Experiment]) -> ResultStatistics | None:
    """Return count, average, minimum and maximum of results."""
    average = calculate_average_result(experiments)
    bounds = find_min_max(experiments)
    if average is None or bounds is None:
        return None
    minimum, maximum = bounds
    return ResultStatistics(
        count=len(experiments),
        average=average,
        minimum=minimum.result,
        maximum=maximum.result,
    )
