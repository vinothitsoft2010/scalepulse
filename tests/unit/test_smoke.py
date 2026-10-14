from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app

LATENCY_HEADER = "x-scalepulse-latency-ms"


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = Settings(database_url=None, admin_token=None, rate_limit_enabled=False)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "service": "ScalePulse Edge Gateway"}


def test_readiness_without_database_is_503(client: TestClient) -> None:
    resp = client.get("/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "not_ready", "database": "not_configured"}


def test_admin_api_disabled_without_token(client: TestClient) -> None:
    response = client.get("/api/v1/admin/tenants")
    assert response.status_code == 503


def test_admin_api_rejects_invalid_token() -> None:
    settings = Settings(database_url=None, admin_token=SecretStr("a" * 64))
    with TestClient(create_app(settings)) as test_client:
        response = test_client.get(
            "/api/v1/admin/tenants",
            headers={"Authorization": f"Bearer {'b' * 64}"},
        )
    assert response.status_code == 401


def test_resource_requires_api_key_when_rate_limit_enabled() -> None:
    settings = Settings(
        database_url=None,
        admin_token=None,
        rate_limit_enabled=True,
        redis_url=None,
    )
    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/resource")
    assert response.status_code == 401


def test_resource_fails_closed_without_redis() -> None:
    settings = Settings(
        database_url=None,
        admin_token=None,
        rate_limit_enabled=True,
        redis_url=None,
    )
    with TestClient(create_app(settings)) as test_client:
        response = test_client.get(
            "/api/v1/resource",
            headers={"X-API-Key": "sp_live_" + "a" * 64},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "rate_limiter_not_configured"


def test_resource(client: TestClient) -> None:
    resp = client.get("/api/v1/resource")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


@pytest.mark.parametrize("path", ["/health", "/api/v1/resource", "/does-not-exist"])
def test_latency_header_present(client: TestClient, path: str) -> None:
    resp = client.get(path)
    assert LATENCY_HEADER in resp.headers
    assert float(resp.headers[LATENCY_HEADER]) >= 0


def test_unknown_route_404(client: TestClient) -> None:
    assert client.get("/does-not-exist").status_code == 404
