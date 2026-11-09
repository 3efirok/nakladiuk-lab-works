"""Experiment 3b: all branches and boundary values."""

import pytest
from classification import classify_accuracy


@pytest.mark.parametrize(("error", "expected"),
                         [(0.005, "high"), (0.01, "high"), (0.03, "acceptable"), (0.05, "acceptable"),
                          (0.1, "low")])
def test_classify_accuracy(error: float, expected: str) -> None:
    assert classify_accuracy(error) == expected
