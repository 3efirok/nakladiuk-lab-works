"""Experiment 1: execution is not verification."""

import pytest
from buggy_metrics import BuggyMeanStrategy

from experiment_registry.domain.strategies import AnalysisStrategy, MeanStrategy

VALUES = [293.4, 297.1, 301.8]


@pytest.mark.parametrize("strategy", [MeanStrategy(), BuggyMeanStrategy()], ids=["correct", "buggy"])
def test_mean_weak(strategy: AnalysisStrategy) -> None:
    strategy.analyze(VALUES)  # no assertion: passes for any result


@pytest.mark.parametrize("strategy", [MeanStrategy(), BuggyMeanStrategy()], ids=["correct", "buggy"])
def test_mean_strong(strategy: AnalysisStrategy) -> None:
    assert strategy.analyze(VALUES) == pytest.approx(297.433333)
