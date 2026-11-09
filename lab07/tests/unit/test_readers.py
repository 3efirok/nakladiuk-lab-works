from pathlib import Path

import pytest

from experiment_registry.exceptions import DataImportError, RecordValidationError
from experiment_registry.importer.config import ValidationConfig
from experiment_registry.importer.readers import CsvReader, JsonLinesReader, reader_for
from experiment_registry.importer.validators import validate_record

RULES = ValidationConfig({"temperature": "K"}, 0.0, 1000.0)


def test_csv_reader_yields_rows_with_line_numbers(csv_file: Path) -> None:
    rows = list(CsvReader().read(csv_file))

    assert [line for line, _ in rows] == [2, 3, 4, 5]
    assert rows[0][1]["researcher"] == "Olena Kovalenko"


def test_csv_reader_reports_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("experiment_id,name\n1,Test\n", encoding="utf-8")

    with pytest.raises(DataImportError, match="missing columns"):
        list(CsvReader().read(path))


def test_csv_reader_wraps_missing_file_error(tmp_path: Path) -> None:
    with pytest.raises(DataImportError) as exc_info:
        list(CsvReader().read(tmp_path / "missing.csv"))

    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


def test_csv_reader_rejects_non_utf8_file(tmp_path: Path) -> None:
    path = tmp_path / "cp1251.csv"
    path.write_bytes("experiment_id,name,researcher,parameter,result,date\n1,Тест,Олена,temperature,1,2026-01-01\n"
                     .encode("cp1251"))

    with pytest.raises(DataImportError, match="UTF-8"):
        list(CsvReader().read(path))


def test_json_lines_reader_parses_objects(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"experiment_id": 1, "result": 293.4}\n\n{"experiment_id": 2, "result": 1}\n',
                    encoding="utf-8")

    assert list(JsonLinesReader().read(path)) == [
        (1, {"experiment_id": "1", "result": "293.4"}),
        (3, {"experiment_id": "2", "result": "1"}),
    ]


def test_json_null_value_is_treated_as_missing(tmp_path: Path) -> None:
    """null must not turn into the string 'None' and pass validation as a researcher name."""
    path = tmp_path / "data.jsonl"
    path.write_text('{"experiment_id": 1, "name": "Run", "researcher": null, "parameter": "temperature",'
                    ' "result": 293.4, "date": "2026-02-03"}\n', encoding="utf-8")
    line, row = next(JsonLinesReader().read(path))

    with pytest.raises(RecordValidationError, match="researcher"):
        validate_record(row, line, RULES)


def test_invalid_json_line_raises_data_import_error(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"experiment_id": 1}\n{broken\n', encoding="utf-8")

    with pytest.raises(DataImportError, match=":2: invalid JSON"):
        list(JsonLinesReader().read(path))


@pytest.mark.parametrize(("name", "reader_type"), [("a.csv", CsvReader), ("a.JSONL", JsonLinesReader)])
def test_reader_is_chosen_by_extension(name: str, reader_type: type) -> None:
    assert isinstance(reader_for(Path(name)), reader_type)


def test_unsupported_extension_is_rejected() -> None:
    with pytest.raises(DataImportError, match="Unsupported"):
        reader_for(Path("data.xlsx"))
