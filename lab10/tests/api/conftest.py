from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from experiment_registry.api.app import create_app

EXPERIMENTS = [
    {
        "name": "Thermal conductivity of Al alloy",
        "researcher_id": 1,
        "parameter": "temperature",
        "result": 293.4,
        "date": "2026-02-03",
    },
    {
        "name": "Gas compression test",
        "researcher_id": 2,
        "parameter": "pressure",
        "result": 101.3,
        "date": "2026-02-05",
    },
    {
        "name": "Thermal conductivity of Cu",
        "researcher_id": 1,
        "parameter": "temperature",
        "result": 301.8,
        "date": "2026-02-10",
        "notes": "second sample",
    },
    {
        "name": "Cryogenic cooling run",
        "researcher_id": 2,
        "parameter": "temperature",
        "result": 77.2,
        "date": "2026-01-18",
    },
]


@pytest.fixture
def api_app(tmp_path: Path) -> Iterator[FastAPI]:
    """Application bound to a separate SQLite database for every test."""
    app = create_app(f"sqlite:///{tmp_path / 'api_test.db'}")
    yield app
    app.state.engine.dispose()  # ASGITransport does not run the lifespan handler


@pytest.fixture
def client(api_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(api_app) as test_client:  # runs lifespan (engine.dispose on exit)
        yield test_client


@pytest.fixture
def seeded(client: TestClient) -> TestClient:
    for name, email in (("Olena Kovalenko", "o.kovalenko@lnu.edu.ua"), ("Taras Hnatiuk", None)):
        assert client.post("/researchers", json={"full_name": name, "email": email}).status_code == 201
    for body in EXPERIMENTS:
        assert client.post("/experiments", json=body).status_code == 201
    return client
