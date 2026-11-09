"""Integration tests of the persistence layer on a separate SQLite test database."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from experiment_registry.exceptions import ExperimentNotFoundError, ExperimentValidationError
from experiment_registry.persistence.orm import ExperimentORM, ResearcherORM
from experiment_registry.persistence.repositories import ExperimentRepository, ResearcherRepository
from experiment_registry.persistence.services import ExperimentRegistry, NewExperiment

pytestmark = pytest.mark.integration

DATA = [
    NewExperiment("Thermal conductivity of Cu", "Olena Kovalenko", "temperature", 301.8, date(2026, 2, 10)),
    NewExperiment("Gas compression test", "Taras Hnatiuk", "pressure", 101.3, date(2026, 2, 5)),
    NewExperiment("Thermal conductivity of Al", "Olena Kovalenko", "temperature", 293.4, date(2026, 2, 3)),
    NewExperiment("Cryogenic cooling run", "Andrii Bondar", "temperature", 77.2, date(2026, 2, 18)),
]


@pytest.fixture
def registry(session_factory: sessionmaker[Session]) -> ExperimentRegistry:
    registry = ExperimentRegistry(session_factory)
    registry.add_series(DATA)
    return registry


# ------------------------------------------------------------------------ CRUD
def test_create_assigns_primary_key_and_researcher(db_session: Session) -> None:
    researcher = ResearcherRepository(db_session).add("Olena Kovalenko", "o.kovalenko@lnu.edu.ua")
    experiment = ExperimentRepository(db_session).add(
        "Run", researcher, "temperature", 293.4, date(2026, 2, 3)
    )

    assert researcher.id is not None and experiment.id is not None
    assert experiment.researcher_id == researcher.id


def test_read_returns_saved_values(registry: ExperimentRegistry, db_session: Session) -> None:
    saved = ExperimentRepository(db_session).get(1)

    assert (saved.name, saved.parameter, saved.result, saved.date) == (
        "Thermal conductivity of Cu",
        "temperature",
        301.8,
        date(2026, 2, 10),
    )


def test_update_changes_result_and_notes(registry: ExperimentRegistry, db_session: Session) -> None:
    registry.update_result(2, 102.0)
    ExperimentRepository(db_session).update(2, notes="calibrated")
    db_session.commit()

    assert db_session.get(ExperimentORM, 2).result == 102.0  # type: ignore[union-attr]
    assert db_session.get(ExperimentORM, 2).notes == "calibrated"  # type: ignore[union-attr]


def test_update_rejects_unknown_field(registry: ExperimentRegistry, db_session: Session) -> None:
    with pytest.raises(ValueError, match="Cannot update"):
        ExperimentRepository(db_session).update(1, researcher_id=99)


def test_delete_removes_row(registry: ExperimentRegistry, db_session: Session) -> None:
    registry.delete(4)

    with pytest.raises(ExperimentNotFoundError):
        ExperimentRepository(db_session).get(4)
    assert len(registry.sorted_by_date()) == 3


# -------------------------------------------------------------- relationships
def test_researcher_relationship_and_reuse(registry: ExperimentRegistry, db_session: Session) -> None:
    olena = ResearcherRepository(db_session).get_by_name("olena kovalenko")

    assert olena is not None
    assert [e.name for e in olena.experiments] == ["Thermal conductivity of Al", "Thermal conductivity of Cu"]
    assert len(ResearcherRepository(db_session).list_all()) == 3  # researcher reused, not duplicated


def test_foreign_key_is_enforced(db_session: Session) -> None:
    db_session.add(
        ExperimentORM(
            name="Orphan", researcher_id=999, parameter="temperature", result=1.0, date=date(2026, 1, 1)
        )
    )

    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        db_session.flush()


def test_deleting_researcher_cascades_to_experiments(
    registry: ExperimentRegistry, db_session: Session
) -> None:
    olena = ResearcherRepository(db_session).get_by_name("Olena Kovalenko")
    assert olena is not None
    ResearcherRepository(db_session).delete(olena.id)
    db_session.commit()

    assert db_session.scalars(select(ExperimentORM.name)).all() == [
        "Gas compression test",
        "Cryogenic cooling run",
    ]


def test_unique_researcher_name_is_enforced(db_session: Session) -> None:
    db_session.add_all([ResearcherORM(full_name="Iryna Melnyk"), ResearcherORM(full_name="Iryna Melnyk")])

    with pytest.raises(IntegrityError, match="UNIQUE"):
        db_session.flush()


# ------------------------------------------------- search, aggregates, sorting
def test_find_by_researcher(registry: ExperimentRegistry) -> None:
    assert [e.result for e in registry.find_by_researcher("Olena Kovalenko")] == [293.4, 301.8]
    assert registry.find_by_researcher("Nobody") == []


def test_aggregates_are_calculated_by_sql(registry: ExperimentRegistry) -> None:
    stats = registry.statistics("temperature")

    assert stats.count == 3
    assert stats.average == pytest.approx((301.8 + 293.4 + 77.2) / 3)
    assert (stats.minimum, stats.maximum) == (77.2, 301.8)


def test_aggregates_of_empty_table(session_factory: sessionmaker[Session]) -> None:
    stats = ExperimentRegistry(session_factory).statistics()

    assert (stats.count, stats.average, stats.minimum, stats.maximum) == (0, None, None, None)


@pytest.mark.parametrize(
    ("low", "high", "expected"), [(290, 302, [293.4, 301.8]), (77.2, 77.2, [77.2]), (400, 500, [])]
)
def test_range_filter_includes_boundaries(
    registry: ExperimentRegistry, low: float, high: float, expected: list[float]
) -> None:
    assert [e.result for e in registry.filter_by_range(low, high, "temperature")] == expected


def test_experiments_are_ordered_by_date(registry: ExperimentRegistry) -> None:
    dates = [e.date for e in registry.sorted_by_date()]

    assert dates == sorted(dates) and dates[0] == date(2026, 2, 3)


def test_statistics_by_researcher_uses_join_and_group_by(registry: ExperimentRegistry) -> None:
    rows = {name: (count, low, high) for name, count, _, low, high in registry.statistics_by_researcher()}

    assert rows["Olena Kovalenko"] == (2, 293.4, 301.8)
    assert set(rows) == {"Olena Kovalenko", "Taras Hnatiuk", "Andrii Bondar"}


def test_pagination(registry: ExperimentRegistry, db_session: Session) -> None:
    page = ExperimentRepository(db_session).list_all(limit=2, offset=1)

    assert [e.result for e in page] == [101.3, 301.8]


# ---------------------------------------------------------------- transactions
def test_invalid_record_rolls_back_whole_series(registry: ExperimentRegistry) -> None:
    series = [
        NewExperiment("Fuel cell", "Iryna Melnyk", "voltage", 0.71, date(2026, 3, 13)),
        NewExperiment("Broken sensor", "Maria Shevchuk", "temperature", -5.0, date(2026, 3, 18)),
    ]

    with pytest.raises(ExperimentValidationError, match="outside"):
        registry.add_series(series)

    assert registry.statistics().count == len(DATA)
    assert registry.find_by_researcher("Iryna Melnyk") == []  # researcher insert rolled back too


class UncheckedRegistry(ExperimentRegistry):
    """Skips application validation so that the database CHECK constraint is reached."""

    def _validate(self, item: NewExperiment) -> None:
        return None


def test_database_constraint_violation_rolls_back(
    registry: ExperimentRegistry, session_factory: sessionmaker[Session]
) -> None:
    series = [
        NewExperiment("Valid", "Olena Kovalenko", "temperature", 1.0, date(2026, 1, 1)),
        NewExperiment("", "Olena Kovalenko", "temperature", 1.0, date(2026, 1, 1)),
    ]

    with pytest.raises(ExperimentValidationError, match="CHECK constraint") as exc_info:
        UncheckedRegistry(session_factory).add_series(series)

    assert isinstance(exc_info.value.__cause__, IntegrityError)
    assert registry.statistics().count == len(DATA)
