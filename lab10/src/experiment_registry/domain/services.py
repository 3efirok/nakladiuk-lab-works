"""Application/service layer: use cases built on top of the domain model."""

from collections.abc import Sequence
from datetime import date

from experiment_registry.domain.dto import AnalysisReport, ExperimentPayload
from experiment_registry.domain.models import Experiment, ExperimentResult, Researcher
from experiment_registry.domain.protocols import ReportExporter, ReportSink
from experiment_registry.domain.repositories import ExperimentRepository, ResearcherRepository
from experiment_registry.domain.strategies import AnalysisStrategy
from experiment_registry.domain.value_objects import Measurement, ResultRange


class ExperimentService:
    """Use cases for experiments; repositories are injected (dependency injection)."""

    def __init__(self, experiments: ExperimentRepository, researchers: ResearcherRepository) -> None:
        self._experiments = experiments
        self._researchers = researchers
        self._next_result_id = 1

    def register_researcher(self, researcher: Researcher) -> Researcher:
        self._researchers.add(researcher)
        return researcher

    def create_experiment(
        self, experiment_id: int, name: str, researcher_id: int, parameter: str, unit: str
    ) -> Experiment:
        researcher = self._researchers.get(researcher_id)
        experiment = Experiment(experiment_id, name, researcher, parameter, unit)
        self._experiments.add(experiment)
        return experiment

    def add_result(
        self, experiment_id: int, value: float, recorded_on: date, notes: str = ""
    ) -> ExperimentResult:
        """Add a value measured in the experiment's own parameter and unit."""
        experiment = self._experiments.get(experiment_id)
        measurement = Measurement(experiment.parameter, value, experiment.unit)
        return self.record_measurement(experiment_id, measurement, recorded_on, notes)

    def record_measurement(
        self, experiment_id: int, measurement: Measurement, recorded_on: date, notes: str = ""
    ) -> ExperimentResult:
        """Add a measurement; Experiment.add_result() rejects an incompatible parameter/unit."""
        experiment = self._experiments.get(experiment_id)
        result = ExperimentResult(self._next_result_id, measurement, recorded_on, notes)
        experiment.add_result(result)
        self._next_result_id += 1
        return result

    def find_all(self) -> list[Experiment]:
        return self._experiments.list_all()

    def find_by_researcher(self, full_name: str) -> list[Experiment]:
        return self._experiments.find_by_researcher(full_name)

    def filter_results(
        self, interval: ResultRange, parameter: str | None = None
    ) -> list[tuple[Experiment, ExperimentResult]]:
        return [
            (experiment, result)
            for experiment in self._experiments
            if parameter is None or experiment.parameter == parameter
            for result in experiment.results_in(interval)
        ]

    def import_payload(
        self, payload: ExperimentPayload, email_domain: str = "lnu.edu.ua"
    ) -> ExperimentResult:
        """Convert an external TypedDict payload into domain objects."""
        researcher = self._researchers.find_by_name(payload["researcher"])
        if researcher is None:
            first, _, last = payload["researcher"].partition(" ")
            researcher = self.register_researcher(
                Researcher(
                    len(self._researchers) + 1,
                    first,
                    last or first,
                    f"{first.lower()}.{(last or first).lower()}@{email_domain}",
                )
            )
        if payload["experiment_id"] not in self._experiments:
            self.create_experiment(
                payload["experiment_id"],
                payload["name"],
                researcher.id,
                payload["parameter"],
                payload["unit"],
            )
        measurement = Measurement(payload["parameter"], payload["result"], payload["unit"])
        return self.record_measurement(
            payload["experiment_id"],
            measurement,
            date.fromisoformat(payload["date"]),
            payload.get("notes", ""),
        )


class ReportingService:
    """Builds analysis reports; strategies, exporter and sink are abstractions (DIP)."""

    def __init__(
        self, strategies: Sequence[AnalysisStrategy], exporter: ReportExporter, sink: ReportSink
    ) -> None:
        self._strategies = list(strategies)
        self._exporter = exporter
        self._sink = sink

    def build_report(self, experiment: Experiment) -> AnalysisReport:
        values = experiment.values()
        return AnalysisReport(
            experiment_id=experiment.id,
            experiment=experiment.name,
            researcher=experiment.researcher.full_name,
            parameter=experiment.parameter,
            unit=experiment.unit,
            count=len(values),
            metrics={s.name: s.analyze(values) for s in self._strategies},
        )

    def publish(self, experiments: Sequence[Experiment]) -> int:
        """Export reports for experiments that have results; return how many were written."""
        written = 0
        for experiment in experiments:
            if len(experiment) == 0:
                continue
            self._sink.write(self._exporter.export(self.build_report(experiment)))
            written += 1
        return written
