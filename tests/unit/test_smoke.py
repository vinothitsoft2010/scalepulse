import pytest
from fastapi.testclient import TestClient

from app.main import create_app

LATENCY_HEADER = "x-scalepulse-latency-ms"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "service": "ScalePulse Edge Gateway"}


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
