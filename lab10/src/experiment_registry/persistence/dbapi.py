"""Plain Python DB-API (sqlite3) access with parameterized SQL queries."""

import sqlite3
from pathlib import Path

# Equivalent SQL schema (the real schema is created by Alembic migrations).
SCHEMA_SQL = """
CREATE TABLE researchers (
    id          INTEGER PRIMARY KEY,
    full_name   VARCHAR(120) NOT NULL UNIQUE,
    email       VARCHAR(255) UNIQUE,
    department  VARCHAR(80)  NOT NULL
);

CREATE TABLE experiments (
    id            INTEGER PRIMARY KEY,
    name          VARCHAR(200) NOT NULL CHECK (length(name) > 0),
    researcher_id INTEGER      NOT NULL REFERENCES researchers (id) ON DELETE CASCADE,
    parameter     VARCHAR(50)  NOT NULL CHECK (length(parameter) > 0),
    result        FLOAT        NOT NULL,
    date          DATE         NOT NULL,
    notes         VARCHAR(500)
);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def search_by_researcher(connection: sqlite3.Connection, researcher: str) -> list[sqlite3.Row]:
    """Parameterized query: the value is passed separately, never formatted into SQL."""
    sql = """
        SELECT e.id, e.name, r.full_name AS researcher, e.parameter, e.result, e.date
        FROM experiments AS e
        JOIN researchers AS r ON r.id = e.researcher_id
        WHERE lower(r.full_name) = lower(?)
        ORDER BY e.date
    """
    return connection.execute(sql, (researcher,)).fetchall()


def search_by_result_range(
    connection: sqlite3.Connection, low: float, high: float, parameter: str | None = None
) -> list[sqlite3.Row]:
    sql = """
        SELECT e.id, e.name, e.parameter, e.result, e.date
        FROM experiments AS e
        WHERE e.result BETWEEN :low AND :high
          AND (:parameter IS NULL OR e.parameter = :parameter)
        ORDER BY e.result
    """
    return connection.execute(sql, {"low": low, "high": high, "parameter": parameter}).fetchall()


def aggregate_by_parameter(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    sql = """
        SELECT parameter, COUNT(*) AS count, ROUND(AVG(result), 3) AS average,
               MIN(result) AS minimum, MAX(result) AS maximum
        FROM experiments
        GROUP BY parameter
        ORDER BY parameter
    """
    return connection.execute(sql).fetchall()
