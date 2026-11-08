"""Import pipeline: read -> validate -> domain conversion -> filter -> export."""

import logging
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from experiment_registry.domain.dto import ExperimentPayload
from experiment_registry.domain.exporters import JsonReportExporter, MemorySink
from experiment_registry.domain.repositories import ExperimentRepository, ResearcherRepository
from experiment_registry.domain.services import ExperimentService, ReportingService
from experiment_registry.domain.strategies import default_strategies
from experiment_registry.exceptions import (
    DataImportError,
    ExperimentValidationError,
    RecordValidationError,
)
from experiment_registry.importer.config import AppConfig
from experiment_registry.importer.exporters import export_errors_csv, export_json
from experiment_registry.importer.readers import RecordReader, reader_for
from experiment_registry.importer.validators import validate_record


@dataclass
class ImportStatistics:
    processed: int = 0
    valid: int = 0
    invalid: int = 0
    filtered_out: int = 0
    exported: int = 0
    errors_by_field: Counter[str] = field(default_factory=Counter)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["errors_by_field"] = dict(self.errors_by_field)
        return data


@contextmanager
def log_stage(logger: logging.Logger, stage: str) -> Iterator[None]:
    """Context manager that logs the start, duration and failure of a stage."""
    logger.info("Stage '%s' started", stage)
    start = time.perf_counter()
    try:
        yield
    except Exception:
        logger.error("Stage '%s' failed after %.3f s", stage, time.perf_counter() - start)
        raise
    logger.info("Stage '%s' finished in %.3f s", stage, time.perf_counter() - start)


class ImportService:
    def __init__(self, config: AppConfig, logger: logging.Logger,
                 reader: RecordReader | None = None) -> None:
        self.config = config
        self.logger = logger
        self.reader = reader or reader_for(config.input_path)
        self.stats = ImportStatistics()
        self.rejected: list[dict[str, str]] = []
        # all valid records (domain validation) and the exported subset (summaries)
        self.experiments = ExperimentService(ExperimentRepository(), ResearcherRepository())
        self.exported = ExperimentService(ExperimentRepository(), ResearcherRepository())

    # ------------------------------------------------------------- streaming
    def _reject(self, error: RecordValidationError) -> None:
        self.stats.invalid += 1
        self.stats.errors_by_field[error.field] += 1
        self.rejected.append({"line": str(error.line), "field": error.field,
                              "value": str(error.value), "error": str(error)})
        if not self.config.processing.skip_invalid:
            self.logger.error("Strict mode: %s", error)
            raise DataImportError(f"Import aborted at line {error.line} (strict mode)") from error
        self.logger.warning("Skipped invalid record: %s", error)

    def iter_valid(self) -> Iterator[tuple[int, ExperimentPayload]]:
        """Lazily yield (line, payload) for valid records, applying the strict/tolerant policy."""
        rules = self.config.validation
        for line, row in self.reader.read(self.config.input_path):
            self.stats.processed += 1
            try:
                payload = validate_record(row, line, rules)
            except RecordValidationError as error:
                self._reject(error)
                continue
            yield line, payload

    def _passes_filters(self, payload: ExperimentPayload) -> bool:
        processing = self.config.processing
        if processing.researcher and payload["researcher"].lower() != processing.researcher.lower():
            return False
        if processing.result_range is not None:
            low, high = processing.result_range
            return low <= payload["result"] <= high
        return True

    # --------------------------------------------------------------- run
    def run(self) -> ImportStatistics:
        cfg = self.config
        self.logger.info("Import %s -> %s (skip_invalid=%s)", cfg.input_path, cfg.output_path,
                         cfg.processing.skip_invalid)
        with log_stage(self.logger, "import"):
            results: list[ExperimentPayload] = []
            for line, payload in self.iter_valid():
                try:
                    self.experiments.import_payload(payload)  # domain conversion + checks
                except ExperimentValidationError as error:
                    wrapped = RecordValidationError(str(error), line=line, field="experiment_id",
                                                    value=payload["experiment_id"])
                    wrapped.__cause__ = error
                    self._reject(wrapped)
                    continue
                self.stats.valid += 1
                if self._passes_filters(payload):
                    self.exported.import_payload(payload)
                    results.append(payload)
                else:
                    self.stats.filtered_out += 1

        with log_stage(self.logger, "export"):
            document = self.build_document(results)
            export_json(cfg.output_path, document, cfg.indent, cfg.create_dirs)
            self.stats.exported = len(results)
            if cfg.errors_path is not None and self.rejected:
                export_errors_csv(cfg.errors_path, self.rejected, cfg.create_dirs)

        self.logger.info("Statistics: %s", self.stats.as_dict())
        return self.stats

    def build_document(self, results: list[ExperimentPayload]) -> dict[str, Any]:
        reporting = ReportingService(default_strategies(), JsonReportExporter(), MemorySink())
        summaries = [reporting.build_report(experiment) for experiment in self.exported.find_all()]
        return {
            "schema_version": 1,
            "generated_at": datetime.now().replace(microsecond=0),
            "source": self.config.input_path.name,
            "statistics": self.stats.as_dict() | {"exported": len(results)},
            "experiments": summaries,
            "results": results,
        }
