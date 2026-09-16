"""The plan endpoint: shape, error responses and no leaked internals."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.plan_store import plan_store
from app.config import get_settings
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    plan_store.clear()
    get_settings.cache_clear()
    # raise_server_exceptions=False so the 500 handler answers like a real server.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()
    plan_store.clear()


@pytest.fixture
def use_data_path(monkeypatch: pytest.MonkeyPatch):
    def _use(path: Path) -> None:
        monkeypatch.setenv("DATA_PATH", str(path))
        get_settings.cache_clear()

    return _use


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ai_provider"] == "none"
    assert body["ai_configured"] is False


def test_plan_seed_returns_the_expected_shape(client: TestClient) -> None:
    response = client.post("/api/plan/seed")
    assert response.status_code == 200

    body = response.json()
    assert set(body) == {"plan_id", "source_file", "source", "plan"}
    assert body["source_file"].endswith(".xlsx")
    assert len(body["plan_id"]) == 64  # sha256 of the normalised source data

    source = body["source"]
    assert set(source) == {"farms", "clients", "station", "reference_prices"}
    assert len(source["farms"]) == 20
    assert len(source["clients"]) == 10
    assert len(source["reference_prices"]) == 4

    plan = body["plan"]
    assert set(plan) == {
        "kpis",
        "segment_comparison",
        "farm_comparison",
        "clients",
        "allocations",
        "residuals",
        "risk_links",
        "invariants",
    }
    assert len(plan["allocations"]) == 43
    assert len(plan["clients"]) == 10
    assert len(plan["farm_comparison"]) == 20
    assert len(plan["segment_comparison"]) == 4
    assert all(item["passed"] for item in plan["invariants"])


def test_plan_seed_numbers_are_plain_json_numbers(client: TestClient) -> None:
    plan = client.post("/api/plan/seed").json()["plan"]
    kpis = plan["kpis"]
    assert kpis["export_volume_t"] == 500
    assert kpis["local_volume_t"] == 60
    assert kpis["export_revenue_eur"] == 549500
    assert kpis["local_value_eur"] == 4500
    assert kpis["at_risk_clients"] == 3
    assert round(kpis["export_rate"] * 100, 1) == 89.3
    assert isinstance(kpis["export_revenue_eur"], (int, float))


def test_plan_contains_no_timestamp(client: TestClient) -> None:
    """The plan must be byte for byte the same on every call."""
    first = client.post("/api/plan/seed")
    second = client.post("/api/plan/seed")

    assert first.json() == second.json()
    assert first.json()["plan_id"] == second.json()["plan_id"]
    assert "X-Compute-Ms" in first.headers  # timing lives in the header only


def test_plan_is_cached_for_the_assistant(client: TestClient) -> None:
    plan_id = client.post("/api/plan/seed").json()["plan_id"]
    stored = plan_store.get(plan_id)
    assert stored is not None
    assert stored.plan.kpis.export_volume_t == 500


def test_invalid_workbook_returns_422_with_all_errors(
    client: TestClient, use_data_path, edited_workbook
) -> None:
    use_data_path(
        edited_workbook(
            ("Farms", "A6", "F01"),  # duplicate farm id
            ("Clients", "C6", "maybe"),  # invalid acceptance mode
        )
    )
    response = client.post("/api/plan/seed")

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "VALIDATION_FAILED"
    assert "plan" not in body  # never a partial plan

    codes = {item["code"] for item in body["errors"]}
    assert {"ID_DUPLICATE", "MODE_INVALID"} <= codes
    first = body["errors"][0]
    assert set(first) == {"code", "sheet", "row", "entity_id", "field", "message"}


def test_missing_data_file_returns_500_without_a_stack_trace(
    client: TestClient, use_data_path, tmp_path: Path
) -> None:
    use_data_path(tmp_path / "nothing-here.xlsx")
    response = client.post("/api/plan/seed")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "SERVER_ERROR"
    assert "Traceback" not in body["message"]
    assert "nothing-here.xlsx" in body["message"]


def test_unexpected_error_is_not_leaked(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_source):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr("app.api.routes_plan.build_plan", boom)
    response = client.post("/api/plan/seed")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error": "SERVER_ERROR",
        "message": "Something went wrong on the server. Please try again.",
    }
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text


def test_invariant_violation_returns_500_not_a_plan(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, seed_source
) -> None:
    from app.domain.models import Invariant
    from app.planning.invariants import InvariantViolation

    def broken(_source):
        raise InvariantViolation(
            [Invariant(name="export_within_station_capacity", passed=False, detail="over capacity")]
        )

    monkeypatch.setattr("app.api.routes_plan.build_plan", broken)
    response = client.post("/api/plan/seed")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "SERVER_ERROR"
    assert "export_within_station_capacity" in body["message"]
    assert "plan" not in body


def test_unknown_route_is_not_an_api_error(client: TestClient) -> None:
    assert client.get("/api/does-not-exist").status_code == 404
