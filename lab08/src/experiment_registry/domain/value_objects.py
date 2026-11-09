"""Immutable value objects."""

import math
from dataclasses import dataclass
from functools import total_ordering

from experiment_registry.exceptions import (
    ExperimentValidationError,
    IncompatibleMeasurementError,
)


@total_ordering
@dataclass(frozen=True)
class Measurement:
    """A measured value of a physical parameter, e.g. 293.4 K of temperature.

    Frozen: equal measurements are interchangeable and can be dict keys or set items.
    """

    parameter: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        if not self.parameter.strip():
            raise ExperimentValidationError("Measurement parameter must not be empty.")
        if not self.unit.strip():
            raise ExperimentValidationError("Measurement unit must not be empty.")
        if not math.isfinite(self.value):
            raise ExperimentValidationError(f"Measurement value must be finite, got {self.value}.")

    def _check_compatible(self, other: "Measurement") -> None:
        if (self.parameter, self.unit) != (other.parameter, other.unit):
            raise IncompatibleMeasurementError(
                f"Cannot compare {self.parameter} [{self.unit}] with {other.parameter} [{other.unit}]."
            )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Measurement):
            return NotImplemented
        self._check_compatible(other)
        return self.value < other.value

    def __sub__(self, other: "Measurement") -> "Measurement":
        """Difference of two compatible measurements (arithmetic dunder)."""
        self._check_compatible(other)
        return Measurement(self.parameter, round(self.value - other.value, 6), self.unit)

    def __str__(self) -> str:
        return f"{self.value:g} {self.unit}"


@dataclass(frozen=True)
class ResultRange:
    """Closed interval [low, high] used to filter results."""

    low: float
    high: float

    def __post_init__(self) -> None:
        if self.low > self.high:
            raise ExperimentValidationError(f"Invalid range: {self.low} > {self.high}.")

    def __contains__(self, measurement: object) -> bool:
        if isinstance(measurement, Measurement):
            return self.low <= measurement.value <= self.high
        if isinstance(measurement, (int, float)):
            return self.low <= measurement <= self.high
        return False
