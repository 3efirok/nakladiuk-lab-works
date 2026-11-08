"""Structural interfaces (Protocols) used for dependency inversion."""

from typing import Protocol, runtime_checkable

from experiment_registry.domain.dto import AnalysisReport


@runtime_checkable
class Identifiable(Protocol):
    """Anything with an integer `id` can be stored in the generic repository."""

    @property
    def id(self) -> int: ...


class ReportExporter(Protocol):
    """Serializes an analysis report into text (JSON, plain text, ...)."""

    format_name: str

    def export(self, report: AnalysisReport) -> str: ...


class ReportSink(Protocol):
    """Destination of exported reports (console, file, network)."""

    def write(self, text: str) -> None: ...
