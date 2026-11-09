from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlops_triage.config import get_settings


def ollama_is_reachable() -> bool:
    import urllib.error
    import urllib.request

    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


@pytest.fixture(scope="session")
def ollama_available() -> bool:
    return ollama_is_reachable()


@pytest.fixture
def skip_without_ollama(ollama_available: bool):
    if not ollama_available:
        pytest.skip("Ollama not reachable at localhost:11434")


def ollama_has_embedding_model() -> bool:
    if not ollama_is_reachable():
        return False
    import urllib.request

    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except OSError:
        return False

    wanted = get_settings().embedding_model.split(":")[0]
    for model in payload.get("models", []):
        name = model.get("name", "")
        if name == wanted or name.startswith(f"{wanted}:"):
            return True
    return False


@pytest.fixture
def skip_without_embedding_model(skip_without_ollama):
    if not ollama_has_embedding_model():
        settings = get_settings()
        pytest.skip(
            f"Embedding model not in Ollama: {settings.embedding_model} "
            "(run: ollama pull nomic-embed-text)"
        )


@pytest.fixture
def incident_cases():
    from mlops_triage.eval.golden import load_golden_cases

    return load_golden_cases()
