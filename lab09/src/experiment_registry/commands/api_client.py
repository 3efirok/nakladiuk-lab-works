"""Lab 8 scenario: run the API server or query it concurrently with the async HTTP client."""

import asyncio
import logging
import time

import httpx

from experiment_registry.api.external import ExperimentApiClient


async def query_statistics(base_url: str, researcher_ids: list[int], timeout: float, retries: int,
                           concurrency: int, transport: httpx.AsyncBaseTransport | None = None) -> int:
    start = time.perf_counter()
    async with ExperimentApiClient(base_url, timeout=timeout, retries=retries,
                                   max_concurrency=concurrency, transport=transport) as client:
        results = await client.fetch_many(researcher_ids)
    total = (time.perf_counter() - start) * 1000
    print(f"GET {base_url}/experiments/statistics?researcher_id=... "
          f"(timeout={timeout}s, retries={retries}, Semaphore({concurrency}))")
    for item in results:
        if item.data is not None:
            print(f"  researcher {item.researcher_id}: count={item.data['count']} "
                  f"average={item.data['average']} min={item.data['minimum']} max={item.data['maximum']}"
                  f"  [{item.attempts} attempt(s), {item.elapsed_ms} ms]")
        else:
            print(f"  researcher {item.researcher_id}: ERROR {item.error}  "
                  f"[{item.attempts} attempt(s), {item.elapsed_ms} ms]")
    print(f"Total: {len(results)} requests in {total:.1f} ms")
    return 0 if all(item.error is None for item in results) else 1


def run_api_client(base_url: str, researcher_ids: list[int], timeout: float, retries: int,
                   concurrency: int) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    return asyncio.run(query_statistics(base_url.rstrip("/"), researcher_ids, timeout, retries, concurrency))


def run_server(host: str, port: int) -> int:
    import uvicorn

    uvicorn.run("experiment_registry.api:app", host=host, port=port)
    return 0
