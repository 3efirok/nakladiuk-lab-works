"""Experiments of lab 5. Run from the project root: python benchmarks/import_experiments.py [1-5]

Temporary files are created in data/generated/ (ignored by Git).
"""

import csv
import logging
import sys
import time
import traceback
import tracemalloc
from collections.abc import Callable, Iterator
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import Any

import yaml

from experiment_registry.exceptions import ConfigurationError, DataImportError, ExperimentError
from experiment_registry.importer.config import load_config
from experiment_registry.importer.exporters import export_json
from experiment_registry.importer.services import ImportService
from experiment_registry.importer.validators import validate_record
from experiment_registry.streaming.datagen import generate_test_file

WORK = Path("data/generated")
BASE_CONFIG = Path("config.yaml")


def quiet_logger() -> logging.Logger:
    logger = logging.getLogger("experiments")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    return logger


# ------------------------------------------------------------ experiment 1
def make_strict_tolerant_input(path: Path, valid: int = 1000, invalid: int = 10) -> Path:
    generate_test_file(path, valid, invalid_ratio=0.0)
    rows = list(csv.reader(path.open(encoding="utf-8")))
    broken = [
        ("result", "error"),
        ("researcher", ""),
        ("date", "2026-02-30"),
        ("parameter", "colour"),
        ("experiment_id", "-4"),
        ("result", "1e9"),
        ("name", ""),
        ("date", "tomorrow"),
        ("result", "nan"),
        ("parameter", "speed"),
    ]
    header = rows[0]
    for index, (field, value) in enumerate(broken[:invalid]):
        row = list(rows[1 + (index + 1) * valid // (invalid + 1)])
        row[header.index(field)] = value
        rows.insert(2 + (index + 1) * valid // (invalid + 1) + index, row)
    with path.open("w", encoding="utf-8", newline="") as file:
        csv.writer(file).writerows(rows)
    return path


def experiment_strict_vs_tolerant() -> None:
    path = make_strict_tolerant_input(WORK / "strict_tolerant.csv")
    base = load_config(BASE_CONFIG)
    print(f"Input: {path} (1000 valid + 10 invalid records)")
    print(f"{'Mode':<9} | {'processed':>9} | {'valid':>5} | {'invalid':>7} | {'exported':>8} | finished")
    for mode, skip in (("strict", False), ("tolerant", True)):
        config = replace(
            base,
            input_path=path,
            output_path=WORK / f"out_{mode}.json",
            errors_path=None,
            processing=replace(base.processing, skip_invalid=skip),
        )
        service = ImportService(config, quiet_logger())
        try:
            service.run()
            finished = "normally (exit code 0)"
        except DataImportError as error:
            finished = f"aborted (exit code 1): {error}"
        s = service.stats
        print(f"{mode:<9} | {s.processed:>9} | {s.valid:>5} | {s.invalid:>7} | {s.exported:>8} | {finished}")


# ------------------------------------------------------------ experiment 2
def eager_import(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def streaming_import(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        yield from csv.DictReader(file)


def consume(rows: Any) -> int:
    count = 0
    for _ in rows:
        count += 1
    return count


def count_rows(reader: Callable[[Path], Any], path: Path) -> int:
    return consume(reader(path))


def measure(func: Callable[[], int]) -> tuple[float, float, int]:
    start = time.perf_counter()
    count = func()
    elapsed = time.perf_counter() - start
    tracemalloc.start()
    func()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024, count


def experiment_streaming_vs_eager() -> None:
    print(
        f"{'Records':>8} | {'Eager time, s':>13} | {'Streaming time, s':>17} | "
        f"{'Eager peak, MB':>14} | {'Streaming peak, MB':>18}"
    )
    for size in (10_000, 100_000, 500_000):
        path = WORK / f"experiments_{size}.csv"
        if not path.exists():
            generate_test_file(path, size)
        e_time, e_peak, e_count = measure(partial(count_rows, eager_import, path))
        s_time, s_peak, s_count = measure(partial(count_rows, streaming_import, path))
        assert e_count == s_count == size
        print(f"{size:>8,} | {e_time:>13.3f} | {s_time:>17.3f} | {e_peak:>14.2f} | {s_peak:>18.3f}")


# ------------------------------------------------------------ experiment 3
def experiment_exception_chaining() -> None:
    rules = load_config(BASE_CONFIG).validation
    row = {
        "experiment_id": "1",
        "name": "Thermal conductivity of Al alloy",
        "researcher": "Olena Kovalenko",
        "parameter": "temperature",
        "result": "wrong",
        "date": "2026-02-03",
    }
    print("Record: 1,Thermal conductivity of Al alloy,Olena Kovalenko,temperature,wrong,2026-02-03")
    try:
        validate_record(row, line=2, rules=rules)
    except ExperimentError as error:
        print("".join(traceback.format_exception(error)).replace(str(Path.cwd()) + "/", ""))
        print(f"error.__cause__ -> {type(error.__cause__).__name__}: {error.__cause__}")
        print(f"error.field={error.field!r}, error.line={error.line}")  # type: ignore[attr-defined]


# ------------------------------------------------------------ experiment 4
def experiment_atomic_output() -> None:
    logger = logging.getLogger("experiment_registry.importer")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stdout)
    target = WORK / "atomic" / "experiments.json"
    export_json(target, {"results": [1, 2, 3]}, create_dirs=True)
    before = target.read_text(encoding="utf-8")
    print(f"Valid output written: {target} -> {before.strip()!r}")
    broken = {"results": [4, 5, 6], "bad_value": object()}  # not JSON-serializable
    try:
        export_json(target, broken)
    except ExperimentError as error:
        logger.error("Export failed: %s (cause: %r)", error, error.__cause__)
    after = target.read_text(encoding="utf-8")
    leftovers = sorted(p.name for p in target.parent.iterdir() if p.suffix == ".tmp")
    print(f"Previous output intact: {after == before}")
    print(f"Temporary files left: {leftovers or 'none'}")


# ------------------------------------------------------------ experiment 5
def experiment_configuration_errors() -> None:
    base = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    cases: list[tuple[str, Any]] = [
        ("missing config.yaml", None),
        ("invalid YAML", "version: 1\ninput: [path: data\n"),
        ("no key input", {k: v for k, v in base.items() if k != "input"}),
        ("min_result > max_result", base | {"validation": base["validation"] | {"min_result": 15000}}),
        ("input file missing", base | {"input": {"path": "data/missing.csv"}}),
        ("output dir missing", base | {"output": {"path": "missing_dir/out.json", "create_dirs": False}}),
    ]
    for title, content in cases:
        path = Path(f"case_{title.split()[0]}.yaml")
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        elif content is not None:
            path.write_text(yaml.safe_dump(content), encoding="utf-8")
        try:
            load_config(path if content is not None else Path("missing/config.yaml"))
            outcome = "loaded (unexpected)"
        except ConfigurationError as error:
            cause = f" <- {type(error.__cause__).__name__}" if error.__cause__ else ""
            outcome = f"ConfigurationError{cause}: {str(error).splitlines()[0][:80]}"
        finally:
            path.unlink(missing_ok=True)
        print(f"{title:<24} | {outcome}")


EXPERIMENTS = {
    "1": experiment_strict_vs_tolerant,
    "2": experiment_streaming_vs_eager,
    "3": experiment_exception_chaining,
    "4": experiment_atomic_output,
    "5": experiment_configuration_errors,
}

if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    for key in sys.argv[1:] or list(EXPERIMENTS):
        print(f"=== Experiment {key}: {EXPERIMENTS[key].__name__.removeprefix('experiment_')}")
        EXPERIMENTS[key]()
