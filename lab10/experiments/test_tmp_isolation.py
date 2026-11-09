"""Experiment 6: every run gets its own empty temporary directory."""

from pathlib import Path

from experiment_registry.importer.exporters import export_json


def test_export_into_isolated_directory(tmp_path: Path) -> None:
    assert list(tmp_path.iterdir()) == []
    target = export_json(tmp_path / "experiments.json", {"results": [293.4]})
    print(f"\n  tmp_path = {tmp_path}")
    assert target.exists()
