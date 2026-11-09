"""Lab 2 scenario: processing structured experiment data."""

from experiment_registry.analytics import (
    average_of,
    average_result,
    create_experiment,
    export_summary,
    make_counter,
    make_parameter_filter,
    make_range_filter,
    min_max_result,
    rank_results,
    researcher_statistics,
)
from experiment_registry.data import load_experiments
from experiment_registry.decorators import OPERATION_HISTORY
from experiment_registry.models import Experiment
from experiment_registry.processors import (
    build_index_by_id,
    build_index_by_name,
    count_by_parameter,
    filter_records,
    find_by_researcher,
    get_unique_researchers,
    group_by_researcher,
    group_nested,
    pipeline,
    sort_records,
)


def show(title: str, experiments: list[Experiment]) -> None:
    print(f"\n{title}")
    for item in experiments:
        print(
            f"  #{item.experiment_id:<3} {item.name:<34} {item.researcher:<16} "
            f"{item.parameter:<12} {item.result:>8.2f}  {item.date}"
        )


def run_analysis(researcher: str, low: float, high: float) -> None:
    experiments = load_experiments()
    experiments.append(
        create_experiment(
            experiment_id=15,
            name="Pressure sensor validation",
            researcher="Maria Shevchuk",
            parameter="pressure",
            result=98.7,
            date="2026-03-27",
        )
    )
    print(f"Loaded experiments: {len(experiments)} (list)")

    researchers = get_unique_researchers(experiments)
    print(f"Unique researchers ({len(researchers)}, set): {sorted(researchers)}")

    by_id = build_index_by_id(experiments)
    by_name = build_index_by_name(experiments)
    print(f"Index by ID, key 7 -> {by_id[7].name}")
    print(f"Index by name, 'gas compression test' -> #{by_name['gas compression test'].experiment_id}")

    show(f"Experiments of {researcher}:", find_by_researcher(experiments, researcher))

    temperature = filter_records(experiments, make_parameter_filter("temperature"))
    average = average_result(temperature)
    bounds = min_max_result(temperature)
    print(f"\nTemperature: average={average:.2f}, (min, max)={bounds}")
    print(f"average_of(*args) for 3 values: {average_of(293.4, 301.8, 348.9):.2f}")

    in_range = make_range_filter(low, high)
    show(
        f"Temperature results in [{low:g}, {high:g}] (closure filter):", filter_records(temperature, in_range)
    )

    print("\nGroups by researcher (defaultdict):")
    for name, items in sorted(group_by_researcher(experiments).items()):
        print(f"  {name:<16} -> IDs {[item.experiment_id for item in items]}")

    print("\nNested grouping researcher -> parameter -> results:")
    for name, params in sorted(group_nested(experiments).items()):
        print(f"  {name:<16} {params}")

    print("\nStatistics by researcher (name, count, avg, min, max):")
    for name, stats in sorted(researcher_statistics(experiments).items()):
        _, count, avg, minimum, maximum = stats
        print(f"  {name:<16} n={count}  avg={avg:8.2f}  min={minimum:8.2f}  max={maximum:8.2f}")

    print(f"\nCounter by parameter: {count_by_parameter(experiments).most_common()}")

    print("\nRanking of temperature results (top 5):")
    for place, item in rank_results(temperature, top=5):
        print(f"  {place}. {item.result:>7.2f}  {item.name} ({item.researcher})")

    latest = pipeline(
        experiments,
        lambda data: filter_records(data, make_parameter_filter("pressure")),
        lambda data: sort_records(data, "date", reverse=True),
        lambda data: data[:3],
    )
    show("Pipeline: pressure -> sort by date desc -> first 3:", latest)

    counter = make_counter()
    calls = 0
    for _ in range(3):
        calls = counter()
    print(f"\nClosure counter (nonlocal state) after 3 calls: {calls}")
    print(f"Operation history (deque, maxlen=5): {list(OPERATION_HISTORY)}")
    print("\nExport summary (**kwargs: indent=None, top=2):")
    print(export_summary(experiments, indent=None, top=2))
