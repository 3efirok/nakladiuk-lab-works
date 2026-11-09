"""Experiment 3a: two of three branches are tested."""

import pytest
from classification import classify_accuracy


@pytest.mark.parametrize(("error", "expected"), [(0.005, "high"), (0.03, "acceptable")])
def test_classify_accuracy(error: float, expected: str) -> None:
    assert classify_accuracy(error) == expected
