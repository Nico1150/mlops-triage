from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from mlops_triage.config import Settings, get_settings
from mlops_triage.llm.client import create_openai_client
from mlops_triage.rag.chunk import RunbookChunk, load_runbook_chunks
from mlops_triage.rag.embeddings import embed_query, embed_texts
from mlops_triage.rag.rank import top_k_by_vector


def _runbooks_latest_mtime(runbooks_dir: Path) -> float:
    mtimes = [p.stat().st_mtime for p in runbooks_dir.glob("*.md")]
    return max(mtimes) if mtimes else 0.0


def index_is_stale(settings: Settings) -> bool:
    index_path = settings.rag_index_file
    if not index_path.is_file():
        return True
    if index_path.stat().st_mtime < _runbooks_latest_mtime(settings.runbooks_dir):
        return True
    try:
        with index_path.open(encoding="utf-8") as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError):
        return True
    if meta.get("embedding_model") != settings.embedding_model:
        return True
    if meta.get("runbooks_dir") != str(settings.runbooks_dir.resolve()):
        return True
    return False


def build_runbook_index(
    *,
    client: OpenAI | None = None,
    settings: Settings | None = None,
) -> Path:
    cfg = settings or get_settings()
    llm = client or create_openai_client(cfg)
    chunks = load_runbook_chunks(cfg.runbooks_dir)
    texts = [c.text for c in chunks]
    vectors = embed_texts(llm, cfg.embedding_model, texts)

    records: list[dict[str, Any]] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        records.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_file": chunk.source_file,
                "title": chunk.title,
                "text": chunk.text,
                "embedding": vector,
            }
        )

    payload = {
        "embedding_model": cfg.embedding_model,
        "built_at_utc": datetime.now(UTC).isoformat(),
        "runbooks_dir": str(cfg.runbooks_dir.resolve()),
        "records": records,
    }
    cfg.rag_index_file.parent.mkdir(parents=True, exist_ok=True)
    with cfg.rag_index_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f)
    return cfg.rag_index_file


def _load_index_records(settings: Settings) -> list[dict[str, Any]]:
    with settings.rag_index_file.open(encoding="utf-8") as f:
        payload = json.load(f)
    return payload["records"]


def ensure_runbook_index(
    *,
    client: OpenAI | None = None,
    settings: Settings | None = None,
) -> Path:
    cfg = settings or get_settings()
    if index_is_stale(cfg):
        return build_runbook_index(client=client, settings=cfg)
    return cfg.rag_index_file


def search_runbooks(
    query: str,
    top_k: int = 3,
    *,
    client: OpenAI | None = None,
    settings: Settings | None = None,
) -> dict[str, object]:
    cfg = settings or get_settings()
    llm = client or create_openai_client(cfg)
    ensure_runbook_index(client=llm, settings=cfg)

    records = _load_index_records(cfg)
    query_vector = embed_query(llm, cfg.embedding_model, query)
    hits = top_k_by_vector(query_vector, records, k=top_k)

    return {
        "query": query,
        "top_k": top_k,
        "index": str(cfg.rag_index_file.resolve()),
        "hits": [
            {
                "chunk_id": hit["chunk_id"],
                "source_file": hit["source_file"],
                "title": hit["title"],
                "text": hit["text"],
                "score": round(float(hit["score"]), 4),
            }
            for hit in hits
        ],
    }
