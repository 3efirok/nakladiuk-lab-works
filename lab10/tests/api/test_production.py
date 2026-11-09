"""Health endpoint and protection of write operations with a token (lab 10)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from experiment_registry.api.app import create_app
from experiment_registry.settings import Settings

pytestmark = pytest.mark.integration


def test_health_reports_database_and_version(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() | {"version": "-"} == {
        "status": "ok",
        "database": "ok",
        "version": "-",
        "environment": "development",
    }


def test_health_returns_503_when_database_is_unavailable(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'missing_dir' / 'db.sqlite'}", create_schema=False)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


@pytest.fixture
def protected(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(api_token=SecretStr("s3cret"), environment="production")
    with TestClient(create_app(f"sqlite:///{tmp_path / 'p.db'}", settings=settings)) as client:
        yield client


def test_write_requires_token_when_configured(protected: TestClient) -> None:
    body = {"full_name": "Olena Kovalenko"}

    assert protected.post("/researchers", json=body).status_code == 401
    assert protected.post("/researchers", json=body, headers={"X-API-Token": "wrong"}).status_code == 401
    assert protected.post("/researchers", json=body, headers={"X-API-Token": "s3cret"}).status_code == 201


def test_read_endpoints_stay_public(protected: TestClient) -> None:
    assert protected.get("/researchers").status_code == 200
    assert protected.get("/health").json()["environment"] == "production"
