"""Asynchronous HTTP client for the experiment API (HTTPX + retry + timeout + Semaphore)."""

import asyncio
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("experiment_registry.api.client")
RETRY_STATUSES = {502, 503, 504}


@dataclass
class FetchResult:
    researcher_id: int
    data: dict[str, Any] | None = None
    error: str | None = None
    attempts: int = 0
    elapsed_ms: float = 0.0


@dataclass
class ExperimentApiClient:
    """Calls GET /experiments/statistics for many researchers concurrently.

    One AsyncClient (connection pool) is shared by all requests inside `async with`.
    """

    base_url: str
    timeout: float = 2.0
    retries: int = 3
    backoff: float = 0.2
    max_concurrency: int = 4
    transport: httpx.AsyncBaseTransport | None = None
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def __aenter__(self) -> "ExperimentApiClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(self.timeout),
                                         transport=self.transport)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def get_json(self, path: str, **params: Any) -> tuple[Any, int]:
        """GET with retry and exponential backoff for network errors, timeouts and 502-504."""
        assert self._client is not None, "use 'async with ExperimentApiClient(...)'"
        for attempt in range(1, self.retries + 1):
            try:
                response = await self._client.get(path, params=params)
                if response.status_code in RETRY_STATUSES:
                    raise httpx.HTTPStatusError(f"server error {response.status_code}",
                                                request=response.request, response=response)
                response.raise_for_status()
                return response.json(), attempt
            except (httpx.TransportError, httpx.HTTPStatusError) as error:
                retryable = not isinstance(error, httpx.HTTPStatusError) or (
                    error.response.status_code in RETRY_STATUSES)
                if not retryable or attempt == self.retries:
                    raise
                delay = self.backoff * 2 ** (attempt - 1)
                logger.warning("attempt %d for %s failed (%s), retry in %.2f s", attempt, path,
                               type(error).__name__, delay)
                await asyncio.sleep(delay)
        raise RuntimeError("unreachable")

    async def fetch_statistics(self, researcher_id: int, semaphore: asyncio.Semaphore) -> FetchResult:
        result = FetchResult(researcher_id)
        start = time.perf_counter()
        async with semaphore:
            try:
                result.data, result.attempts = await self.get_json(
                    "/experiments/statistics", researcher_id=researcher_id)
            except httpx.HTTPStatusError as error:
                result.error = f"HTTP {error.response.status_code}"
                result.attempts = self.retries if error.response.status_code in RETRY_STATUSES else 1
            except httpx.TimeoutException:
                result.error, result.attempts = "timeout", self.retries
            except httpx.TransportError as error:
                result.error, result.attempts = type(error).__name__, self.retries
        result.elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return result

    async def fetch_many(self, researcher_ids: Sequence[int]) -> list[FetchResult]:
        semaphore = asyncio.Semaphore(self.max_concurrency)
        tasks = [asyncio.create_task(self.fetch_statistics(rid, semaphore)) for rid in researcher_ids]
        return list(await asyncio.gather(*tasks))
