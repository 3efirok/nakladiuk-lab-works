"""Custom exceptions of the experiment registry."""


class ExperimentError(Exception):
    """Base class for all errors of the application."""


class ExperimentValidationError(ExperimentError):
    """Raised when experiment data are invalid."""


class DuplicateExperimentError(ExperimentError):
    """Raised when an experiment with the same ID already exists."""
