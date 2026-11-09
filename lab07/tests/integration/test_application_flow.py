"""Integration: the console application end to end (sub-commands and exit codes)."""

import logging
from pathlib import Path

import pytest

from experiment_registry.commands.demo import create_demo_experiments, run_menu
from experiment_registry.main import main

pytestmark = pytest.mark.integration
SAMPLE = Path(__file__).resolve().parents[2] / "data" / "experiments_sample.csv"


def test_import_command_returns_zero_and_prints_statistics(
    config_file: Path, capsys: pytest.CaptureFixture[str], importer_logger: logging.Logger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EXPERIMENTS_SKIP_INVALID", raising=False)

    code = main(["import", "--config", str(config_file)])

    assert code == 0
    assert "Processed: 4 | valid: 3 | invalid: 1" in capsys.readouterr().out


def test_import_command_in_strict_mode_returns_one(
    config_file: Path, capsys: pytest.CaptureFixture[str], importer_logger: logging.Logger,
) -> None:
    assert main(["import", "--config", str(config_file), "--strict"]) == 1
    assert "strict mode" in capsys.readouterr().err


def test_missing_configuration_returns_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["import", "--config", str(tmp_path / "missing.yaml")]) == 2
    assert "configuration error" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], "Average temperature result: 267.38"),
        (["analyze"], "Unique researchers (5, set)"),
        (["iterators"], "flatten (yield from)"),
        (["stream", str(SAMPLE), "--range", "250", "350"], "Read: 16  valid: 12  invalid: 4"),
        (["domain"], "Composition processor"),
    ],
    ids=["demo", "analyze", "iterators", "stream", "domain"],
)
def test_sub_commands_run_end_to_end(argv: list[str], expected: str,
                                     capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 0
    assert expected in capsys.readouterr().out


def test_interactive_menu_with_scripted_input(monkeypatch: pytest.MonkeyPatch,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    answers = iter(["4", "temperature", "5", "100", "50", "2", "Probe", "Andrii Bondar", "density",
                    "abc", "12.5", "2026-03-15", "3", "Andrii Bondar", "7", "0"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    experiments = create_demo_experiments()

    run_menu(experiments)

    out = capsys.readouterr().out
    assert "count=4 average=255.32" in out
    assert "Invalid range: 100.0 > 50.0" in out
    assert "Please enter a number." in out
    assert len(experiments) == 9 and experiments[-1].parameter == "density"
    assert "Unknown command." in out and "Goodbye." in out
