import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from mlops_triage.api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "llm_model" in body
    assert "embedding_model" in body


@pytest.mark.integration
def test_triage_endpoint_sample_alert(client: TestClient, skip_without_embedding_model):
    from mlops_triage.fixtures import SAMPLE_ALERT

    response = client.post(
        "/triage",
        json={
            "alert": SAMPLE_ALERT.strip(),
            "use_runbooks": True,
            "temperature": 0.2,
            "max_agent_steps": 22,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["incident"]["severity"] == "critical"
    assert data["triage"]["priority"] == "P1"
    assert "triage" in data and "recommended_actions" in data["triage"]
