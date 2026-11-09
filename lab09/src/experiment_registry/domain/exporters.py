"""Report exporters and sinks; they satisfy the Protocols structurally (no inheritance)."""

import json

from experiment_registry.domain.dto import AnalysisReport


class JsonReportExporter:
    format_name = "json"

    def __init__(self, indent: int | None = 2) -> None:
        self.indent = indent

    def export(self, report: AnalysisReport) -> str:
        return json.dumps(report, indent=self.indent, ensure_ascii=False)


class TextReportExporter:
    format_name = "text"

    def export(self, report: AnalysisReport) -> str:
        metrics = ", ".join(f"{key}={value:g}" for key, value in report["metrics"].items())
        return (f"#{report['experiment_id']} {report['experiment']} ({report['researcher']}), "
                f"{report['parameter']} [{report['unit']}], n={report['count']}: {metrics}")


class ConsoleSink:
    def write(self, text: str) -> None:
        print(text)


class MemorySink:
    """Collects exported texts in memory (handy for demos and tests)."""

    def __init__(self) -> None:
        self.items: list[str] = []

    def write(self, text: str) -> None:
        self.items.append(text)
