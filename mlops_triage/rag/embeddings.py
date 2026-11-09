from __future__ import annotations

from openai import OpenAI


def embed_texts(client: OpenAI, model: str, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    response = client.embeddings.create(model=model, input=texts)
    ordered = sorted(response.data, key=lambda row: row.index)
    return [row.embedding for row in ordered]


def embed_query(client: OpenAI, model: str, query: str) -> list[float]:
    vectors = embed_texts(client, model, [query])
    return vectors[0]
