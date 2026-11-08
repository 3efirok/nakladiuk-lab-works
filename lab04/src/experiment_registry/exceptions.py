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
