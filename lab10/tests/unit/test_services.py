from datetime import date
from unittest.mock import Mock

import pytest

from experiment_registry.domain.dto import ExperimentPayload
from experiment_registry.domain.exporters import JsonReportExporter, MemorySink
from experiment_registry.domain.models import Experiment, Researcher
from experiment_registry.domain.protocols import ReportExporter, ReportSink
from experiment_registry.domain.repositories import ExperimentRepository, ResearcherRepository
from experiment_registry.domain.services import ExperimentService, ReportingService
from experiment_registry.domain.strategies import MaximumStrategy, MeanStrategy, MinimumStrategy
from experiment_registry.domain.value_objects import ResultRange
from experiment_registry.exceptions import (
    DuplicateExperimentError,
    ExperimentNotFoundError,
    ExportError,
)


def test_add_result_uses_experiment_parameter_and_unit(experiment_service: ExperimentService) -> None:
    result = experiment_service.add_result(1, 293.4, date(2026, 2, 3), notes="first run")

    assert result.measurement.parameter == "temperature"
    assert result.measurement.unit == "K"
    assert result.notes == "first run"


def test_add_result_to_unknown_experiment_raises(experiment_service: ExperimentService) -> None:
    with pytest.raises(ExperimentNotFoundError):
        experiment_service.add_result(99, 1.0, date(2026, 2, 3))


def test_result_ids_are_unique_across_experiments(experiment_service: ExperimentService) -> None:
    first = experiment_service.add_result(1, 293.4, date(2026, 2, 3))
    second = experiment_service.add_result(2, 101.3, date(2026, 2, 3))

    assert second.result_id == first.result_id + 1


@pytest.mark.parametrize("name", ["Olena Kovalenko", "olena kovalenko", "  OLENA KOVALENKO "])
def test_find_by_researcher_is_case_insensitive(experiment_service: ExperimentService, name: str) -> None:
    assert [item.id for item in experiment_service.find_by_researcher(name)] == [1]


def test_find_by_unknown_researcher_returns_empty_list(experiment_service: ExperimentService) -> None:
    assert experiment_service.find_by_researcher("Nobody") == []


def test_filter_results_by_range_and_parameter(experiment_service: ExperimentService) -> None:
    for value in (250.0, 300.0, 350.0):
        experiment_service.add_result(1, value, date(2026, 2, 3))
    experiment_service.add_result(2, 300.0, date(2026, 2, 3))

    found = experiment_service.filter_results(ResultRange(260, 340), parameter="temperature")

    assert [(exp.id, res.value) for exp, res in found] == [(1, 300.0)]


def test_creating_duplicate_experiment_raises(experiment_service: ExperimentService) -> None:
    with pytest.raises(DuplicateExperimentError):
        experiment_service.create_experiment(1, "Duplicate", 1, "temperature", "K")


def test_import_payload_creates_researcher_and_experiment() -> None:
    service = ExperimentService(ExperimentRepository(), ResearcherRepository())
    payload: ExperimentPayload = {
        "experiment_id": 5,
        "name": "Battery cycle",
        "researcher": "Iryna Melnyk",
        "parameter": "voltage",
        "result": 3.71,
        "unit": "V",
        "date": "2026-02-12",
    }

    service.import_payload(payload)

    assert [exp.researcher.full_name for exp in service.find_all()] == ["Iryna Melnyk"]


# --------------------------------------------------------------- reporting with mocks
def test_report_contains_metrics_from_all_strategies(experiment: Experiment) -> None:
    reporting = ReportingService(
        [MeanStrategy(), MinimumStrategy(), MaximumStrategy()], JsonReportExporter(), MemorySink()
    )

    report = reporting.build_report(experiment)

    assert report["count"] == 3
    assert report["metrics"] == pytest.approx({"average": 297.433333, "minimum": 293.4, "maximum": 301.8})


def test_publish_sends_exported_text_to_sink(experiment: Experiment) -> None:
    exporter = Mock(spec=ReportExporter)
    exporter.export.return_value = "REPORT #1"
    sink = Mock(spec=ReportSink)

    written = ReportingService([MeanStrategy()], exporter, sink).publish([experiment])

    assert written == 1
    exporter.export.assert_called_once()
    sink.write.assert_called_once_with("REPORT #1")


def test_publish_skips_experiments_without_results(researcher: Researcher) -> None:
    exporter, sink = Mock(spec=ReportExporter), Mock(spec=ReportSink)
    empty = Experiment(3, "Not started yet", researcher, "temperature", "K")

    assert ReportingService([MeanStrategy()], exporter, sink).publish([empty]) == 0
    exporter.export.assert_not_called()


def test_exporter_failure_does_not_write_to_sink(experiment: Experiment) -> None:
    """Failure path: the error propagates and no partial report reaches the sink."""
    exporter = Mock(spec=ReportExporter)
    exporter.export.side_effect = ExportError("disk is full")
    sink = Mock(spec=ReportSink)

    with pytest.raises(ExportError, match="disk is full"):
        ReportingService([MeanStrategy()], exporter, sink).publish([experiment])
    sink.write.assert_not_called()


def test_strategy_is_called_with_experiment_values(experiment: Experiment) -> None:
    strategy = Mock()
    strategy.name = "custom"
    strategy.analyze.return_value = 1.5

    report = ReportingService([strategy], JsonReportExporter(), MemorySink()).build_report(experiment)

    strategy.analyze.assert_called_once_with([293.4, 297.1, 301.8])
    assert report["metrics"] == {"custom": 1.5}
