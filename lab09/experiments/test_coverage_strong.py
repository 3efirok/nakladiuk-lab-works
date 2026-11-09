"""Experiment 2b: a meaningful assertion reveals the defect."""

import pytest
from error_metrics import relative_error


@pytest.mark.parametrize(("measured", "expected", "error"), [(110.0, 100.0, 0.10), (90.0, 100.0, 0.10)])
def test_relative_error_value(measured: float, expected: float, error: float) -> None:
    assert relative_error(measured, expected) == pytest.approx(error)
