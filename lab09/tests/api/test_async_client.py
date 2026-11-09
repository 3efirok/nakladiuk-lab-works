"""Asynchronous tests: httpx.AsyncClient + ASGITransport, retry, timeout, Semaphore, gather."""

import asyncio
import time
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from experiment_registry.api.aggregation import collect_statistics
from experiment_registry.api.external import ExperimentApiClient
from experiment_registry.persistence.repositories import ResultSummary

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_concurrent_requests_to_the_real_app(api_app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=api_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/researchers", json={"full_name": "Olena Kovalenko"})
        bodies = [{"name": f"Run {i}", "researcher_id": 1, "parameter": "temperature", "result": 290 + i,
                   "date": "2026-02-03"} for i in range(5)]
        responses = await asyncio.gather(*(client.post("/experiments", json=b) for b in bodies))
        statistics = (await client.get("/experiments/statistics")).json()

    assert [r.status_code for r in responses] == [201] * 5
    assert statistics["count"] == 5 and statistics["average"] == pytest.approx(292.0)


@pytest.mark.asyncio
async def test_api_client_fetches_statistics_through_asgi(api_app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=api_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as setup:
        await setup.post("/researchers", json={"full_name": "Taras Hnatiuk"})
        await setup.post("/experiments", json={"name": "Gas", "researcher_id": 1, "parameter": "pressure",
                                               "result": 101.3, "date": "2026-02-05"})

    async with ExperimentApiClient("http://test", transport=transport) as client:
        results = await client.fetch_many([1, 2])

    assert results[0].data is not None and results[0].data["maximum"] == 101.3
    assert results[1].error == "HTTP 404" and results[1].attempts == 1  # 4xx is not retried


@pytest.mark.asyncio
async def test_retry_with_backoff_after_server_errors() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"count": 1, "average": 1.0, "minimum": 1.0, "maximum": 1.0})

    async with ExperimentApiClient("http://test", transport=httpx.MockTransport(handler), backoff=0.01) as client:
        [result] = await client.fetch_many([1])

    assert result.data is not None and result.attempts == 3 and calls == 3


@pytest.mark.asyncio
async def test_retries_are_limited_and_error_is_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with ExperimentApiClient("http://test", transport=httpx.MockTransport(handler), retries=2,
                                   backoff=0.01) as client:
        [result] = await client.fetch_many([1])

    assert result.data is None and result.error == "ConnectError" and result.attempts == 2


@pytest.mark.asyncio
async def test_timeout_is_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with ExperimentApiClient("http://test", transport=httpx.MockTransport(handler), retries=1) as client:
        [result] = await client.fetch_many([1])

    assert result.error == "timeout"


@pytest.mark.asyncio
async def test_semaphore_limits_parallel_http_requests() -> None:
    active = peak = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return httpx.Response(200, json={"count": 0, "average": None, "minimum": None, "maximum": None})

    async with ExperimentApiClient("http://test", transport=httpx.MockTransport(handler),
                                   max_concurrency=2) as client:
        results = await client.fetch_many(list(range(1, 7)))

    assert peak == 2 and all(item.error is None for item in results)


@pytest.mark.asyncio
async def test_collect_statistics_runs_in_parallel_and_applies_timeout() -> None:
    def load(researcher_id: int) -> ResultSummary:
        time.sleep(0.5 if researcher_id == 3 else 0.1)
        return ResultSummary(1, float(researcher_id), 1.0, 1.0)

    start = time.perf_counter()
    result = await collect_statistics(load, [1, 2, 3], max_concurrency=3, timeout=0.3)
    elapsed = time.perf_counter() - start

    assert [item.error for item in result.items] == [None, None, "timeout"]
    assert result.items[1].statistics is not None and result.items[1].statistics.average == 2.0
    assert elapsed < 0.45  # 0.1 s tasks ran concurrently and the slow one was cut at 0.3 s


@pytest.mark.asyncio
async def test_api_client_command_prints_results(api_app: FastAPI, capsys: pytest.CaptureFixture[str]) -> None:
    from experiment_registry.commands.api_client import query_statistics

    transport = httpx.ASGITransport(app=api_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as setup:
        await setup.post("/researchers", json={"full_name": "Olena Kovalenko"})

    code = await query_statistics("http://test", [1, 5], timeout=1.0, retries=2, concurrency=2,
                                  transport=transport)

    out = capsys.readouterr().out
    assert code == 1  # researcher 5 does not exist
    assert "researcher 1: count=0" in out and "researcher 5: ERROR HTTP 404" in out


def test_lazy_module_level_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import experiment_registry.api as api_package

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'lazy.db'}")
    monkeypatch.delitem(api_package.__dict__, "app", raising=False)

    application = api_package.app

    assert application.title == "Experiment Registry API"
    assert api_package.app is application  # created once, then cached
    application.state.engine.dispose()
    with pytest.raises(AttributeError):
        _ = api_package.missing  # type: ignore[attr-defined]
