"""Lab 7 scenario: persistence layer (ORM repositories, transactions, DB-API)."""

from collections.abc import Sequence
from contextlib import closing
from datetime import date

from sqlalchemy import Engine, inspect
from sqlalchemy.engine import make_url

from experiment_registry.exceptions import ExperimentValidationError
from experiment_registry.persistence import dbapi
from experiment_registry.persistence.database import create_db_engine, create_session_factory
from experiment_registry.persistence.orm import ExperimentORM
from experiment_registry.persistence.services import ExperimentRegistry, NewExperiment

SERIES = [
    NewExperiment(
        "Thermal conductivity of Al alloy", "Olena Kovalenko", "temperature", 293.4, date(2026, 2, 3)
    ),
    NewExperiment("Gas compression test", "Taras Hnatiuk", "pressure", 101.3, date(2026, 2, 5)),
    NewExperiment("Thermal conductivity of Cu", "Olena Kovalenko", "temperature", 301.8, date(2026, 2, 10)),
    NewExperiment("Battery discharge cycle", "Iryna Melnyk", "voltage", 3.71, date(2026, 2, 12)),
    NewExperiment("Cryogenic cooling run", "Andrii Bondar", "temperature", 77.2, date(2026, 2, 18)),
    NewExperiment("Vacuum chamber leak test", "Taras Hnatiuk", "pressure", 0.8, date(2026, 2, 21)),
    NewExperiment(
        "Heat exchanger efficiency",
        "Olena Kovalenko",
        "temperature",
        348.9,
        date(2026, 3, 2),
        notes="repeat with insulation",
    ),
    NewExperiment("Solar cell output", "Iryna Melnyk", "voltage", 0.62, date(2026, 3, 4)),
]


def show(title: str, rows: Sequence[ExperimentORM]) -> None:
    print(f"\n{title}")
    for e in rows:
        notes = f"  [{e.notes}]" if e.notes else ""
        print(
            f"  #{e.id:<3} {e.date}  {e.name:<34} {e.researcher.full_name:<16} "
            f"{e.parameter:<12} {e.result:>8.2f}{notes}"
        )


def run_db_demo(url: str) -> int:
    engine = create_db_engine(url)
    try:
        return _demo(engine, url)
    finally:
        engine.dispose()  # close pooled connections


def _demo(engine: Engine, url: str) -> int:
    if not inspect(engine).has_table("experiments"):
        print("Database schema not found. Run: alembic upgrade head")
        return 2
    registry = ExperimentRegistry(create_session_factory(engine))

    ids = registry.add_series(SERIES)
    print(f"CREATE: inserted {len(ids)} experiments in one transaction, IDs {ids[0]}..{ids[-1]}")
    show("READ: experiments of Olena Kovalenko", registry.find_by_researcher("Olena Kovalenko"))

    stats = registry.statistics("temperature")
    print(
        f"\nAggregates (temperature): COUNT={stats.count} AVG={stats.average:.2f} "
        f"MIN={stats.minimum} MAX={stats.maximum}"
    )
    show("Range filter: temperature in [290, 320]", registry.filter_by_range(290, 320, "temperature"))

    updated = registry.update_result(ids[1], 102.0)
    print(f"\nUPDATE: experiment #{updated.id} result -> {updated.result}")
    registry.delete(ids[5])
    print(f"DELETE: experiment #{ids[5]} removed")
    show("Sorted by date (ORDER BY date)", registry.sorted_by_date())

    print("\nStatistics by researcher (JOIN + GROUP BY):")
    for name, count, avg, minimum, maximum in registry.statistics_by_researcher():
        print(f"  {name:<16} n={count}  avg={avg:8.2f}  min={minimum:8.2f}  max={maximum:8.2f}")

    before = registry.statistics().count
    broken = [
        NewExperiment("Fuel cell stack test", "Iryna Melnyk", "voltage", 0.71, date(2026, 3, 13)),
        NewExperiment("Thermal shock resistance", "Olena Kovalenko", "temperature", 412.5, date(2026, 3, 17)),
        NewExperiment("Broken sensor run", "Maria Shevchuk", "temperature", -5.0, date(2026, 3, 18)),
    ]
    try:
        registry.add_series(broken)
    except ExperimentValidationError as error:
        print(f"\nTRANSACTION: {error}")
    after = registry.statistics().count
    print(f"  rows before = {before}, after = {after} -> ROLLBACK, the first two records were not saved")

    database = make_url(url).database
    if database:
        # sqlite3's own context manager only commits; closing() really closes the connection
        with closing(dbapi.connect(database)) as connection:
            print("\nDB-API (sqlite3), parameterized queries:")
            for row in dbapi.search_by_researcher(connection, "taras hnatiuk"):
                print(f"  researcher=? -> #{row['id']} {row['name']} {row['result']}")
            for row in dbapi.search_by_result_range(connection, 0.5, 5.0, "voltage"):
                print(f"  BETWEEN :low AND :high -> #{row['id']} {row['name']} {row['result']}")
            injection = "x' OR '1'='1"
            found = dbapi.search_by_researcher(connection, injection)
            print(f"  injection attempt {injection!r}: {len(found)} rows")
            for row in dbapi.aggregate_by_parameter(connection):
                print(
                    f"  {row['parameter']:<12} COUNT={row['count']} AVG={row['average']} "
                    f"MIN={row['minimum']} MAX={row['maximum']}"
                )
    return 0
