"""Experiment 5a: a flaky test that depends on randomness."""

import random


def read_sensor() -> float:
    return random.gauss(300.0, 5.0)  # noisy temperature sensor


def test_sensor_reading_is_below_threshold() -> None:
    assert read_sensor() < 303.0
