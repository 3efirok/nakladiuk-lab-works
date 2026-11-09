"""Domain entities: Researcher, ExperimentResult, Experiment, ExperimentSeries."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import overload

from experiment_registry.domain.value_objects import Measurement, ResultRange
from experiment_registry.exceptions import (
    ExperimentNotFoundError,
    ExperimentValidationError,
    IncompatibleMeasurementError,
)


class Person:
    """Base class with a validated full name."""

    def __init__(self, first_name: str, last_name: str) -> None:
        if not first_name.strip() or not last_name.strip():
            raise ExperimentValidationError("First and last name are required.")
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Researcher(Person):
    """A scientist who performs experiments (inherits name handling from Person)."""

    def __init__(
        self, researcher_id: int, first_name: str, last_name: str, email: str, department: str = "Physics"
    ) -> None:
        super().__init__(first_name, last_name)
        if researcher_id <= 0:
            raise ExperimentValidationError("Researcher ID must be positive.")
        self._id = researcher_id
        self.department = department
        self._email = ""
        self.email = email  # goes through the property setter

    @property
    def id(self) -> int:
        """Read-only identifier."""
        return self._id

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ExperimentValidationError(f"Invalid e-mail: {value!r}.")
        self._email = value

    def __repr__(self) -> str:
        return f"Researcher(id={self._id}, name={self.full_name!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Researcher) and other.id == self.id

    def __hash__(self) -> int:
        return hash(("Researcher", self._id))


@dataclass
class ExperimentResult:
    """One recorded result of an experiment."""

    result_id: int
    measurement: Measurement
    recorded_on: date
    notes: str = ""

    def __post_init__(self) -> None:
        if self.result_id <= 0:
            raise ExperimentValidationError("Result ID must be positive.")
        if self.recorded_on > date.today():
            raise ExperimentValidationError("Result date cannot be in the future.")

    @property
    def value(self) -> float:
        return self.measurement.value


class Experiment:
    """Experiment entity; owns its results (composition)."""

    def __init__(
        self, experiment_id: int, name: str, researcher: Researcher, parameter: str, unit: str
    ) -> None:
        if experiment_id <= 0:
            raise ExperimentValidationError("Experiment ID must be positive.")
        if not name.strip():
            raise ExperimentValidationError("Experiment name must not be empty.")
        self._id = experiment_id
        self.name = name.strip()
        self.researcher = researcher
        self.parameter = parameter
        self.unit = unit
        self._results: list[ExperimentResult] = []

    @property
    def id(self) -> int:
        return self._id

    @property
    def results(self) -> tuple[ExperimentResult, ...]:
        """Read-only view; results can be added only through add_result()."""
        return tuple(self._results)

    def add_result(self, result: ExperimentResult) -> None:
        m = result.measurement
        if (m.parameter, m.unit) != (self.parameter, self.unit):
            raise IncompatibleMeasurementError(
                f"Experiment #{self._id} measures {self.parameter} [{self.unit}], "
                f"got {m.parameter} [{m.unit}]."
            )
        if any(item.result_id == result.result_id for item in self._results):
            raise ExperimentValidationError(f"Duplicate result ID {result.result_id}.")
        self._results.append(result)

    def values(self) -> list[float]:
        return [item.value for item in self._results]

    def results_in(self, interval: ResultRange) -> list[ExperimentResult]:
        return [item for item in self._results if item.measurement in interval]

    def __len__(self) -> int:
        return len(self._results)

    def __iter__(self) -> Iterator[ExperimentResult]:
        return iter(self._results)

    def __repr__(self) -> str:
        return (
            f"Experiment(id={self._id}, name={self.name!r}, "
            f"researcher={self.researcher.full_name!r}, results={len(self)})"
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Experiment) and other.id == self.id

    def __hash__(self) -> int:
        return hash(("Experiment", self._id))


class ExperimentSeries:
    """Custom collection of experiments (e.g. one research project)."""

    def __init__(self, title: str, experiments: list[Experiment] | None = None) -> None:
        self.title = title
        self._experiments: list[Experiment] = list(experiments or [])

    def add(self, experiment: Experiment) -> None:
        if experiment in self:
            raise ExperimentValidationError(f"Experiment #{experiment.id} is already in the series.")
        self._experiments.append(experiment)

    def get(self, experiment_id: int) -> Experiment:
        for experiment in self._experiments:
            if experiment.id == experiment_id:
                return experiment
        raise ExperimentNotFoundError(f"Experiment #{experiment_id} not found in {self.title!r}.")

    def by_researcher(self, researcher: Researcher) -> "ExperimentSeries":
        return ExperimentSeries(
            f"{self.title} / {researcher.full_name}",
            [item for item in self._experiments if item.researcher == researcher],
        )

    def all_values(self, parameter: str) -> list[float]:
        return [v for item in self._experiments if item.parameter == parameter for v in item.values()]

    def __len__(self) -> int:
        return len(self._experiments)

    def __iter__(self) -> Iterator[Experiment]:
        return iter(self._experiments)

    def __contains__(self, item: object) -> bool:
        return item in self._experiments

    @overload
    def __getitem__(self, index: int) -> Experiment: ...

    @overload
    def __getitem__(self, index: slice) -> list[Experiment]: ...

    def __getitem__(self, index: int | slice) -> Experiment | list[Experiment]:
        return self._experiments[index]

    def __repr__(self) -> str:
        return f"ExperimentSeries({self.title!r}, experiments={len(self)})"
