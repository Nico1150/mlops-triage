import pytest

from mlops_triage.agent import run_agent
from mlops_triage.config import get_settings
from mlops_triage.eval import assert_triage_expectations
from mlops_triage.fixtures import SAMPLE_ALERT
from mlops_triage.llm import create_openai_client
from mlops_triage.schemas import TriageReport
from mlops_triage.tools import default_mlops_tools

SYSTEM_PROMPT = """\
You are an on-call MLOps engineer. Use search_runbook, deployment/SLO tools,
then submit_triage_report once. Services: rec-engine, serving-prod-eu.
"""


@pytest.mark.integration
def test_agent_triage_sample_alert(
    skip_without_ollama,
    skip_without_embedding_model,
):
    settings = get_settings()
    client = create_openai_client(settings)

    result = run_agent(
        client=client,
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Triage:\n\n{SAMPLE_ALERT.strip()}",
            },
        ],
        tools=default_mlops_tools(),
        temperature=0.2,
        max_steps=12,
    )

    assert isinstance(result, TriageReport)
    assert_triage_expectations(
        result,
        {
            "priority": "P1",
            "rollback_recommended": True,
            "min_actions": 1,
        },
    )
