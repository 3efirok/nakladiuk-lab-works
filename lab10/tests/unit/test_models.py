from datetime import date, timedelta

import pytest

from experiment_registry.domain.models import Experiment, ExperimentResult, ExperimentSeries, Researcher
from experiment_registry.domain.value_objects import Measurement, ResultRange
from experiment_registry.exceptions import (
    ExperimentNotFoundError,
    ExperimentValidationError,
    IncompatibleMeasurementError,
)


def test_researcher_full_name_and_normalized_email() -> None:
    researcher = Researcher(7, "Iryna", "Melnyk", "  I.Melnyk@LNU.edu.ua ")

    assert researcher.full_name == "Iryna Melnyk"
    assert researcher.email == "i.melnyk@lnu.edu.ua"
    assert researcher.id == 7


@pytest.mark.parametrize("email", ["no-at-sign", "@lnu.edu.ua", "name@", ""])
def test_invalid_email_raises_validation_error(email: str) -> None:
    with pytest.raises(ExperimentValidationError, match="e-mail"):
        Researcher(1, "Olena", "Kovalenko", email)


def test_researcher_requires_positive_id_and_names() -> None:
    with pytest.raises(ExperimentValidationError):
        Researcher(0, "Olena", "Kovalenko", "o@lnu.edu.ua")
    with pytest.raises(ExperimentValidationError):
        Researcher(1, " ", "Kovalenko", "o@lnu.edu.ua")


def test_researchers_with_same_id_are_equal(researcher: Researcher) -> None:
    same = Researcher(1, "Olena", "Kovalenko-Shevchuk", "other@lnu.edu.ua")

    assert researcher == same and hash(researcher) == hash(same)


def test_experiment_result_rejects_future_date() -> None:
    with pytest.raises(ExperimentValidationError, match="future"):
        ExperimentResult(1, Measurement("temperature", 300.0, "K"), date.today() + timedelta(days=1))


def test_add_result_appends_compatible_measurement(experiment: Experiment) -> None:
    experiment.add_result(ExperimentResult(10, Measurement("temperature", 310.0, "K"), date(2026, 3, 1)))

    assert len(experiment) == 4
    assert experiment.values()[-1] == 310.0


def test_add_result_rejects_other_parameter(experiment: Experiment) -> None:
    """Regression test: a pressure value must not be stored in a temperature experiment."""
    wrong = ExperimentResult(11, Measurement("pressure", 101.3, "kPa"), date(2026, 3, 1))

    with pytest.raises(IncompatibleMeasurementError):
        experiment.add_result(wrong)
    assert len(experiment) == 3


def test_add_result_rejects_duplicate_result_id(experiment: Experiment) -> None:
    with pytest.raises(ExperimentValidationError, match="Duplicate"):
        experiment.add_result(ExperimentResult(1, Measurement("temperature", 1.0, "K"), date(2026, 3, 1)))


def test_results_property_is_read_only_view(experiment: Experiment) -> None:
    assert isinstance(experiment.results, tuple)


def test_results_in_range(experiment: Experiment) -> None:
    found = experiment.results_in(ResultRange(295, 305))

    assert [item.value for item in found] == [297.1, 301.8]


def test_empty_series_behaves_like_empty_collection() -> None:
    series = ExperimentSeries("Empty project")

    assert len(series) == 0
    assert list(series) == []
    assert series.all_values("temperature") == []
    with pytest.raises(ExperimentNotFoundError):
        series.get(1)


def test_series_supports_indexing_membership_and_filtering(
    experiment: Experiment, researcher: Researcher
) -> None:
    other = Experiment(
        2, "Gas compression", Researcher(2, "Taras", "Hnatiuk", "t@lnu.edu.ua"), "pressure", "kPa"
    )
    series = ExperimentSeries("Project", [experiment, other])

    assert series[0] is experiment and series[1:] == [other]
    assert experiment in series
    assert series.get(2) is other
    assert list(series.by_researcher(researcher)) == [experiment]


def test_series_rejects_duplicate_experiment(experiment: Experiment) -> None:
    series = ExperimentSeries("Project", [experiment])

    with pytest.raises(ExperimentValidationError):
        series.add(experiment)
