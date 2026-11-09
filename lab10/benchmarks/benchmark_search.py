"""Benchmark: search by ID in a list (O(n)) vs a dict index (O(1)).

Run from the project root:  python benchmarks/benchmark_search.py
"""

import random
import timeit
from collections.abc import Container
from functools import partial

from experiment_registry.data import generate_experiments
from experiment_registry.models import Experiment
from experiment_registry.processors import build_index_by_id, find_by_id_linear

SIZES = (1_000, 10_000, 100_000)
LOOKUPS = 200
REPEATS = 5


def best_per_lookup(stmt, number: int) -> float:
    """Best of REPEATS runs, converted to microseconds per lookup."""
    return min(timeit.repeat(stmt, number=1, repeat=REPEATS)) / number * 1e6


def search_linear(experiments: list[Experiment], targets: list[int]) -> list[Experiment | None]:
    return [find_by_id_linear(experiments, t) for t in targets]


def search_index(index: dict[int, Experiment], targets: list[int]) -> list[Experiment | None]:
    return [index.get(t) for t in targets]


def membership(container: Container[int], targets: list[int]) -> list[bool]:
    return [t in container for t in targets]


def run() -> list[tuple[int, float, float, float, float, float]]:
    rows = []
    for size in SIZES:
        experiments = generate_experiments(size)
        rng = random.Random(size)
        targets = [rng.randint(1, size) for _ in range(LOOKUPS)]

        build_ms = min(timeit.repeat(partial(build_index_by_id, experiments), number=1, repeat=REPEATS)) * 1e3
        index = build_index_by_id(experiments)
        ids_list = [item.experiment_id for item in experiments]
        ids_set = set(ids_list)

        list_search = best_per_lookup(partial(search_linear, experiments, targets), LOOKUPS)
        dict_search = best_per_lookup(partial(search_index, index, targets), LOOKUPS)
        list_in = best_per_lookup(partial(membership, ids_list, targets), LOOKUPS)
        set_in = best_per_lookup(partial(membership, ids_set, targets), LOOKUPS)

        assert all(find_by_id_linear(experiments, t) is index[t] for t in targets[:20])
        rows.append((size, list_search, dict_search, build_ms, list_in, set_in))
    return rows


def main() -> None:
    print(f"Lookups per run: {LOOKUPS}, best of {REPEATS} runs, time per lookup in microseconds")
    print(
        f"{'Records':>9} | {'list search':>12} | {'dict search':>11} | {'dict build, ms':>14} | "
        f"{'x in list':>10} | {'x in set':>8} | {'speedup':>8}"
    )
    for size, list_s, dict_s, build_ms, list_in, set_in in run():
        print(
            f"{size:>9,} | {list_s:>12.2f} | {dict_s:>11.3f} | {build_ms:>14.2f} | "
            f"{list_in:>10.2f} | {set_in:>8.3f} | {list_s / dict_s:>7.0f}x"
        )


if __name__ == "__main__":
    main()
