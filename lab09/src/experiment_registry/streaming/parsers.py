"""Parsing and transformation stages of the streaming pipeline."""

import csv
from collections.abc import Iterable, Iterator
from datetime import date

from experiment_registry.models import Experiment
from experiment_registry.streaming import CSV_HEADER

RawRow = dict[str, str]


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Drop blank lines and comments, strip trailing whitespace."""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            yield stripped


def parse_rows(lines: Iterable[str]) -> Iterator[RawRow]:
    """Parse CSV lines into dictionaries (csv.reader consumes the iterator lazily)."""
    for fields in csv.reader(lines):
        yield dict(zip(CSV_HEADER, (field.strip() for field in fields), strict=False))


def to_experiment(row: RawRow) -> Experiment:
    """Convert a raw row into an Experiment (raises ValueError on bad data)."""
    return Experiment(
        experiment_id=int(row["experiment_id"]),
        name=row["name"],
        researcher=row["researcher"],
        parameter=row["parameter"].lower(),
        result=float(row["result"]),
        date=date.fromisoformat(row["date"]),
    )


def normalize(experiments: Iterable[Experiment]) -> Iterator[Experiment]:
    """Transformation stage: normalize text fields and round results."""
    for item in experiments:
        item.researcher = " ".join(item.researcher.split()).title()
        item.result = round(item.result, 3)
        yield item
