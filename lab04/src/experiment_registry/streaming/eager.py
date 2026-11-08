"""Eager counterpart of the pipeline: every stage materializes a full list."""

import csv
from pathlib import Path

from experiment_registry.data import PARAMETERS
from experiment_registry.exceptions import ExperimentValidationError
from experiment_registry.models import Experiment
from experiment_registry.streaming import CSV_HEADER
from experiment_registry.streaming.parsers import to_experiment


def load_valid_experiments(path: Path) -> list[Experiment]:
    """Read the whole file, then parse, then validate - three full lists in memory."""
    with path.open(encoding="utf-8", newline="") as file:
        lines = file.readlines()[1:]
    rows = [dict(zip(CSV_HEADER, fields, strict=False)) for fields in csv.reader(lines)]
    experiments = []
    for row in rows:
        try:
            item = to_experiment(row)
        except (ValueError, KeyError, ExperimentValidationError):
            continue
        if item.parameter in PARAMETERS:
            experiments.append(item)
    return experiments


def eager_filter(path: Path, low: float, high: float) -> list[Experiment]:
    return [item for item in load_valid_experiments(path) if low <= item.result <= high]
