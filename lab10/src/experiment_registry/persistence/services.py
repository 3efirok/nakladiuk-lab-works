"""Service layer on top of repositories; every public method is one transaction."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from experiment_registry.exceptions import DuplicateExperimentError, ExperimentValidationError
from experiment_registry.persistence.database import session_scope
from experiment_registry.persistence.orm import ExperimentORM, ResearcherORM
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
    def __init__(
        self, session_factory: sessionmaker[Session], min_result: float = 0.0, max_result: float = 1_000_000.0
    ) -> None:
        self._sessions = session_factory
        self._min = min_result
        self._max = max_result
        # lab 9: cache of extended statistics, invalidated by a version counter on every write
        self.version = 0
        self._stats_cache: dict[tuple[str | None, int], ExtendedStatistics] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def _changed(self) -> None:
        self.version += 1
        self._stats_cache.clear()

    def _validate(self, item: NewExperiment) -> None:
        if not item.name.strip() or not item.researcher.strip() or not item.parameter.strip():
            raise ExperimentValidationError(f"Empty field in {item!r}")
        if not math.isfinite(item.result) or not self._min <= item.result <= self._max:
            raise ExperimentValidationError(
                f"Result {item.result} of {item.name!r} is outside [{self._min}, {self._max}]"
            )

    def _insert(self, session: Session, item: NewExperiment) -> ExperimentORM:
        self._validate(item)
        researcher = ResearcherRepository(session).get_or_create(item.researcher)
        return ExperimentRepository(session).add(
            item.name, researcher, item.parameter, item.result, item.date, item.notes
        )

    def add_experiment(self, item: NewExperiment) -> int:
        with session_scope(self._sessions) as session:
            experiment_id = self._insert(session, item).id
        self._changed()
        return experiment_id

    def add_series(self, items: Sequence[NewExperiment]) -> list[int]:
        """Batch insert in ONE transaction: an invalid record rolls back the whole series."""
        try:
            with session_scope(self._sessions) as session:
                ids = [self._insert(session, item).id for item in items]
        except IntegrityError as error:
            raise ExperimentValidationError(f"Database constraint violated: {error.orig}") from error
        self._changed()
        return ids

    def update_result(self, experiment_id: int, result: float) -> ExperimentORM:
        with session_scope(self._sessions) as session:
            experiment = ExperimentRepository(session).get(experiment_id)
            self._validate(NewExperiment(experiment.name, "-", experiment.parameter, result, experiment.date))
            updated = ExperimentRepository(session).update(experiment_id, result=result)
        self._changed()
        return updated

    def delete(self, experiment_id: int) -> None:
        with session_scope(self._sessions) as session:
            ExperimentRepository(session).delete(experiment_id)
        self._changed()

    def find_by_researcher(self, full_name: str) -> Sequence[ExperimentORM]:
        with session_scope(self._sessions) as session:
            return ExperimentRepository(session).find_by_researcher(full_name)

    def filter_by_range(
        self, low: float, high: float, parameter: str | None = None
    ) -> Sequence[ExperimentORM]:
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

    # ------------------------------------------------------- REST API (lab 8)
    def create_researcher(
        self, full_name: str, email: str | None = None, department: str = "Physics"
    ) -> ResearcherORM:
        try:
            with session_scope(self._sessions) as session:
                return ResearcherRepository(session).add(full_name, email, department)
        except IntegrityError as error:
            raise DuplicateExperimentError(f"Researcher {full_name!r} or e-mail already exists.") from error

    def get_researcher(self, researcher_id: int) -> ResearcherORM:
        with session_scope(self._sessions) as session:
            return ResearcherRepository(session).get(researcher_id)

    def list_researchers(self) -> Sequence[ResearcherORM]:
        with session_scope(self._sessions) as session:
            return ResearcherRepository(session).list_all()

    def researcher_experiments(self, researcher_id: int, sort: str = "date") -> Sequence[ExperimentORM]:
        with session_scope(self._sessions) as session:
            ResearcherRepository(session).get(researcher_id)  # 404 if the researcher does not exist
            return ExperimentRepository(session).search(researcher_id=researcher_id, sort=sort)

    def list_experiments(self, **filters: Any) -> Sequence[ExperimentORM]:
        with session_scope(self._sessions) as session:
            return ExperimentRepository(session).search(**filters)

    def get_experiment(self, experiment_id: int) -> ExperimentORM:
        with session_scope(self._sessions) as session:
            experiment = ExperimentRepository(session).get(experiment_id)
            _ = experiment.researcher.full_name  # load relationship before the session closes
            return experiment

    def create_experiment(
        self,
        researcher_id: int,
        name: str,
        parameter: str,
        result: float,
        day: date,
        notes: str | None = None,
    ) -> ExperimentORM:
        with session_scope(self._sessions) as session:
            researcher = ResearcherRepository(session).get(researcher_id)
            self._validate(NewExperiment(name, researcher.full_name, parameter, result, day, notes))
            created = ExperimentRepository(session).add(name, researcher, parameter, result, day, notes)
        self._changed()
        return created

    def update_experiment(self, experiment_id: int, fields: dict[str, Any]) -> ExperimentORM:
        with session_scope(self._sessions) as session:
            repository = ExperimentRepository(session)
            current = repository.get(experiment_id)
            merged: dict[str, Any] = {
                "name": current.name,
                "parameter": current.parameter,
                "result": current.result,
                "date": current.date,
                "notes": current.notes,
            } | fields
            self._validate(
                NewExperiment(
                    merged["name"],
                    current.researcher.full_name,
                    merged["parameter"],
                    merged["result"],
                    merged["date"],
                    merged["notes"],
                )
            )
            updated = repository.update(experiment_id, **fields)
        self._changed()
        return updated

    def summary(self, parameter: str | None = None, researcher_id: int | None = None) -> ResultSummary:
        with session_scope(self._sessions) as session:
            if researcher_id is not None:
                ResearcherRepository(session).get(researcher_id)
            return ExperimentRepository(session).summary(parameter=parameter, researcher_id=researcher_id)

    # ------------------------------------------- optimized statistics (lab 9)
    def extended_statistics(self, parameter: str | None = None) -> "ExtendedStatistics":
        """NumPy statistics with caching; the cache is invalidated by any write."""
        key = (parameter, self.version)
        cached = self._stats_cache.get(key)
        if cached is not None:
            self.cache_hits += 1
            return cached
        self.cache_misses += 1
        with session_scope(self._sessions) as session:
            values = np.asarray(ExperimentRepository(session).result_values(parameter), dtype=np.float64)
        result = ExtendedStatistics.from_values(values, parameter, self.version)
        self._stats_cache[key] = result
        return result


@dataclass(frozen=True)
class ExtendedStatistics:
    count: int
    mean: float | None
    std: float | None
    minimum: float | None
    maximum: float | None
    median: float | None
    p95: float | None
    parameter: str | None
    version: int

    @classmethod
    def from_values(
        cls, values: NDArray[np.float64], parameter: str | None, version: int
    ) -> "ExtendedStatistics":
        if values.size == 0:
            return cls(0, None, None, None, None, None, None, parameter, version)
        std = float(values.std(ddof=1)) if values.size > 1 else 0.0
        return cls(
            int(values.size),
            float(values.mean()),
            std,
            float(np.min(values)),
            float(np.max(values)),
            float(np.median(values)),
            float(np.percentile(values, 95)),
            parameter,
            version,
        )
