"""Serialization and atomic output."""

import csv
import json
import os
import tempfile
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from types import TracebackType
from typing import IO, Any, Literal

from experiment_registry.exceptions import ExportError


class ExperimentJSONEncoder(json.JSONEncoder):
    """Serializes dates and other non-standard values."""

    def default(self, o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o)
        return super().default(o)


class AtomicWriter:
    """Context manager: write into a temporary file, then atomically replace the target.

    If the block raises, the temporary file is removed and the previous target stays intact.
    """

    def __init__(self, target: Path, create_dirs: bool = False, encoding: str = "utf-8") -> None:
        self.target = target
        self.create_dirs = create_dirs
        self.encoding = encoding
        self._tmp_path: Path | None = None
        self._file: IO[str] | None = None

    def __enter__(self) -> IO[str]:
        try:
            if self.create_dirs:
                self.target.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(dir=self.target.parent, prefix=f".{self.target.name}.",
                                        suffix=".tmp")
        except OSError as error:
            raise ExportError(f"Cannot create temporary file for {self.target}") from error
        self._tmp_path = Path(name)
        self._file = os.fdopen(fd, "w", encoding=self.encoding, newline="")
        return self._file

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 tb: TracebackType | None) -> Literal[False]:
        assert self._file is not None and self._tmp_path is not None
        self._file.close()
        if exc_type is not None:
            self._tmp_path.unlink(missing_ok=True)
            return False  # propagate the original exception
        try:
            os.replace(self._tmp_path, self.target)
        except OSError as error:
            self._tmp_path.unlink(missing_ok=True)
            raise ExportError(f"Cannot replace {self.target}") from error
        return False


def export_json(path: Path, data: Any, indent: int = 2, create_dirs: bool = False) -> Path:
    """Serialize data to JSON atomically; any failure is reported as ExportError."""
    try:
        with AtomicWriter(path, create_dirs) as file:
            json.dump(data, file, indent=indent or None, ensure_ascii=False, cls=ExperimentJSONEncoder)
            file.write("\n")
    except ExportError:
        raise
    except (TypeError, ValueError, OSError) as error:
        raise ExportError(f"JSON export to {path} failed: {error}") from error
    return path


def export_errors_csv(path: Path, errors: Iterable[dict[str, str]], create_dirs: bool = False) -> int:
    """Write rejected records with the reason into a separate CSV file."""
    count = 0
    try:
        with AtomicWriter(path, create_dirs) as file:
            writer = csv.DictWriter(file, fieldnames=["line", "field", "value", "error"])
            writer.writeheader()
            for row in errors:
                writer.writerow(row)
                count += 1
    except OSError as error:
        raise ExportError(f"Cannot write error report {path}") from error
    return count
