"""Service layer on top of repositories; every public method is one transaction."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from experiment_registry.exceptions import ExperimentValidationError
from experiment_registry.persistence.database import session_scope
from experiment_registry.persistence.orm import ExperimentORM
from experiment_registry.persistence.repositories import (
    ExperimentRepository,
    ResearcherRepository,
    ResultSummary,
)


@dataclass(frozen=True)
class NewExperiment:
    name: str
    researcher: str
    parameter: str
    result: float
    date: date
    notes: str | None = None


class ExperimentRegistry:
    def __init__(self, session_factory: sessionmaker[Session],
                 min_result: float = 0.0, max_result: float = 1_000_000.0) -> None:
        self._sessions = session_factory
        self._min = min_result
        self._max = max_result

    def _validate(self, item: NewExperiment) -> None:
        if not item.name.strip() or not item.researcher.strip() or not item.parameter.strip():
            raise ExperimentValidationError(f"Empty field in {item!r}")
        if not math.isfinite(item.result) or not self._min <= item.result <= self._max:
            raise ExperimentValidationError(
                f"Result {item.result} of {item.name!r} is outside [{self._min}, {self._max}]")

    def _insert(self, session: Session, item: NewExperiment) -> ExperimentORM:
        self._validate(item)
        researcher = ResearcherRepository(session).get_or_create(item.researcher)
        return ExperimentRepository(session).add(item.name, researcher, item.parameter, item.result,
                                                 item.date, item.notes)

    def add_experiment(self, item: NewExperiment) -> int:
        with session_scope(self._sessions) as session:
            return self._insert(session, item).id

    def add_series(self, items: Sequence[NewExperiment]) -> list[int]:
        """Batch insert in ONE transaction: an invalid record rolls back the whole series."""
        try:
            with session_scope(self._sessions) as session:
                return [self._insert(session, item).id for item in items]
        except IntegrityError as error:
            raise ExperimentValidationError(f"Database constraint violated: {error.orig}") from error

    def update_result(self, experiment_id: int, result: float) -> ExperimentORM:
        with session_scope(self._sessions) as session:
            experiment = ExperimentRepository(session).get(experiment_id)
            self._validate(NewExperiment(experiment.name, "-", experiment.parameter, result, experiment.date))
            return ExperimentRepository(session).update(experiment_id, result=result)

    def delete(self, experiment_id: int) -> None:
        with session_scope(self._sessions) as session:
            ExperimentRepository(session).delete(experiment_id)

    def find_by_researcher(self, full_name: str) -> Sequence[ExperimentORM]:
        with session_scope(self._sessions) as session:
            return ExperimentRepository(session).find_by_researcher(full_name)

    def filter_by_range(self, low: float, high: float, parameter: str | None = None) -> Sequence[ExperimentORM]:
        with session_scope(self._sessions) as session:
            return ExperimentRepository(session).filter_by_result_range(low, high, parameter)

    def sorted_by_date(self) -> Sequence[ExperimentORM]:
        with session_scope(self._sessions) as session:
            return ExperimentRepository(session).list_all()

    def statistics(self, parameter: str | None = None) -> ResultSummary:
        with session_scope(self._sessions) as session:
            return ExperimentRepository(session).summary(parameter=parameter)

    def statistics_by_researcher(self) -> list[tuple[str, int, float, float, float]]:
        with session_scope(self._sessions) as session:
            return ExperimentRepository(session).statistics_by_researcher()
