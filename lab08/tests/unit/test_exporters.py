import json
from datetime import date
from pathlib import Path

import pytest

from experiment_registry.exceptions import ExportError
from experiment_registry.importer.exporters import AtomicWriter, export_errors_csv, export_json


def test_export_json_serializes_dates(tmp_path: Path) -> None:
    target = export_json(tmp_path / "out.json", {"date": date(2026, 2, 3), "values": [1.5]})

    assert json.loads(target.read_text(encoding="utf-8")) == {"date": "2026-02-03", "values": [1.5]}


def test_export_json_creates_missing_directories_when_allowed(tmp_path: Path) -> None:
    target = export_json(tmp_path / "a" / "b" / "out.json", {"ok": True}, create_dirs=True)

    assert target.exists()


def test_failed_serialization_keeps_previous_output(tmp_path: Path) -> None:
    target = export_json(tmp_path / "out.json", {"version": 1})

    with pytest.raises(ExportError) as exc_info:
        export_json(target, {"version": 2, "bad": object()})

    assert isinstance(exc_info.value.__cause__, TypeError)
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 1}
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_writer_removes_temp_file_on_error(tmp_path: Path) -> None:
    target = tmp_path / "report.txt"

    with pytest.raises(RuntimeError), AtomicWriter(target) as file:
        file.write("partial")
        raise RuntimeError("interrupted")

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_atomic_writer_without_directory_raises_export_error(tmp_path: Path) -> None:
    with pytest.raises(ExportError), AtomicWriter(tmp_path / "missing" / "out.json"):
        pass


def test_export_errors_csv_writes_header_and_rows(tmp_path: Path) -> None:
    rows = [{"line": "4", "field": "result", "value": "wrong", "error": "must be a number"}]

    count = export_errors_csv(tmp_path / "rejected.csv", rows)

    lines = (tmp_path / "rejected.csv").read_text(encoding="utf-8").splitlines()
    assert count == 1
    assert lines == ["line,field,value,error", "4,result,wrong,must be a number"]
