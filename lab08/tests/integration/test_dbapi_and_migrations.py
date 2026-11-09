"""Integration tests: raw DB-API queries, Alembic migrations and the `db` sub-command."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from experiment_registry.main import main
from experiment_registry.persistence import dbapi

pytestmark = pytest.mark.integration
PROJECT = Path(__file__).resolve().parents[2]


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = dbapi.connect(tmp_path / "raw.db")
    connection.executescript(dbapi.SCHEMA_SQL)
    connection.executemany("INSERT INTO researchers (id, full_name, department) VALUES (?, ?, 'Physics')",
                           [(1, "Olena Kovalenko"), (2, "Taras Hnatiuk")])
    connection.executemany(
        "INSERT INTO experiments (name, researcher_id, parameter, result, date) VALUES (?, ?, ?, ?, ?)",
        [("Cu", 1, "temperature", 301.8, "2026-02-10"), ("Al", 1, "temperature", 293.4, "2026-02-03"),
         ("Gas", 2, "pressure", 101.3, "2026-02-05")],
    )
    yield connection
    connection.close()


def test_parameterized_search_by_researcher_orders_by_date(connection: sqlite3.Connection) -> None:
    rows = dbapi.search_by_researcher(connection, "OLENA KOVALENKO")

    assert [row["name"] for row in rows] == ["Al", "Cu"]


def test_sql_injection_is_treated_as_plain_value(connection: sqlite3.Connection) -> None:
    assert dbapi.search_by_researcher(connection, "x' OR '1'='1") == []


def test_range_query_and_aggregates(connection: sqlite3.Connection) -> None:
    assert [row["result"] for row in dbapi.search_by_result_range(connection, 100, 300)] == [101.3, 293.4]
    stats = {row["parameter"]: tuple(row)[1:] for row in dbapi.aggregate_by_parameter(connection)}
    assert stats["temperature"] == (2, 297.6, 293.4, 301.8)


def test_raw_schema_enforces_foreign_key(connection: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        connection.execute("INSERT INTO experiments (name, researcher_id, parameter, result, date) "
                           "VALUES ('Orphan', 99, 'temperature', 1, '2026-01-01')")


def alembic_config(url: str) -> Config:
    config = Config(str(PROJECT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def table_columns(url: str, table: str) -> set[str] | None:
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        if not inspector.has_table(table):
            return None
        return {column["name"] for column in inspector.get_columns(table)}
    finally:
        engine.dispose()


def test_migrations_upgrade_and_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = alembic_config(url)

    command.upgrade(config, "head")
    columns = table_columns(url, "experiments")
    assert columns is not None
    assert {"id", "name", "researcher_id", "parameter", "result", "date", "notes"} <= columns

    command.downgrade(config, "0001")
    columns = table_columns(url, "experiments")
    assert columns is not None and "notes" not in columns

    command.downgrade(config, "base")
    assert table_columns(url, "experiments") is None


def test_db_command_runs_demo_on_migrated_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                   capsys: pytest.CaptureFixture[str]) -> None:
    url = f"sqlite:///{tmp_path / 'demo.db'}"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    command.upgrade(alembic_config(url), "head")

    assert main(["db", "--url", url]) == 0
    out = capsys.readouterr().out
    assert "inserted 8 experiments" in out
    assert "ROLLBACK" in out and "rows before = 7, after = 7" in out
    assert "injection attempt" in out and ": 0 rows" in out


def test_db_command_without_schema_returns_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["db", "--url", f"sqlite:///{tmp_path / 'empty.db'}"]) == 2
    assert "alembic upgrade head" in capsys.readouterr().out
