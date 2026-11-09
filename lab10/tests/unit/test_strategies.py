import pytest

from experiment_registry.domain.strategies import (
    AnalysisStrategy,
    MaximumStrategy,
    MeanStrategy,
    MinimumStrategy,
    StandardDeviationStrategy,
)

VALUES = [293.4, 297.1, 301.8]


@pytest.mark.parametrize(
    ("strategy", "expected"),
    [
        (MeanStrategy(), 297.433333),
        (MinimumStrategy(), 293.4),
        (MaximumStrategy(), 301.8),
        (StandardDeviationStrategy(), 4.209909),
    ],
    ids=lambda item: getattr(item, "name", str(item)),
)
def test_strategy_calculates_metric(strategy: AnalysisStrategy, expected: float) -> None:
    assert strategy.analyze(VALUES) == pytest.approx(expected, rel=1e-6)


@pytest.mark.parametrize("strategy", [MeanStrategy(), MinimumStrategy(), MaximumStrategy()])
def test_single_value_is_its_own_average_min_and_max(strategy: AnalysisStrategy) -> None:
    assert strategy.analyze([42.0]) == 42.0


def test_standard_deviation_of_single_value_is_zero() -> None:
    assert StandardDeviationStrategy().analyze([42.0]) == 0.0


def test_empty_values_raise_value_error() -> None:
    with pytest.raises(ValueError, match="no values"):
        MeanStrategy().analyze([])


def test_abstract_strategy_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        AnalysisStrategy()  # type: ignore[abstract]
