"""Experiment 5b: the same check made deterministic."""

import random

import pytest
from test_flaky_bad import read_sensor


def test_sensor_reading_with_seed() -> None:
    random.seed(15)
    readings = [read_sensor() for _ in range(3)]
    random.seed(15)
    assert [read_sensor() for _ in range(3)] == readings


def test_sensor_reading_with_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(random, "gauss", lambda mu, sigma: 301.5)
    assert read_sensor() < 303.0
