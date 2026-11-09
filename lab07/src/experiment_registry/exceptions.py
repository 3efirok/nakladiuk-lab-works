"""Custom exceptions of the experiment registry."""


class ExperimentError(Exception):
    """Base class for all errors of the application."""


class ExperimentValidationError(ExperimentError):
    """Raised when experiment data are invalid."""


class DuplicateExperimentError(ExperimentError):
    """Raised when an experiment with the same ID already exists."""


class ExperimentNotFoundError(ExperimentError):
    """Raised when an experiment with the given ID does not exist."""


class IncompatibleMeasurementError(ExperimentValidationError):
    """Raised when a measurement does not match the experiment parameter or unit."""


class ConfigurationError(ExperimentError):
    """Configuration file is missing, malformed or contains invalid values."""


class DataImportError(ExperimentError):
    """Input data cannot be read or the import must be aborted."""


class RecordValidationError(DataImportError):
    """A single input record is invalid."""

    def __init__(self, message: str, *, line: int, field: str, value: object) -> None:
        super().__init__(f"line {line}: {field}={value!r}: {message}")
        self.line = line
        self.field = field
        self.value = value


class ExportError(ExperimentError):
    """Output file cannot be written."""
