"""Repository pattern over SQLAlchemy sessions (CRUD, search, aggregates)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from experiment_registry.exceptions import ExperimentNotFoundError
from experiment_registry.persistence.orm import ExperimentORM, ResearcherORM


@dataclass(frozen=True)
class ResultSummary:
    count: int
    average: float | None
    minimum: float | None
    maximum: float | None


class ResearcherRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, full_name: str, email: str | None = None, department: str = "Physics") -> ResearcherORM:
        researcher = ResearcherORM(full_name=full_name.strip(), email=email, department=department)
        self.session.add(researcher)
        self.session.flush()  # assigns the primary key without committing
        return researcher

    def get(self, researcher_id: int) -> ResearcherORM:
        researcher = self.session.get(ResearcherORM, researcher_id)
        if researcher is None:
            raise ExperimentNotFoundError(f"Researcher #{researcher_id} not found.")
        return researcher

    def get_by_name(self, full_name: str) -> ResearcherORM | None:
        statement = select(ResearcherORM).where(func.lower(ResearcherORM.full_name) == full_name.strip().lower())
        return self.session.scalars(statement).first()

    def get_or_create(self, full_name: str) -> ResearcherORM:
        return self.get_by_name(full_name) or self.add(full_name)

    def list_all(self) -> Sequence[ResearcherORM]:
        return self.session.scalars(select(ResearcherORM).order_by(ResearcherORM.full_name)).all()

    def delete(self, researcher_id: int) -> None:
        self.session.delete(self.get(researcher_id))
        self.session.flush()


class ExperimentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ CRUD
    def add(self, name: str, researcher: ResearcherORM, parameter: str, result: float,
            day: date, notes: str | None = None) -> ExperimentORM:
        experiment = ExperimentORM(name=name, researcher=researcher, parameter=parameter,
                                   result=result, date=day, notes=notes)
        self.session.add(experiment)
        self.session.flush()
        return experiment

    def get(self, experiment_id: int) -> ExperimentORM:
        experiment = self.session.get(ExperimentORM, experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(f"Experiment #{experiment_id} not found.")
        return experiment

    def list_all(self, limit: int | None = None, offset: int = 0) -> Sequence[ExperimentORM]:
        """All experiments sorted by date (with optional pagination)."""
        statement = (select(ExperimentORM).options(joinedload(ExperimentORM.researcher))
                     .order_by(ExperimentORM.date, ExperimentORM.id).offset(offset))
        if limit is not None:
            statement = statement.limit(limit)
        return self.session.scalars(statement).all()

    def update(self, experiment_id: int, **fields: object) -> ExperimentORM:
        allowed = {"name", "parameter", "result", "date", "notes"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Cannot update fields: {sorted(unknown)}")
        experiment = self.get(experiment_id)
        for key, value in fields.items():
            setattr(experiment, key, value)
        self.session.flush()
        return experiment

    def delete(self, experiment_id: int) -> None:
        self.session.delete(self.get(experiment_id))
        self.session.flush()

    # --------------------------------------------------------------- queries
    def find_by_researcher(self, full_name: str) -> Sequence[ExperimentORM]:
        statement = (
            select(ExperimentORM)
            .join(ExperimentORM.researcher)
            .options(joinedload(ExperimentORM.researcher))
            .where(func.lower(ResearcherORM.full_name) == full_name.strip().lower())
            .order_by(ExperimentORM.date)
        )
        return self.session.scalars(statement).all()

    def filter_by_result_range(self, low: float, high: float,
                               parameter: str | None = None) -> Sequence[ExperimentORM]:
        if low > high:
            raise ValueError(f"Invalid range: {low} > {high}")
        statement = (select(ExperimentORM).options(joinedload(ExperimentORM.researcher))
                     .where(ExperimentORM.result.between(low, high)))
        if parameter is not None:
            statement = statement.where(ExperimentORM.parameter == parameter)
        return self.session.scalars(statement.order_by(ExperimentORM.result)).all()

    def search(self, *, researcher_id: int | None = None, parameter: str | None = None,
               min_result: float | None = None, max_result: float | None = None,
               sort: str = "date", limit: int | None = None, offset: int = 0) -> Sequence[ExperimentORM]:
        """Combined filters + sorting + pagination used by the REST API."""
        order = {"date": ExperimentORM.date, "-date": ExperimentORM.date.desc(),
                 "result": ExperimentORM.result, "-result": ExperimentORM.result.desc()}
        if sort not in order:
            raise ValueError(f"Unknown sort {sort!r}; allowed: {sorted(order)}")
        statement = select(ExperimentORM).options(joinedload(ExperimentORM.researcher))
        if researcher_id is not None:
            statement = statement.where(ExperimentORM.researcher_id == researcher_id)
        if parameter is not None:
            statement = statement.where(ExperimentORM.parameter == parameter)
        if min_result is not None:
            statement = statement.where(ExperimentORM.result >= min_result)
        if max_result is not None:
            statement = statement.where(ExperimentORM.result <= max_result)
        statement = statement.order_by(order[sort], ExperimentORM.id).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        return self.session.scalars(statement).all()

    def summary(self, parameter: str | None = None, researcher_id: int | None = None) -> ResultSummary:
        """COUNT / AVG / MIN / MAX calculated by the database."""
        statement = select(func.count(ExperimentORM.id), func.avg(ExperimentORM.result),
                           func.min(ExperimentORM.result), func.max(ExperimentORM.result))
        if parameter is not None:
            statement = statement.where(ExperimentORM.parameter == parameter)
        if researcher_id is not None:
            statement = statement.where(ExperimentORM.researcher_id == researcher_id)
        count, average, minimum, maximum = self.session.execute(statement).one()
        return ResultSummary(count, average, minimum, maximum)

    def statistics_by_researcher(self) -> list[tuple[str, int, float, float, float]]:
        """JOIN + GROUP BY: per-researcher count, average, minimum and maximum."""
        statement = (
            select(ResearcherORM.full_name, func.count(ExperimentORM.id), func.avg(ExperimentORM.result),
                   func.min(ExperimentORM.result), func.max(ExperimentORM.result))
            .join(ExperimentORM, ExperimentORM.researcher_id == ResearcherORM.id)
            .group_by(ResearcherORM.full_name)
            .order_by(ResearcherORM.full_name)
        )
        return [(name, count, avg, low, high)
                for name, count, avg, low, high in self.session.execute(statement).all()]
