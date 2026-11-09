"""Deliberately defective code used in the testing experiments (not part of the package)."""

from collections.abc import Sequence

from experiment_registry.domain.strategies import AnalysisStrategy


class BuggyMeanStrategy(AnalysisStrategy):
    """Defect: divides by n - 1 instead of n."""

    name = "average"

    def _calculate(self, values: Sequence[float]) -> float:
        return sum(values) / (len(values) - 1 or 1)

