"""Generation of large CSV test files with a share of invalid records."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from experiment_registry.data import PARAMETERS, RESEARCHERS
from experiment_registry.streaming import CSV_HEADER

# (column index, broken value) pairs used to corrupt rows on purpose.
INVALID_VALUES = (
    (4, "error"),       # non-numeric result
    (2, ""),            # empty researcher
    (5, "2026-13-45"),  # impossible date
    (3, "colour"),      # unknown parameter
    (4, "1e9"),         # result outside the allowed range
)


def generate_test_file(path: Path, count: int, invalid_ratio: float = 0.01, seed: int = 15) -> Path:
    """Write `count` experiment rows; about invalid_ratio of them are broken on purpose."""
    rng = random.Random(seed)
    start = date(2025, 1, 1)
    parameters = list(PARAMETERS)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)
        for experiment_id in range(1, count + 1):
            parameter = rng.choice(parameters)
            low, high = PARAMETERS[parameter]
            row = [
                str(experiment_id),
                f"{parameter.capitalize()} run {experiment_id}",
                rng.choice(RESEARCHERS),
                parameter,
                f"{rng.uniform(low, high):.3f}",
                (start + timedelta(days=rng.randrange(730))).isoformat(),
            ]
            if rng.random() < invalid_ratio:
                column, broken = rng.choice(INVALID_VALUES)
                row[column] = broken
            writer.writerow(row)
    return path
