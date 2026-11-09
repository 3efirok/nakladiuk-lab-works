import asyncio
from datetime import date
from unittest.mock import AsyncMock

import pytest

from experiment_registry.domain.services import ExperimentService
from experiment_registry.domain.sources import ExperimentPipeline, InMemoryMeasurementSource

FIXED_DAY = date(2026, 3, 1)


@pytest.mark.asyncio
async def test_pipeline_records_values_from_async_source(experiment_service: ExperimentService) -> None:
    source = AsyncMock()
    source.fetch.return_value = [293.4, 297.1]
    pipeline = ExperimentPipeline(source, experiment_service, clock=lambda: FIXED_DAY)

    report = await pipeline.collect([1])

    source.fetch.assert_awaited_once_with(1)
    assert report.collected == 2 and report.failed == {}
    assert experiment_service.find_by_researcher("Olena Kovalenko")[0].values() == [293.4, 297.1]


@pytest.mark.asyncio
async def test_source_failure_is_reported_and_other_experiments_continue(
    experiment_service: ExperimentService,
) -> None:
    async def fetch(experiment_id: int) -> list[float]:
        if experiment_id == 2:
            raise TimeoutError("device timeout")
        return [300.0]

    source = AsyncMock()
    source.fetch.side_effect = fetch

    report = await ExperimentPipeline(source, experiment_service, clock=lambda: FIXED_DAY).collect([1, 2])

    assert report.collected == 1
    assert report.failed == {2: "TimeoutError: device timeout"}
    assert source.fetch.await_count == 2


@pytest.mark.asyncio
async def test_invalid_value_from_source_is_reported(experiment_service: ExperimentService) -> None:
    source = AsyncMock()
    source.fetch.return_value = [float("nan")]

    report = await ExperimentPipeline(source, experiment_service, clock=lambda: FIXED_DAY).collect([1])

    assert report.collected == 0
    assert "ExperimentValidationError" in report.failed[1]


@pytest.mark.asyncio
async def test_semaphore_limits_concurrent_requests(experiment_service: ExperimentService) -> None:
    active = peak = 0

    async def fetch(experiment_id: int) -> list[float]:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return []

    source = AsyncMock()
    source.fetch.side_effect = fetch

    await ExperimentPipeline(source, experiment_service, max_concurrency=2).collect([1, 2, 1, 2, 1])

    assert peak == 2


@pytest.mark.asyncio
async def test_in_memory_source_raises_lookup_error_for_unknown_experiment() -> None:
    with pytest.raises(LookupError):
        await InMemoryMeasurementSource({1: [1.0]}).fetch(5)


def test_pipeline_requires_positive_concurrency(experiment_service: ExperimentService) -> None:
    with pytest.raises(ValueError):
        ExperimentPipeline(AsyncMock(), experiment_service, max_concurrency=0)
