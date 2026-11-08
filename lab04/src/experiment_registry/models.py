"""Data models of the experiment registry."""

from dataclasses import dataclass
from datetime import date

from experiment_registry.config import MAX_RESULT, MIN_RESULT
from experiment_registry.exceptions import ExperimentValidationError


@dataclass
class Experiment:
    """Single scientific experiment and its numeric result."""

    experiment_id: int
    name: str
    researcher: str
    parameter: str
    result: float
    date: date

    def __post_init__(self) -> None:
        if self.experiment_id <= 0:
            raise ExperimentValidationError("Experiment ID must be positive.")
        if not self.name.strip():
            raise ExperimentValidationError("Experiment name must not be empty.")
        if not self.researcher.strip():
            raise ExperimentValidationError("Researcher must not be empty.")
        if not self.parameter.strip():
            raise ExperimentValidationError("Parameter must not be empty.")
        if not MIN_RESULT <= self.result <= MAX_RESULT:
            raise ExperimentValidationError(
                f"Result {self.result} is outside [{MIN_RESULT}, {MAX_RESULT}]."
            )

    @property
    def label(self) -> str:
        """Short human-readable description of the experiment."""
        return f"#{self.experiment_id} {self.name} ({self.researcher})"


@dataclass(frozen=True)
class ResultStatistics:
    """Aggregated statistics of experiment results."""

    count: int
    average: float
    minimum: float
    maximum: float
