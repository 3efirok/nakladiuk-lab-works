"""Asynchronous measurement sources and the experiment collection pipeline."""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from experiment_registry.domain.services import ExperimentService
from experiment_registry.exceptions import ExperimentError


class AsyncMeasurementSource(Protocol):
    """External device or service that returns measured values for an experiment."""

    async def fetch(self, experiment_id: int) -> list[float]: ...


class InMemoryMeasurementSource:
    """Simple source used in demos; `delay` imitates network or device latency."""

    def __init__(self, data: dict[int, list[float]], delay: float = 0.0) -> None:
        self._data = data
        self._delay = delay

    async def fetch(self, experiment_id: int) -> list[float]:
        await asyncio.sleep(self._delay)
        try:
            return list(self._data[experiment_id])
        except KeyError:
            raise LookupError(f"no measurements for experiment #{experiment_id}") from None


@dataclass
class CollectionReport:
    collected: int = 0
    failed: dict[int, str] = field(default_factory=dict)


class ExperimentPipeline:
    """Fetches measurements concurrently (bounded by a semaphore) and records them."""

    def __init__(
        self,
        source: AsyncMeasurementSource,
        service: ExperimentService,
        max_concurrency: int = 4,
        clock: Callable[[], date] = date.today,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self._source = source
        self._service = service
        self._max_concurrency = max_concurrency
        self._clock = clock

    async def collect(self, experiment_ids: Sequence[int]) -> CollectionReport:
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def fetch_one(experiment_id: int) -> list[float]:
            async with semaphore:
                return await self._source.fetch(experiment_id)

        outcomes = await asyncio.gather(*(fetch_one(i) for i in experiment_ids), return_exceptions=True)
        report = CollectionReport()
        for experiment_id, outcome in zip(experiment_ids, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                report.failed[experiment_id] = f"{type(outcome).__name__}: {outcome}"
                continue
            try:
                for value in outcome:
                    self._service.add_result(experiment_id, value, self._clock())
                    report.collected += 1
            except ExperimentError as error:
                report.failed[experiment_id] = f"{type(error).__name__}: {error}"
        return report
