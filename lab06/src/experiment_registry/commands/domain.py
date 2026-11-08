"""Lab 4 scenario: typed object model, services and dependency injection."""

from datetime import date

from experiment_registry.domain.dto import ExperimentPayload
from experiment_registry.domain.exporters import ConsoleSink, JsonReportExporter, TextReportExporter
from experiment_registry.domain.models import ExperimentSeries, Researcher
from experiment_registry.domain.processing import (
    CsvLineParser,
    CsvResultProcessor,
    RangeValidator,
    ResultProcessor,
    TextFormatter,
)
from experiment_registry.domain.protocols import Identifiable
from experiment_registry.domain.repositories import ExperimentRepository, ResearcherRepository
from experiment_registry.domain.services import ExperimentService, ReportingService
from experiment_registry.domain.strategies import default_strategies
from experiment_registry.domain.value_objects import Measurement, ResultRange
from experiment_registry.exceptions import ExperimentError


def build_service() -> ExperimentService:
    """Composition root: concrete dependencies are created in one place."""
    service = ExperimentService(ExperimentRepository(), ResearcherRepository())
    service.register_researcher(Researcher(1, "Olena", "Kovalenko", "o.kovalenko@lnu.edu.ua"))
    service.register_researcher(Researcher(2, "Taras", "Hnatiuk", "t.hnatiuk@lnu.edu.ua", "Mechanics"))
    service.create_experiment(1, "Thermal conductivity of Al alloy", 1, "temperature", "K")
    service.create_experiment(2, "Gas compression test", 2, "pressure", "kPa")
    service.create_experiment(3, "Heat exchanger efficiency", 1, "temperature", "K")
    for experiment_id, value, day in [
        (1, 293.4, "2026-02-03"), (1, 297.1, "2026-02-04"), (1, 301.8, "2026-02-10"),
        (2, 101.3, "2026-02-05"), (2, 99.8, "2026-02-06"), (2, 250.4, "2026-03-06"),
        (3, 348.9, "2026-03-02"), (3, 352.2, "2026-03-03"),
    ]:
        service.add_result(experiment_id, value, date.fromisoformat(day))
    return service


def run_domain_demo() -> None:
    service = build_service()
    olena = service.find_by_researcher("Olena Kovalenko")
    print(f"Experiments of Olena Kovalenko: {olena}")

    print("\nValidation:")
    for action in (
        lambda: service.add_result(1, float("nan"), date(2026, 3, 1)),
        lambda: service.add_result(1, 290.0, date(2030, 1, 1)),
        lambda: Researcher(3, "Iryna", "Melnyk", "wrong-email"),
        lambda: ResultRange(400, 100),
    ):
        try:
            action()
        except ExperimentError as error:
            print(f"  {type(error).__name__}: {error}")

    m1, m2 = Measurement("temperature", 301.8, "K"), Measurement("temperature", 293.4, "K")
    print(f"\nValue objects: {m1} - {m2} = {m1 - m2}; {m1} > {m2}: {m1 > m2}; "
          f"hashable: {len({m1, Measurement('temperature', 301.8, 'K')})} unique")
    try:
        _ = m1 < Measurement("pressure", 1.0, "kPa")
    except ExperimentError as error:
        print(f"  {type(error).__name__}: {error}")

    interval = ResultRange(290, 310)
    print(f"\nResults in [{interval.low}, {interval.high}] K:")
    for experiment, result in service.filter_results(interval, "temperature"):
        print(f"  #{experiment.id} {experiment.name}: {result.measurement} ({result.recorded_on})")

    print("\nReports (strategies + JSON exporter + console sink):")
    reporting = ReportingService(default_strategies(), JsonReportExporter(indent=None), ConsoleSink())
    reporting.publish(olena[:1])
    print("Same service with another exporter injected (TextReportExporter):")
    ReportingService(default_strategies(), TextReportExporter(), ConsoleSink()).publish(olena)

    series = ExperimentSeries("Thermal project", olena)
    print(f"\nSeries: {series!r}; len={len(series)}; series[0]={series[0].name!r}; "
          f"first experiment in series: {olena[0] in series}")
    print(f"All temperature values: {series.all_values('temperature')}")
    print(f"Experiment is Identifiable (runtime_checkable Protocol): {isinstance(olena[0], Identifiable)}")

    payload: ExperimentPayload = {
        "experiment_id": 4, "name": "Battery discharge cycle", "researcher": "Iryna Melnyk",
        "parameter": "voltage", "result": 3.71, "unit": "V", "date": "2026-02-12",
    }
    result = service.import_payload(payload)
    print(f"\nImported TypedDict payload -> {service.find_by_researcher('Iryna Melnyk')}, "
          f"result {result.measurement}")

    line = "7,Heat exchanger efficiency,Olena Kovalenko,temperature,348.9,2026-03-02"
    inherited = CsvResultProcessor(ResultRange(0, 500))
    composed = ResultProcessor(CsvLineParser(), RangeValidator(ResultRange(0, 500)), TextFormatter())
    print(f"\nInheritance processor: {inherited.process(line)}")
    print(f"Composition processor: {composed.process(line)}")
