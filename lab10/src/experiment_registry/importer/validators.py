"""Validation of external records and conversion into typed payloads."""

import math
from datetime import date

from experiment_registry.domain.dto import ExperimentPayload
from experiment_registry.exceptions import RecordValidationError
from experiment_registry.importer.config import ValidationConfig
from experiment_registry.importer.readers import Row


def _required(row: Row, field: str, line: int) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise RecordValidationError("value is required", line=line, field=field, value=value)
    return value


def validate_record(
    row: Row, line: int, rules: ValidationConfig, today: date | None = None
) -> ExperimentPayload:
    """Return a typed payload or raise RecordValidationError (with the original cause chained)."""
    raw_id = _required(row, "experiment_id", line)
    try:
        experiment_id = int(raw_id)
    except ValueError as error:
        raise RecordValidationError(
            "must be an integer", line=line, field="experiment_id", value=raw_id
        ) from error
    if experiment_id <= 0:
        raise RecordValidationError("must be positive", line=line, field="experiment_id", value=raw_id)

    name = _required(row, "name", line)
    researcher = " ".join(_required(row, "researcher", line).split())

    parameter = _required(row, "parameter", line).lower()
    if parameter not in rules.allowed_parameters:
        raise RecordValidationError(
            f"allowed: {sorted(rules.allowed_parameters)}", line=line, field="parameter", value=parameter
        )

    raw_result = _required(row, "result", line)
    try:
        result = float(raw_result)
    except ValueError as error:
        raise RecordValidationError(
            "must be a number", line=line, field="result", value=raw_result
        ) from error
    if not math.isfinite(result) or not rules.min_result <= result <= rules.max_result:
        raise RecordValidationError(
            f"must be within [{rules.min_result}, {rules.max_result}]",
            line=line,
            field="result",
            value=raw_result,
        )

    raw_date = _required(row, "date", line)
    try:
        day = date.fromisoformat(raw_date)
    except ValueError as error:
        raise RecordValidationError(
            "must be a date YYYY-MM-DD", line=line, field="date", value=raw_date
        ) from error
    if day > (today or date.today()):
        raise RecordValidationError("date is in the future", line=line, field="date", value=raw_date)

    return ExperimentPayload(
        experiment_id=experiment_id,
        name=name,
        researcher=researcher,
        parameter=parameter,
        result=result,
        unit=rules.allowed_parameters[parameter],
        date=day.isoformat(),
    )
