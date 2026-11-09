"""Input datasets: a small curated sample and a generator of large datasets."""

import random
from datetime import date, datetime, timedelta

from experiment_registry.config import DATE_FORMAT
from experiment_registry.models import Experiment

# Raw rows are immutable tuples: (id, name, researcher, parameter, result, date).
RAW_EXPERIMENTS: tuple[tuple[int, str, str, str, float, str], ...] = (
    (1, "Thermal conductivity of Al alloy", "Olena Kovalenko", "temperature", 293.4, "2026-02-03"),
    (2, "Gas compression test", "Taras Hnatiuk", "pressure", 101.3, "2026-02-05"),
    (3, "Thermal conductivity of Cu", "Olena Kovalenko", "temperature", 301.8, "2026-02-10"),
    (4, "Battery discharge cycle", "Iryna Melnyk", "voltage", 3.71, "2026-02-12"),
    (5, "Cryogenic cooling run", "Andrii Bondar", "temperature", 77.2, "2026-02-18"),
    (6, "Vacuum chamber leak test", "Taras Hnatiuk", "pressure", 0.8, "2026-02-21"),
    (7, "Heat exchanger efficiency", "Olena Kovalenko", "temperature", 348.9, "2026-03-02"),
    (8, "Solar cell output", "Iryna Melnyk", "voltage", 0.62, "2026-03-04"),
    (9, "Hydraulic press calibration", "Taras Hnatiuk", "pressure", 250.4, "2026-03-06"),
    (10, "Superconductor transition", "Andrii Bondar", "temperature", 92.1, "2026-03-11"),
    (11, "Fuel cell stack test", "Iryna Melnyk", "voltage", 0.71, "2026-03-13"),
    (12, "Thermal shock resistance", "Olena Kovalenko", "temperature", 412.5, "2026-03-17"),
    (13, "Weather balloon ascent", "Maria Shevchuk", "pressure", 26.5, "2026-03-20"),
    (14, "Thermocouple drift check", "Maria Shevchuk", "temperature", 298.0, "2026-03-24"),
)

RESEARCHERS = (
    "Olena Kovalenko",
    "Taras Hnatiuk",
    "Iryna Melnyk",
    "Andrii Bondar",
    "Maria Shevchuk",
    "Petro Lysenko",
    "Sofiia Romaniuk",
    "Dmytro Savchuk",
)
PARAMETERS = {
    "temperature": (60.0, 450.0),
    "pressure": (0.5, 300.0),
    "voltage": (0.1, 12.0),
    "frequency": (10.0, 5000.0),
    "concentration": (0.001, 2.0),
}


def parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FORMAT).date()


def load_experiments() -> list[Experiment]:
    """Convert raw tuples into Experiment objects."""
    return [
        Experiment(
            experiment_id=experiment_id,
            name=name,
            researcher=researcher,
            parameter=parameter,
            result=result,
            date=parse_date(day),
        )
        for experiment_id, name, researcher, parameter, result, day in RAW_EXPERIMENTS
    ]


def generate_experiments(count: int, seed: int = 15) -> list[Experiment]:
    """Generate a reproducible synthetic dataset of `count` experiments."""
    rng = random.Random(seed)
    start = date(2025, 1, 1)
    parameters = list(PARAMETERS)
    experiments = []
    for experiment_id in range(1, count + 1):
        parameter = rng.choice(parameters)
        low, high = PARAMETERS[parameter]
        experiments.append(
            Experiment(
                experiment_id=experiment_id,
                name=f"{parameter.capitalize()} run {experiment_id}",
                researcher=rng.choice(RESEARCHERS),
                parameter=parameter,
                result=round(rng.uniform(low, high), 3),
                date=start + timedelta(days=rng.randrange(730)),
            )
        )
    return experiments
