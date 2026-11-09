"""REST API tests with FastAPI TestClient."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_root_returns_service_info(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_create_researcher_returns_201_and_location_fields(client: TestClient) -> None:
    response = client.post("/researchers", json={"full_name": "Iryna Melnyk", "email": "i.melnyk@lnu.edu.ua"})

    assert response.status_code == 201
    assert response.json() == {"id": 1, "full_name": "Iryna Melnyk", "email": "i.melnyk@lnu.edu.ua",
                               "department": "Physics"}


def test_duplicate_researcher_returns_409(seeded: TestClient) -> None:
    response = seeded.post("/researchers", json={"full_name": "Olena Kovalenko"})

    assert response.status_code == 409


def test_create_experiment_returns_created_object(seeded: TestClient) -> None:
    body = {"name": "Heat exchanger efficiency", "researcher_id": 1, "parameter": "temperature",
            "result": 348.9, "date": "2026-03-02"}

    response = seeded.post("/experiments", json=body)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 5 and data["researcher"] == "Olena Kovalenko" and data["notes"] is None


@pytest.mark.parametrize(
    ("change", "field"),
    [({"result": -1}, "result"), ({"result": "abc"}, "result"), ({"parameter": "Temp!"}, "parameter"),
     ({"name": ""}, "name"), ({"date": "2031-01-01"}, "date"), ({"date": "03.02.2026"}, "date"),
     ({"researcher_id": 0}, "researcher_id")],
    ids=["negative", "not-number", "bad-parameter", "empty-name", "future-date", "bad-date", "bad-id"],
)
def test_invalid_experiment_body_returns_422(seeded: TestClient, change: dict[str, Any], field: str) -> None:
    body = {"name": "Run", "researcher_id": 1, "parameter": "temperature", "result": 1.0,
            "date": "2026-02-03"} | change

    response = seeded.post("/experiments", json=body)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


def test_experiment_for_unknown_researcher_returns_404(seeded: TestClient) -> None:
    body = {"name": "Run", "researcher_id": 99, "parameter": "temperature", "result": 1.0, "date": "2026-02-03"}

    assert seeded.post("/experiments", json=body).status_code == 404


def test_get_experiment_by_id(seeded: TestClient) -> None:
    assert seeded.get("/experiments/3").json()["notes"] == "second sample"
    assert seeded.get("/experiments/99").status_code == 404
    assert seeded.get("/experiments/abc").status_code == 422


def test_list_is_sorted_by_date_by_default(seeded: TestClient) -> None:
    dates = [item["date"] for item in seeded.get("/experiments").json()]

    assert dates == sorted(dates)


@pytest.mark.parametrize(
    ("params", "expected_ids"),
    [({"researcher_id": 1}, [1, 3]), ({"parameter": "temperature", "min_result": 100, "max_result": 300}, [1]),
     ({"sort": "-result"}, [3, 1, 2, 4]), ({"sort": "result", "limit": 2, "offset": 1}, [2, 1])],
    ids=["researcher", "range", "sort-desc", "pagination"],
)
def test_query_parameters_filter_sort_and_paginate(seeded: TestClient, params: dict[str, Any],
                                                   expected_ids: list[int]) -> None:
    assert [item["id"] for item in seeded.get("/experiments", params=params).json()] == expected_ids


def test_invalid_range_and_sort_return_422(seeded: TestClient) -> None:
    assert seeded.get("/experiments", params={"min_result": 10, "max_result": 1}).status_code == 422
    assert seeded.get("/experiments", params={"sort": "name"}).status_code == 422


def test_researcher_experiments(seeded: TestClient) -> None:
    response = seeded.get("/researchers/2/experiments")

    assert [item["name"] for item in response.json()] == ["Cryogenic cooling run", "Gas compression test"]
    assert seeded.get("/researchers/42/experiments").status_code == 404


def test_patch_changes_only_sent_fields(seeded: TestClient) -> None:
    before = seeded.get("/experiments/1").json()

    response = seeded.patch("/experiments/1", json={"result": 295.0})

    assert response.status_code == 200
    assert response.json() == before | {"result": 295.0}


@pytest.mark.parametrize("body", [{}, {"result": -5}, {"researcher_id": 2}],
                         ids=["empty", "invalid-value", "unknown-field"])
def test_invalid_patch_returns_422(seeded: TestClient, body: dict[str, Any]) -> None:
    assert seeded.patch("/experiments/1", json=body).status_code == 422


def test_delete_returns_204_and_object_disappears(seeded: TestClient) -> None:
    assert seeded.delete("/experiments/2").status_code == 204
    assert seeded.get("/experiments/2").status_code == 404
    assert seeded.delete("/experiments/2").status_code == 404


def test_statistics_endpoint(seeded: TestClient) -> None:
    overall = seeded.get("/experiments/statistics").json()
    temperature = seeded.get("/experiments/statistics", params={"parameter": "temperature"}).json()
    olena = seeded.get("/experiments/statistics", params={"researcher_id": 1}).json()

    assert overall["count"] == 4
    assert (temperature["minimum"], temperature["maximum"]) == (77.2, 301.8)
    assert olena["average"] == pytest.approx(297.6)
    assert seeded.get("/experiments/statistics", params={"researcher_id": 9}).status_code == 404


def test_statistics_by_researcher_runs_concurrently_and_reports_errors(seeded: TestClient) -> None:
    response = seeded.get("/experiments/statistics/by-researcher", params={"ids": [1, 2, 7], "max_concurrency": 2})

    items = {item["researcher_id"]: item for item in response.json()["items"]}
    assert items[1]["statistics"]["count"] == 2
    assert items[2]["statistics"]["maximum"] == 101.3
    assert items[7]["error"] == "Researcher #7 not found."


def test_openapi_documents_all_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert {"/experiments", "/experiments/{experiment_id}", "/experiments/statistics",
            "/researchers/{researcher_id}/experiments"} <= set(paths)
    assert {"get", "patch", "delete"} <= set(paths["/experiments/{experiment_id}"])
