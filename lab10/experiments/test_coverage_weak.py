"""Experiment 2a: 100% coverage without a single assertion."""

from error_metrics import relative_error


def test_relative_error_runs() -> None:
    relative_error(110.0, 100.0)
