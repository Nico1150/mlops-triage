import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from mlops_triage.api import health as health_module
from mlops_triage.api.app import app
from mlops_triage.api.health import HealthCheck, deep_health_payload, overall_status
from mlops_triage.config import Settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_overall_status_aggregation():
    assert overall_status([HealthCheck("a", "ok", "", {})]) == "ok"
    assert overall_status([HealthCheck("a", "warn", "", {})]) == "degraded"
    assert overall_status([HealthCheck("a", "fail", "", {})]) == "unhealthy"


def test_deep_health_payload_with_tmp_snapshots(tmp_path, monkeypatch):
    deploy = tmp_path / "deployments.json"
    slo = tmp_path / "slo.json"
    deploy.write_text("{}\n", encoding="utf-8")
    slo.write_text("{}\n", encoding="utf-8")

    settings = Settings(
        deployments_file=deploy,
        slo_snapshot_file=slo,
        rag_index_file=tmp_path / "missing_rag.json",
        runbooks_dir=tmp_path / "runbooks",
    )
    settings.runbooks_dir.mkdir()

    monkeypatch.setattr(
        health_module,
        "check_llm",
        lambda _s: HealthCheck("llm", "ok", "mock", {}),
    )

    payload = deep_health_payload(settings)
    assert payload["status"] in ("ok", "degraded")
    names = {c["name"] for c in payload["checks"]}
    assert names == {"llm", "deployments_snapshot", "slo_snapshot", "rag_index"}
    rag = next(c for c in payload["checks"] if c["name"] == "rag_index")
    assert rag["status"] == "warn"


def test_health_ready_endpoint(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        health_module,
        "deep_health_payload",
        lambda settings=None: {
            "status": "unhealthy",
            "checks": [],
        },
    )
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"


def test_health_deep_query_param(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        health_module,
        "deep_health_payload",
        lambda settings=None: {"status": "ok", "checks": []},
    )
    response = client.get("/health?deep=1")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_shallow_health_unchanged(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "llm_model" in body
    assert "checks" not in body
