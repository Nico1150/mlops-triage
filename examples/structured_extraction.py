"""Extract a structured ML incident from unstructured alert text."""

import os

from mlops_triage.config import get_settings
from mlops_triage.fixtures import SAMPLE_ALERT
from mlops_triage.llm import complete_structured, create_openai_client
from mlops_triage.schemas import MLIncident

if __name__ == "__main__":
    settings = get_settings()
    client = create_openai_client(settings)
    use_runbooks = os.environ.get("USE_RUNBOOKS", "1") != "0"

    user_content = (
        "Extract an incident report from the following alert text:\n\n"
        f"{SAMPLE_ALERT.strip()}"
    )
    if use_runbooks:
        from mlops_triage.rag import (
            ensure_runbook_index,
            format_runbook_context,
            search_runbooks,
        )

        ensure_runbook_index(client=client, settings=settings)
        ctx = search_runbooks(SAMPLE_ALERT.strip(), top_k=2, client=client, settings=settings)
        user_content += (
            "\n\nRelevant runbook excerpts:\n\n" + format_runbook_context(ctx)
        )

    incident = complete_structured(
        client=client,
        model=settings.llm_model,
        messages=[{"role": "user", "content": user_content}],
        response_model=MLIncident,
        temperature=0.2,
    )

    print(incident.model_dump_json(indent=2))
