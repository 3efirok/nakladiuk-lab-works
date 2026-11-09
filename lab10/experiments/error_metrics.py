"""Deliberately defective function for the coverage experiment (not part of the package)."""


def relative_error(measured: float, expected: float) -> float:
    """Defect: divides by the measured value and loses the absolute value."""
    return (measured - expected) / measured
