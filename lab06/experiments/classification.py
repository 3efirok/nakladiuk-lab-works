"""Function with three branches for the branch-coverage experiment."""


def classify_accuracy(relative_error: float) -> str:
    if relative_error <= 0.01:
        return "high"
    if relative_error <= 0.05:
        return "acceptable"
    return "low"
