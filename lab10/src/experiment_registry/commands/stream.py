"""Lab 3 scenarios: iterator protocol demo and the streaming pipeline."""

from itertools import islice
from pathlib import Path

from experiment_registry.data import load_experiments
from experiment_registry.streaming.analytics import (
    aggregate,
    count_consecutive_by_researcher,
    pairwise_differences,
    running_average,
)
from experiment_registry.streaming.datagen import generate_test_file
from experiment_registry.streaming.filters import StreamStats
from experiment_registry.streaming.iterators import (
    ExperimentRecordIterator,
    ResultSeries,
    experiment_ids,
    flatten,
)
from experiment_registry.streaming.pipeline import batched, build_pipeline, find_first, take


def run_iterators_demo() -> None:
    experiments = load_experiments()
    results = [item.result for item in experiments[:4]]

    iterator = iter(results)
    print(f"iter(list) -> {type(iterator).__name__}; next() -> {next(iterator)}, {next(iterator)}")

    custom = ExperimentRecordIterator(experiments, 250, 350)
    print(f"ExperimentRecordIterator [250, 350]: {[item.experiment_id for item in custom]}")
    print(f"  second pass over the same iterator: {list(custom)}")

    series = ResultSeries(results)
    print(f"ResultSeries is reusable: sum={sum(series):.2f}, max={max(series):.2f}, len={len(series)}")

    nested = [[293.4, 301.8], [77.2, [92.1, 412.5]], 298.0]
    print(f"flatten (yield from): {list(flatten(nested))}")

    print(f"infinite generator + islice: {list(islice(experiment_ids(), 3))}")

    squares = (value * 2 for value in results)
    print(f"generator expression, 1st pass: {list(squares)}; 2nd pass: {list(squares)}")
    print(f"running average (accumulate): {[round(v, 2) for v in running_average(results)]}")


def run_stream(
    path: Path,
    researcher: str | None,
    parameter: str | None,
    low: float | None,
    high: float | None,
    first: int,
    batch: int,
) -> None:
    stats = StreamStats()
    summary = aggregate(build_pipeline(path, researcher, parameter, low, high, stats))
    print(f"Input: {path}")
    print(
        f"Read: {stats.read}  valid: {stats.valid}  invalid: {stats.invalid}  reasons: {dict(stats.reasons)}"
    )
    print(f"Filter: researcher={researcher}, parameter={parameter}, range=[{low}, {high}]")
    if summary.minimum is None or summary.maximum is None or summary.average is None:
        print("No experiments after filtering.")
        return
    print(f"Matched: {summary.count}  streaming average: {summary.average:.3f}")
    print(
        f"Minimum: {summary.minimum.result:.3f} (#{summary.minimum.experiment_id})  "
        f"maximum: {summary.maximum.result:.3f} (#{summary.maximum.experiment_id})"
    )

    print(f"\nFirst {first} records (islice):")
    for item in take(build_pipeline(path, researcher, parameter, low, high), first):
        print(
            f"  #{item.experiment_id:<7} {item.researcher:<16} {item.parameter:<12} "
            f"{item.result:>10.3f}  {item.date}"
        )

    print("\nPairwise differences of consecutive results:")
    head = take(build_pipeline(path, researcher, parameter, low, high), first)
    for previous_id, current_id, delta in pairwise_differences(head):
        print(f"  #{previous_id} -> #{current_id}: {delta:+.3f}")

    print("\nRuns of the same researcher (groupby) in the first 12 valid rows:")
    print(" ", list(count_consecutive_by_researcher(take(build_pipeline(path), 12))))

    print(f"\nBatch processing (batch size {batch}):")
    batches = 0
    for number, chunk in enumerate(batched(build_pipeline(path, researcher, parameter, low, high), batch), 1):
        batches += 1
        if number <= 3:
            average = sum(item.result for item in chunk) / len(chunk)
            print(f"  batch {number}: {len(chunk)} records, average {average:.3f}")
    print(f"  total batches: {batches}")

    target = high if high is not None else 0.0
    found = find_first(build_pipeline(path, researcher, parameter), lambda item: item.result >= target * 0.99)
    if found:
        print(
            f"\nEarly termination: first result >= {target * 0.99:.2f} is #{found.experiment_id} "
            f"({found.result:.3f})"
        )


def run_generate(path: Path, count: int, invalid_ratio: float) -> None:
    generate_test_file(path, count, invalid_ratio)
    print(f"Generated {count} records -> {path} ({path.stat().st_size / 1e6:.1f} MB)")
