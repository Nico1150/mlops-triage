import pytest

from mlops_triage.eval import assert_incident_expectations, assert_triage_expectations
from mlops_triage.fixtures import SAMPLE_ALERT
from mlops_triage.pipelines import run_incident_pipeline


@pytest.mark.integration
def test_full_incident_pipeline_serving_alert(
    skip_without_ollama,
    skip_without_embedding_model,
):
    result = run_incident_pipeline(SAMPLE_ALERT)

    assert_incident_expectations(
        result.incident,
        {
            "severity": "critical",
            "component_contains": "serv",
            "min_confidence": 0.5,
        },
    )
    assert_triage_expectations(
        result.triage,
        {
            "rollback_recommended": True,
            "priority": "P1",
            "min_actions": 1,
        },
    )
