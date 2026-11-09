"""Integration: configuration -> CSV import -> domain -> JSON export -> logs."""

import json
import logging
from pathlib import Path

import pytest

from experiment_registry.exceptions import DataImportError
from experiment_registry.importer.config import load_config
from experiment_registry.importer.logging_config import setup_logging
from experiment_registry.importer.services import ImportService

pytestmark = pytest.mark.integration


def test_tolerant_import_exports_valid_results_and_rejected_rows(
    config_file: Path,
    importer_logger: logging.Logger,
) -> None:
    config = load_config(config_file, env={})
    service = ImportService(config, setup_logging(config.logging, console=False))

    stats = service.run()

    document = json.loads(config.output_path.read_text(encoding="utf-8"))
    assert (stats.processed, stats.valid, stats.invalid, stats.exported) == (4, 3, 1, 3)
    assert [r["result"] for r in document["results"]] == [293.4, 301.8, 101.3]
    assert document["experiments"][0]["metrics"]["average"] == pytest.approx(297.6)
    assert config.errors_path is not None
    assert "result,wrong" in config.errors_path.read_text(encoding="utf-8")
    assert "Skipped invalid record: line 5" in config.logging.file.read_text(encoding="utf-8")


def test_strict_import_aborts_and_writes_no_output(
    config_file: Path,
    importer_logger: logging.Logger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXPERIMENTS_SKIP_INVALID", "false")
    config = load_config(config_file)
    service = ImportService(config, setup_logging(config.logging, console=False))

    with pytest.raises(DataImportError, match="line 5") as exc_info:
        service.run()

    assert exc_info.value.__cause__ is not None
    assert not config.output_path.exists()
    assert service.stats.valid == 3


def test_filters_from_configuration_change_exported_results(
    tmp_path: Path,
    config_data: dict,
    importer_logger: logging.Logger,
) -> None:
    import yaml

    config_data["processing"] = {
        "skip_invalid": True,
        "researcher": "Olena Kovalenko",
        "result_range": [300, 400],
    }
    path = tmp_path / "filtered.yaml"
    path.write_text(yaml.safe_dump(config_data), encoding="utf-8")
    config = load_config(path, env={})

    stats = ImportService(config, setup_logging(config.logging, console=False)).run()

    assert (stats.valid, stats.filtered_out, stats.exported) == (3, 2, 1)
