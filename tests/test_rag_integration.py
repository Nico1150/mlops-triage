import pytest

from mlops_triage.config import get_settings
from mlops_triage.llm import create_openai_client
from mlops_triage.rag import search_runbooks


@pytest.mark.integration
def test_search_runbooks_canary_rollback(skip_without_embedding_model):
    settings = get_settings()
    client = create_openai_client(settings)

    result = search_runbooks(
        "how to rollback canary after SLO breach",
        top_k=2,
        client=client,
        settings=settings,
    )

    assert result["hits"]
    joined = " ".join(hit["source_file"] + hit["text"] for hit in result["hits"]).lower()
    assert "canary" in joined or "rollback" in joined
