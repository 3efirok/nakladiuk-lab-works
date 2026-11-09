"""Integration: async source -> service -> reporting strategies -> atomic JSON file."""

import json
from datetime import date
from pathlib import Path

import pytest

from experiment_registry.domain.exporters import JsonReportExporter, MemorySink
from experiment_registry.domain.services import ExperimentService, ReportingService
from experiment_registry.domain.sources import ExperimentPipeline, InMemoryMeasurementSource
from experiment_registry.domain.strategies import default_strategies
from experiment_registry.importer.exporters import export_json

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_measurements_flow_from_source_to_json_report(
    experiment_service: ExperimentService, tmp_path: Path,
) -> None:
    source = InMemoryMeasurementSource({1: [293.4, 297.1, 301.8], 2: [101.3, 99.8]}, delay=0.001)
    pipeline = ExperimentPipeline(source, experiment_service, clock=lambda: date(2026, 3, 1))

    collected = await pipeline.collect([1, 2, 3])
    sink = MemorySink()
    written = ReportingService(default_strategies(), JsonReportExporter(indent=None), sink).publish(
        experiment_service.find_all())
    target = export_json(tmp_path / "reports.json", [json.loads(item) for item in sink.items])

    reports = json.loads(target.read_text(encoding="utf-8"))
    assert collected.collected == 5 and list(collected.failed) == [3]
    assert written == 2
    assert reports[0]["metrics"]["average"] == pytest.approx(297.433333)
    assert reports[1]["metrics"]["maximum"] == 101.3
