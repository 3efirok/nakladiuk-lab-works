"""Console entry point of the experiment registry."""

import sys
from datetime import date, datetime

from experiment_registry.config import DATE_FORMAT, NAME_COLUMN_WIDTH
from experiment_registry.exceptions import ExperimentError
from experiment_registry.models import Experiment
from experiment_registry.services import (
    add_experiment,
    calculate_average_result,
    calculate_statistics,
    filter_by_parameter,
    filter_by_result_range,
    find_by_researcher,
    find_min_max,
    next_experiment_id,
    search,
    sort_experiments,
)


def create_demo_experiments() -> list[Experiment]:
    """Return a small demo dataset of experiments."""
    rows = [
        ("Thermal conductivity of Al alloy", "Olena Kovalenko", "temperature", 293.4, "2026-02-03"),
        ("Gas compression test", "Taras Hnatiuk", "pressure", 101.3, "2026-02-05"),
        ("Thermal conductivity of Cu", "Olena Kovalenko", "temperature", 301.8, "2026-02-10"),
        ("Battery discharge cycle", "Iryna Melnyk", "voltage", 3.71, "2026-02-12"),
        ("Cryogenic cooling run", "Andrii Bondar", "temperature", 77.2, "2026-02-18"),
        ("Vacuum chamber leak test", "Taras Hnatiuk", "pressure", 0.8, "2026-02-21"),
        ("Heat exchanger efficiency", "Olena Kovalenko", "temperature", 348.9, "2026-03-02"),
        ("Solar cell output", "Iryna Melnyk", "voltage", 0.62, "2026-03-04"),
    ]
    return [
        Experiment(
            experiment_id=index,
            name=name,
            researcher=researcher,
            parameter=parameter,
            result=result,
            date=datetime.strptime(day, DATE_FORMAT).date(),
        )
        for index, (name, researcher, parameter, result, day) in enumerate(rows, start=1)
    ]


def print_experiments(title: str, experiments: list[Experiment]) -> None:
    """Print experiments as a table."""
    print(f"\n{title}")
    if not experiments:
        print("  (no experiments)")
        return
    print(f"  {'ID':>3}  {'Name':<{NAME_COLUMN_WIDTH}} {'Researcher':<16} "
          f"{'Parameter':<12} {'Result':>9}  Date")
    for item in experiments:
        print(
            f"  {item.experiment_id:>3}  {item.name:<{NAME_COLUMN_WIDTH}} "
            f"{item.researcher:<16} {item.parameter:<12} {item.result:>9.2f}  "
            f"{item.date.isoformat()}"
        )


def run_demo(experiments: list[Experiment]) -> None:
    """Demonstrate all business operations on the demo dataset."""
    print_experiments("All experiments:", experiments)

    new_experiment = Experiment(
        experiment_id=next_experiment_id(experiments),
        name="Thermal conductivity of steel",
        researcher="Andrii Bondar",
        parameter="temperature",
        result=315.6,
        date=date(2026, 3, 9),
    )
    add_experiment(experiments, new_experiment)
    print(f"\nAdded experiment: {new_experiment.label}")

    researcher = "Olena Kovalenko"
    print_experiments(
        f"Experiments of {researcher}:", find_by_researcher(experiments, researcher)
    )

    temperature = filter_by_parameter(experiments, "temperature")
    average = calculate_average_result(temperature)
    if average is not None:
        print(f"\nAverage temperature result: {average:.2f}")

    bounds = find_min_max(temperature)
    if bounds is not None:
        minimum, maximum = bounds
        print(f"Minimum: {minimum.result:.2f} -> {minimum.label}")
        print(f"Maximum: {maximum.result:.2f} -> {maximum.label}")

    print_experiments(
        "Temperature results in range [290, 320]:",
        filter_by_result_range(temperature, 290, 320),
    )
    print_experiments(
        "Search: researcher='Taras Hnatiuk', parameter='pressure':",
        search(experiments, researcher="Taras Hnatiuk", parameter="pressure"),
    )
    print_experiments(
        "Sorted by result (descending, top 3):",
        sort_experiments(experiments, key="result", reverse=True)[:3],
    )


def read_float(prompt: str) -> float:
    """Read a float from the keyboard until the value is valid."""
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a number.")


def read_date(prompt: str) -> date:
    """Read a date in ISO format from the keyboard."""
    while True:
        raw = input(prompt).strip()
        try:
            return datetime.strptime(raw, DATE_FORMAT).date()
        except ValueError:
            print(f"  Please enter a date in format {DATE_FORMAT}.")


def input_experiment(experiments: list[Experiment]) -> None:
    """Create an experiment from keyboard input and add it to the registry."""
    try:
        experiment = Experiment(
            experiment_id=next_experiment_id(experiments),
            name=input("Name: "),
            researcher=input("Researcher: "),
            parameter=input("Parameter: "),
            result=read_float("Result: "),
            date=read_date("Date (YYYY-MM-DD): "),
        )
        add_experiment(experiments, experiment)
    except ExperimentError as error:
        print(f"  Error: {error}")
    else:
        print(f"  Added: {experiment.label}")


def print_menu() -> None:
    print()
    print("1. Show all experiments")
    print("2. Add experiment")
    print("3. Find by researcher")
    print("4. Statistics (average / min / max)")
    print("5. Filter by result range")
    print("6. Sort by date")
    print("0. Exit")


def run_menu(experiments: list[Experiment]) -> None:
    """Run the menu-driven console interface."""
    while True:
        print_menu()
        command = input("Select command: ").strip()
        if command == "1":
            print_experiments("All experiments:", experiments)
        elif command == "2":
            input_experiment(experiments)
        elif command == "3":
            name = input("Researcher: ")
            print_experiments(f"Experiments of {name}:", find_by_researcher(experiments, name))
        elif command == "4":
            parameter = input("Parameter (empty = all): ").strip()
            selected = filter_by_parameter(experiments, parameter) if parameter else experiments
            stats = calculate_statistics(selected)
            if stats is None:
                print("  No data.")
            else:
                print(f"  count={stats.count} average={stats.average:.2f} "
                      f"min={stats.minimum:.2f} max={stats.maximum:.2f}")
        elif command == "5":
            low = read_float("Low: ")
            high = read_float("High: ")
            try:
                found = filter_by_result_range(experiments, low, high)
            except ExperimentError as error:
                print(f"  Error: {error}")
            else:
                print_experiments(f"Results in [{low}, {high}]:", found)
        elif command == "6":
            print_experiments("Sorted by date:", sort_experiments(experiments, key="date"))
        elif command == "0":
            print("Goodbye.")
            break
        else:
            print("Unknown command.")


def main() -> None:
    """Run the demo scenario or the interactive menu (--menu)."""
    experiments = create_demo_experiments()
    if "--menu" in sys.argv[1:]:
        run_menu(experiments)
    else:
        run_demo(experiments)


if __name__ == "__main__":
    main()
