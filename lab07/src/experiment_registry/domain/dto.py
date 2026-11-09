"""TypedDicts for external payloads and reports (plain JSON-like data, not entities)."""

from typing import NotRequired, TypedDict


class ExperimentPayload(TypedDict):
    """A record as it arrives from outside (CSV/JSON/API)."""

    experiment_id: int
    name: str
    researcher: str
    parameter: str
    result: float
    unit: str
    date: str
    notes: NotRequired[str]


class AnalysisReport(TypedDict):
    """Result of applying analysis strategies to one experiment."""

    experiment_id: int
    experiment: str
    researcher: str
    parameter: str
    unit: str
    count: int
    metrics: dict[str, float]
