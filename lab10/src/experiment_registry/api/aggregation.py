"""Concurrent statistics for several researchers: Task + gather + Semaphore + timeout."""

import asyncio
import time
from collections.abc import Callable, Sequence

from experiment_registry.api.schemas import AggregatedStatistics, ResearcherStatistics, StatisticsRead
from experiment_registry.persistence.repositories import ResultSummary


async def collect_statistics(
    load: Callable[[int], ResultSummary],
    researcher_ids: Sequence[int],
    max_concurrency: int = 3,
    timeout: float = 2.0,
) -> AggregatedStatistics:
    """Run blocking `load(researcher_id)` calls in threads, at most `max_concurrency` at once."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def one(researcher_id: int) -> ResultSummary:
        async with semaphore:
            return await asyncio.wait_for(asyncio.to_thread(load, researcher_id), timeout=timeout)

    start = time.perf_counter()
    tasks = [
        asyncio.create_task(one(researcher_id), name=f"stats-{researcher_id}")
        for researcher_id in researcher_ids
    ]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    items = []
    for researcher_id, outcome in zip(researcher_ids, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            reason = "timeout" if isinstance(outcome, TimeoutError) else str(outcome)
            items.append(ResearcherStatistics(researcher_id=researcher_id, error=reason))
        else:
            items.append(
                ResearcherStatistics(
                    researcher_id=researcher_id,
                    statistics=StatisticsRead(
                        count=outcome.count,
                        average=outcome.average,
                        minimum=outcome.minimum,
                        maximum=outcome.maximum,
                        researcher_id=researcher_id,
                    ),
                )
            )
    return AggregatedStatistics(
        items=items,
        elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
        max_concurrency=max_concurrency,
    )
