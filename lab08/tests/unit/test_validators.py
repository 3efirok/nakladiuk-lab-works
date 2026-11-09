from datetime import date

import pytest

from experiment_registry.exceptions import RecordValidationError
from experiment_registry.importer.config import ValidationConfig
from experiment_registry.importer.validators import validate_record

RULES = ValidationConfig({"temperature": "K", "pressure": "kPa"}, min_result=0.0, max_result=1000.0)
TODAY = date(2026, 11, 8)


def make_row(**overrides: str) -> dict[str, str]:
    row = {"experiment_id": "1", "name": "Thermal conductivity", "researcher": "Olena  Kovalenko",
           "parameter": "Temperature", "result": "293.4", "date": "2026-02-03"}
    row.update(overrides)
    return row


def test_valid_record_becomes_typed_payload_with_unit() -> None:
    payload = validate_record(make_row(), line=2, rules=RULES, today=TODAY)

    assert payload == {"experiment_id": 1, "name": "Thermal conductivity", "researcher": "Olena Kovalenko",
                       "parameter": "temperature", "result": 293.4, "unit": "K", "date": "2026-02-03"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("experiment_id", "x1"), ("experiment_id", "0"), ("experiment_id", ""),
        ("name", "  "), ("researcher", ""),
        ("parameter", "colour"),
        ("result", "wrong"), ("result", "nan"), ("result", "-0.1"), ("result", "1000.01"),
        ("date", "2026-02-30"), ("date", "03.02.2026"), ("date", "2026-11-09"),
    ],
)
def test_invalid_field_raises_record_validation_error(field: str, value: str) -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        validate_record(make_row(**{field: value}), line=7, rules=RULES, today=TODAY)

    assert exc_info.value.field == field
    assert exc_info.value.line == 7


@pytest.mark.parametrize("value", ["0", "0.0", "1000", "1000.0"])
def test_boundary_results_are_accepted(value: str) -> None:
    assert validate_record(make_row(result=value), line=2, rules=RULES, today=TODAY)["result"] == float(value)


def test_today_is_not_in_the_future() -> None:
    assert validate_record(make_row(date="2026-11-08"), line=2, rules=RULES, today=TODAY)["date"] == "2026-11-08"


def test_numeric_error_keeps_original_cause() -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        validate_record(make_row(result="wrong"), line=3, rules=RULES, today=TODAY)

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert "line 3: result='wrong'" in str(exc_info.value)


def test_missing_column_is_reported_as_required_value() -> None:
    row = make_row()
    del row["date"]

    with pytest.raises(RecordValidationError, match="required"):
        validate_record(row, line=2, rules=RULES, today=TODAY)
