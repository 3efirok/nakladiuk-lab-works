"""Lab 9 experiments. Run from the project root:

    python benchmarks/benchmark_performance.py [profile|memory|benchmark|operations|workers|cache|io|sync]
"""

import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from experiment_registry.performance.analytics import (
    analyze_dataset,
    generate_dataset,
    numpy_range_filter,
    numpy_researcher_stats,
    numpy_statistics,
    python_range_filter,
    python_researcher_stats,
    python_statistics,
)
from experiment_registry.performance.caching import CachedStatistics
from experiment_registry.performance.parallel import (
    ProgressCounter,
    UnsafeCounter,
    hammer,
    load_sequential,
    load_threaded,
    parallel_statistics,
    write_dataset_files,
)
from experiment_registry.performance.profiling import mean_time, peak_memory_mb, profile_call, time_runs

SIZES = (10_000, 100_000, 1_000_000)
RUNS = 5
WORKERS = 4
RESULTS = Path("benchmarks/results")


def section_profile() -> None:
    dataset = generate_dataset(1_000_000)
    _, report = profile_call(analyze_dataset, dataset, top=10)
    print("cProfile of analyze_dataset() on 1 000 000 results (sorted by tottime):")
    print("\n".join(line for line in report.splitlines() if line.strip())[:3000])


def section_memory() -> None:
    dataset = generate_dataset(1_000_000)
    researchers, values = dataset.as_numpy()
    print("Peak memory (tracemalloc), 1 000 000 results:")
    for title, func, args in (
        ("Python statistics (lists)", python_statistics, (dataset.results,)),
        ("NumPy statistics (array)", numpy_statistics, (values,)),
        ("Python range filter -> list", python_range_filter, (dataset.results, 250.0, 350.0)),
        ("NumPy range filter -> array", numpy_range_filter, (values, 250.0, 350.0)),
        ("Python stats by researcher", python_researcher_stats, (dataset.researchers, dataset.results)),
        ("NumPy stats by researcher", numpy_researcher_stats, (researchers, values)),
    ):
        _, peak = peak_memory_mb(func, *args)
        print(f"  {title:<30} {peak:8.2f} MB")
    _, list_peak = peak_memory_mb(lambda: [float(i) for i in range(1_000_000)])
    _, array_peak = peak_memory_mb(lambda: numpy_range_filter(values, -1e9, 1e9).copy())
    print(f"  {'list of 1M floats':<30} {list_peak:8.2f} MB")
    print(f"  {'NumPy array of 1M floats':<30} {array_peak:8.2f} MB")


def section_benchmark() -> None:
    rows = []
    print(f"Bottleneck: statistics (mean, min, max, std, outliers); {RUNS} runs, workers={WORKERS}")
    print(f"{'Dataset':>9} | {'Method':<10} | {'Workers':>7} | " + " | ".join(f"Run {i}" for i in range(1, RUNS + 1))
          + f" | {'Mean, s':>8} | {'Peak MB':>7} | Speedup | OK")
    with ThreadPoolExecutor(WORKERS) as threads, ProcessPoolExecutor(WORKERS) as processes:
        list(processes.map(abs, range(WORKERS)))  # start workers before measuring
        for size in SIZES:
            dataset = generate_dataset(size)
            _, values = dataset.as_numpy()
            baseline = python_statistics(dataset.results)
            methods = [
                ("Sequential", "1", lambda: python_statistics(dataset.results)),
                ("Threads", str(WORKERS), lambda: parallel_statistics(dataset.results, threads, WORKERS)),
                ("Processes", str(WORKERS), lambda: parallel_statistics(dataset.results, processes, WORKERS)),
                ("NumPy", "-", lambda: numpy_statistics(values)),
            ]
            base_mean = None
            for name, workers, func in methods:
                ok = func().close_to(baseline, rel=1e-9)
                runs = time_runs(func, RUNS)
                mean = mean_time(runs)
                base_mean = base_mean or mean
                _, peak = peak_memory_mb(func)
                speedup = base_mean / mean
                rows.append([size, name, workers, *runs, mean, peak, speedup, ok])
                print(f"{size:>9,} | {name:<10} | {workers:>7} | " + " | ".join(f"{r:.4f}" for r in runs)
                      + f" | {mean:8.4f} | {peak:7.2f} | {speedup:6.2f}x | {ok}")
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "benchmark_results.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["dataset", "method", "workers", *[f"run{i}" for i in range(1, RUNS + 1)],
                         "mean_s", "peak_mb", "speedup", "correct"])
        writer.writerows(rows)


def section_operations() -> None:
    dataset = generate_dataset(1_000_000)
    researchers, values = dataset.as_numpy()
    print("Other profiled operations, 1 000 000 results, mean of 5 runs:")
    print(f"{'Operation':<26} | {'Python, s':>9} | {'NumPy, s':>9} | Speedup | Same result")
    pairs = [
        ("statistics by researcher", lambda: python_researcher_stats(dataset.researchers, dataset.results),
         lambda: numpy_researcher_stats(researchers, values)),
        ("range filter [250, 350]", lambda: python_range_filter(dataset.results, 250.0, 350.0),
         lambda: numpy_range_filter(values, 250.0, 350.0)),
    ]
    for title, py, np_func in pairs:
        py_t = mean_time(time_runs(py, RUNS))
        np_t = mean_time(time_runs(np_func, RUNS))
        a, b = py(), np_func()
        same = (len(a) == len(b)) if not isinstance(a, dict) else all(
            a[k][0] == b[k][0] and abs(a[k][1] - b[k][1]) < 1e-9 for k in a)
        print(f"{title:<26} | {py_t:9.4f} | {np_t:9.5f} | {py_t / np_t:6.1f}x | {same}")


def section_workers() -> None:
    dataset = generate_dataset(1_000_000)
    baseline = mean_time(time_runs(lambda: python_statistics(dataset.results), 3))
    print(f"1 000 000 results, sequential baseline {baseline:.4f} s; mean of 3 runs; os.cpu_count()={os.cpu_count()}")
    print(f"{'Workers':>7} | {'ThreadPool, s':>13} | {'Speedup':>7} | {'ProcessPool, s':>14} | {'Speedup':>7}")
    for workers in (1, 2, 4, 8, 12):
        with ThreadPoolExecutor(workers) as threads, ProcessPoolExecutor(workers) as processes:
            list(processes.map(abs, range(workers)))
            t = mean_time(time_runs(lambda: parallel_statistics(dataset.results, threads, workers), 3))
            p = mean_time(time_runs(lambda: parallel_statistics(dataset.results, processes, workers), 3))
        print(f"{workers:>7} | {t:13.4f} | {baseline / t:6.2f}x | {p:14.4f} | {baseline / p:6.2f}x")


def section_cache() -> None:
    dataset = generate_dataset(1_000_000)
    cached = CachedStatistics(dataset.results)
    first = time_runs(cached.statistics, 1)[0]
    repeated = mean_time(time_runs(cached.statistics, 5))
    print("Caching of statistics for an unchanged dataset (1 000 000 results):")
    print(f"  first call (miss)        {first * 1000:9.3f} ms")
    print(f"  repeated call (hit)      {repeated * 1000:9.4f} ms   speedup {first / repeated:,.0f}x")
    before = cached.statistics().mean
    cached.add(10_000.0)
    after_add = time_runs(cached.statistics, 1)[0]
    print(f"  after add() -> version {cached.version}, recomputed in {after_add * 1000:.3f} ms; "
          f"mean {before:.4f} -> {cached.statistics().mean:.4f}")
    cached.update(0, 300.0)
    print(f"  after update() -> version {cached.version}; hits={cached.hits}, misses={cached.misses}")


def section_io() -> None:
    paths = write_dataset_files(Path("data/generated/series"), files=8, rows=50_000)
    print(f"Loading {len(paths)} files x 50 000 rows; mean of 3 runs")
    print(f"{'Storage':<28} | {'Sequential, s':>13} | {'ThreadPool(4), s':>16} | {'ThreadPool(8), s':>16}")
    for title, latency in (("local disk", 0.0), ("network (+0.2 s per file)", 0.2)):
        seq = mean_time(time_runs(lambda: load_sequential(paths, latency), 3))
        t4 = mean_time(time_runs(lambda: load_threaded(paths, 4, latency), 3))
        t8 = mean_time(time_runs(lambda: load_threaded(paths, 8, latency), 3))
        print(f"{title:<28} | {seq:13.3f} | {t4:10.3f} ({seq / t4:.1f}x) | {t8:10.3f} ({seq / t8:.1f}x)")
    assert load_sequential(paths) == load_threaded(paths, 4)
    print("Results of sequential and threaded loading are identical: True")


def section_sync() -> None:
    print("8 threads x 1000 increments of a shared counter (expected 8000):")
    print(f"  without Lock: {hammer(UnsafeCounter())}")
    print(f"  with Lock:    {hammer(ProgressCounter())}")


SECTIONS = {"profile": section_profile, "memory": section_memory, "benchmark": section_benchmark,
            "operations": section_operations,
            "workers": section_workers, "cache": section_cache, "io": section_io, "sync": section_sync}

if __name__ == "__main__":
    for name in sys.argv[1:] or list(SECTIONS):
        SECTIONS[name]()
        print()
