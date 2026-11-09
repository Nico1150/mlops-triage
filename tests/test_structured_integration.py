import pytest

from mlops_triage.config import get_settings
from mlops_triage.eval import assert_incident_expectations
from mlops_triage.llm import complete_structured, create_openai_client
from mlops_triage.schemas import MLIncident


@pytest.mark.integration
def test_structured_extraction_cases(incident_cases, skip_without_ollama):
    settings = get_settings()
    client = create_openai_client(settings)

    for case in incident_cases:
        incident = complete_structured(
            client=client,
            model=settings.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Extract an incident report from the following alert text:\n\n"
                        f"{case['alert'].strip()}"
                    ),
                },
            ],
            response_model=MLIncident,
            temperature=0.2,
        )
        assert_incident_expectations(incident, case["expected_incident"])
