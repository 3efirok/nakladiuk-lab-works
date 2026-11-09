import dataclasses
from collections.abc import Callable

import pytest

from experiment_registry.domain.value_objects import Measurement, ResultRange
from experiment_registry.exceptions import ExperimentValidationError, IncompatibleMeasurementError


def test_measurement_stores_parameter_value_and_unit() -> None:
    measurement = Measurement("temperature", 293.4, "K")

    assert (measurement.parameter, measurement.value, measurement.unit) == ("temperature", 293.4, "K")
    assert str(measurement) == "293.4 K"


def test_measurement_is_immutable(make_measurement: Callable[..., Measurement]) -> None:
    measurement = make_measurement()

    with pytest.raises(dataclasses.FrozenInstanceError):
        measurement.value = 1.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("parameter", "value", "unit"),
    [
        ("", 1.0, "K"),
        ("temperature", 1.0, " "),
        ("temperature", float("nan"), "K"),
        ("temperature", float("inf"), "K"),
    ],
    ids=["empty-parameter", "empty-unit", "nan", "infinity"],
)
def test_invalid_measurement_raises_validation_error(parameter: str, value: float, unit: str) -> None:
    with pytest.raises(ExperimentValidationError):
        Measurement(parameter, value, unit)


def test_measurements_are_ordered_and_subtracted(make_measurement: Callable[..., Measurement]) -> None:
    low, high = make_measurement(293.4), make_measurement(301.8)

    assert low < high and high >= low
    assert (high - low).value == pytest.approx(8.4)


def test_incompatible_measurements_cannot_be_compared(make_measurement: Callable[..., Measurement]) -> None:
    with pytest.raises(IncompatibleMeasurementError, match="pressure"):
        _ = make_measurement(1.0) < make_measurement(1.0, "pressure", "kPa")


def test_equal_measurements_are_hashable_and_deduplicated(
    make_measurement: Callable[..., Measurement],
) -> None:
    assert len({make_measurement(300.0), make_measurement(300.0)}) == 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [(99.999, False), (100.0, True), (250.0, True), (400.0, True), (400.001, False)],
)
def test_result_range_includes_boundaries(value: float, expected: bool) -> None:
    assert (value in ResultRange(100, 400)) is expected


def test_result_range_accepts_measurements_and_rejects_other_types(
    make_measurement: Callable[..., Measurement],
) -> None:
    interval = ResultRange(290, 310)

    assert make_measurement(300.0) in interval
    assert "300" not in interval


def test_inverted_result_range_raises_error() -> None:
    with pytest.raises(ExperimentValidationError, match="Invalid range"):
        ResultRange(400, 100)
