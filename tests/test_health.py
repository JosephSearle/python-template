import asyncio

import pytest
from fastapi.testclient import TestClient

from python_template import health
from python_template.health import ReadinessRegistry


def test_healthz_returns_200(client: TestClient) -> None:
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_readyz_returns_200_with_no_checks(client: TestClient) -> None:
    res = client.get("/readyz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "checks": {}}


def test_readyz_returns_200_when_every_check_passes(
    client: TestClient, registry: ReadinessRegistry
) -> None:
    async def cache() -> None:
        pass

    registry.register("cache", cache)
    registry.register("queue", lambda: None)
    res = client.get("/readyz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "checks": {"cache": "ok", "queue": "ok"}}


def test_readyz_returns_503_and_hides_the_error_when_a_check_fails(
    client: TestClient, registry: ReadinessRegistry
) -> None:
    def database() -> None:
        raise ConnectionError("connect ECONNREFUSED db.internal:5432")

    registry.register("cache", lambda: None)
    registry.register("database", database)
    res = client.get("/readyz")
    assert res.status_code == 503
    assert res.json() == {"status": "unavailable", "checks": {"cache": "ok", "database": "error"}}
    assert "db.internal" not in res.text


def test_readyz_reports_a_slow_check_as_timeout(
    client: TestClient, registry: ReadinessRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "CHECK_TIMEOUT_SECONDS", 0.05)

    async def slow() -> None:
        await asyncio.sleep(1)

    registry.register("slow", slow)
    res = client.get("/readyz")
    assert res.status_code == 503
    assert res.json()["checks"] == {"slow": "timeout"}


def test_readyz_returns_503_while_draining_and_healthz_stays_200(
    client: TestClient, registry: ReadinessRegistry
) -> None:
    registry.start_draining()
    assert client.get("/readyz").status_code == 503
    assert client.get("/healthz").status_code == 200


def test_registering_the_same_check_twice_fails(registry: ReadinessRegistry) -> None:
    registry.register("database", lambda: None)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("database", lambda: None)


def test_a_safe_request_id_is_echoed_and_an_unsafe_one_replaced(client: TestClient) -> None:
    kept = client.get("/healthz", headers={"x-request-id": "abc-123"})
    assert kept.headers["x-request-id"] == "abc-123"
    replaced = client.get("/healthz", headers={"x-request-id": "bad id with spaces"})
    assert len(replaced.headers["x-request-id"]) == 36
