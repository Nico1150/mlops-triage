from __future__ import annotations

import math
from typing import Any


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def top_k_by_vector(
    query_vector: list[float],
    records: list[dict[str, Any]],
    *,
    k: int,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for record in records:
        score = cosine_similarity(query_vector, record["embedding"])
        scored.append((score, record))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {
            **rec,
            "score": score,
            "embedding": None,
        }
        for score, rec in scored[:k]
    ]
