"""Tests for the lab 1-2 core: Experiment record, services, processors and analytics."""

from datetime import date

import pytest

from experiment_registry.analytics import (
    average_of,
    create_experiment,
    make_counter,
    make_range_filter,
    rank_results,
    researcher_statistics,
)
from experiment_registry.data import load_experiments
from experiment_registry.exceptions import DuplicateExperimentError, ExperimentValidationError
from experiment_registry.models import Experiment
from experiment_registry.processors import (
    build_index_by_id,
    count_by_parameter,
    filter_records,
    find_by_id_linear,
    get_unique_researchers,
    group_by_researcher,
    sort_records,
)
from experiment_registry.services import (
    add_experiment,
    calculate_statistics,
    filter_by_result_range,
    find_by_researcher,
    find_min_max,
)


@pytest.fixture
def experiments() -> list[Experiment]:
    return load_experiments()


def test_experiment_record_validates_result_range() -> None:
    with pytest.raises(ExperimentValidationError):
        Experiment(1, "Too big", "Olena Kovalenko", "temperature", 2e6, date(2026, 1, 1))


def test_add_experiment_rejects_duplicate_id(experiments: list[Experiment]) -> None:
    with pytest.raises(DuplicateExperimentError):
        add_experiment(experiments, experiments[0])


def test_statistics_of_empty_list_is_none() -> None:
    assert calculate_statistics([]) is None
    assert find_min_max([]) is None


def test_statistics_for_researcher(experiments: list[Experiment]) -> None:
    stats = calculate_statistics(find_by_researcher(experiments, "olena kovalenko"))

    assert stats is not None
    assert (stats.count, stats.minimum, stats.maximum) == (4, 293.4, 412.5)
    assert stats.average == pytest.approx(339.15)


def test_filter_by_result_range_rejects_inverted_range(experiments: list[Experiment]) -> None:
    with pytest.raises(ExperimentValidationError):
        filter_by_result_range(experiments, 10, 1)


def test_dict_index_and_linear_search_return_same_object(experiments: list[Experiment]) -> None:
    index = build_index_by_id(experiments)

    assert all(find_by_id_linear(experiments, key) is value for key, value in index.items())
    assert find_by_id_linear(experiments, 999) is None


def test_grouping_counting_and_unique_researchers(experiments: list[Experiment]) -> None:
    groups = group_by_researcher(experiments)

    assert get_unique_researchers(experiments) == set(groups)
    assert sum(len(items) for items in groups.values()) == len(experiments)
    assert count_by_parameter(experiments).most_common(1) == [("temperature", 7)]


def test_universal_filter_sort_and_closure(experiments: list[Experiment]) -> None:
    selected = filter_records(
        experiments, make_range_filter(290, 310), lambda e: e.parameter == "temperature"
    )

    assert [e.experiment_id for e in sort_records(selected, "result")] == [1, 14, 3]


def test_ranking_researcher_statistics_and_helpers(experiments: list[Experiment]) -> None:
    assert rank_results(experiments, top=1)[0][1].experiment_id == 12
    assert researcher_statistics(experiments)["Andrii Bondar"][1] == 2
    assert average_of() == 0.0 and average_of(1, 2, 3) == 2.0
    assert create_experiment(
        experiment_id=99, name="X", researcher="R", parameter="p", result=1.0, date="2026-01-01"
    ).date == date(2026, 1, 1)
    counter = make_counter()
    counter()
    assert counter() == 2
