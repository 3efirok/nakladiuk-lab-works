"""Analysis strategies (Strategy pattern on top of an abstract base class)."""

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence


class AnalysisStrategy(ABC):
    """Computes one metric from a sequence of result values."""

    name: str = "metric"

    def analyze(self, values: Sequence[float]) -> float:
        """Template method: common empty-data check, then the concrete calculation."""
        if not values:
            raise ValueError(f"{self.name}: no values to analyze")
        return round(self._calculate(values), 6)

    @abstractmethod
    def _calculate(self, values: Sequence[float]) -> float:
        """Concrete metric; implemented by subclasses."""


class MeanStrategy(AnalysisStrategy):
    name = "average"

    def _calculate(self, values: Sequence[float]) -> float:
        return sum(values) / len(values)


class MinimumStrategy(AnalysisStrategy):
    name = "minimum"

    def _calculate(self, values: Sequence[float]) -> float:
        return min(values)


class MaximumStrategy(AnalysisStrategy):
    name = "maximum"

    def _calculate(self, values: Sequence[float]) -> float:
        return max(values)


class StandardDeviationStrategy(AnalysisStrategy):
    """Sample standard deviation (0 for a single value)."""

    name = "std_dev"

    def _calculate(self, values: Sequence[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def default_strategies() -> list[AnalysisStrategy]:
    return [MeanStrategy(), MinimumStrategy(), MaximumStrategy(), StandardDeviationStrategy()]
