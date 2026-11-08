"""Streaming readers for CSV, JSON and JSON Lines with a common interface."""

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from experiment_registry.exceptions import DataImportError

REQUIRED_COLUMNS = ("experiment_id", "name", "researcher", "parameter", "result", "date")
Row = dict[str, str]


class RecordReader(Protocol):
    def read(self, path: Path) -> Iterator[tuple[int, Row]]: ...


class CsvReader:
    """Yields (line_number, row) lazily; the file is never loaded completely."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]:
        try:
            with path.open(encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
                if missing:
                    raise DataImportError(f"{path}: missing columns {sorted(missing)}")
                for row in reader:
                    yield reader.line_num, {key: (value or "") for key, value in row.items() if key}
        except UnicodeDecodeError as error:
            raise DataImportError(f"{path}: file is not valid UTF-8") from error
        except OSError as error:
            raise DataImportError(f"{path}: cannot read file ({error.strerror})") from error


class JsonLinesReader:
    """One JSON object per line (suitable for very large files)."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]:
        try:
            with path.open(encoding="utf-8") as file:
                for number, line in enumerate(file, start=1):
                    if line.strip():
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as error:
                            raise DataImportError(f"{path}:{number}: invalid JSON") from error
                        yield number, {key: str(value) for key, value in data.items()}
        except OSError as error:
            raise DataImportError(f"{path}: cannot read file ({error.strerror})") from error


READERS: dict[str, RecordReader] = {".csv": CsvReader(), ".jsonl": JsonLinesReader()}


def reader_for(path: Path) -> RecordReader:
    """Choose a reader by file extension."""
    try:
        return READERS[path.suffix.lower()]
    except KeyError:
        raise DataImportError(f"Unsupported input format: {path.suffix!r}") from None
