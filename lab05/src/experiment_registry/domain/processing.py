"""The same behaviour (CSV line -> validated text line) built in two ways.

1. Inheritance: BaseResultProcessor defines the algorithm, CsvResultProcessor fills steps.
2. Composition: ResultProcessor *has* a parser, a validator and a formatter.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from experiment_registry.domain.value_objects import ResultRange
from experiment_registry.exceptions import ExperimentValidationError

Fields = dict[str, str]
COLUMNS = ("experiment_id", "name", "researcher", "parameter", "result", "date")


# ----------------------------------------------------------------- inheritance
class BaseResultProcessor(ABC):
    def __init__(self, interval: ResultRange) -> None:
        self.interval = interval

    def process(self, line: str) -> str:
        fields = self.parse(line)
        self.validate(fields)
        return self.format(fields)

    @abstractmethod
    def parse(self, line: str) -> Fields: ...

    def validate(self, fields: Fields) -> None:
        if float(fields["result"]) not in self.interval:
            raise ExperimentValidationError(f"result {fields['result']} outside {self.interval}")

    def format(self, fields: Fields) -> str:
        return f"#{fields['experiment_id']} {fields['researcher']}: {fields['result']}"


class CsvResultProcessor(BaseResultProcessor):
    def parse(self, line: str) -> Fields:
        return dict(zip(COLUMNS, line.strip().split(","), strict=True))


# ----------------------------------------------------------------- composition
class LineParser(Protocol):
    def parse(self, line: str) -> Fields: ...


class FieldValidator(Protocol):
    def validate(self, fields: Fields) -> None: ...


class FieldFormatter(Protocol):
    def format(self, fields: Fields) -> str: ...


class CsvLineParser:
    def __init__(self, delimiter: str = ",") -> None:
        self.delimiter = delimiter

    def parse(self, line: str) -> Fields:
        return dict(zip(COLUMNS, line.strip().split(self.delimiter), strict=True))


class RangeValidator:
    def __init__(self, interval: ResultRange) -> None:
        self.interval = interval

    def validate(self, fields: Fields) -> None:
        if float(fields["result"]) not in self.interval:
            raise ExperimentValidationError(f"result {fields['result']} outside {self.interval}")


class TextFormatter:
    def format(self, fields: Fields) -> str:
        return f"#{fields['experiment_id']} {fields['researcher']}: {fields['result']}"


class ResultProcessor:
    def __init__(self, parser: LineParser, validator: FieldValidator, formatter: FieldFormatter) -> None:
        self.parser = parser
        self.validator = validator
        self.formatter = formatter

    def process(self, line: str) -> str:
        fields = self.parser.parse(line)
        self.validator.validate(fields)
        return self.formatter.format(fields)
