from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from mlops_triage.config import Settings, get_settings
from mlops_triage.llm.client import create_openai_client
from mlops_triage.rag.search import index_is_stale

CheckStatus = Literal["ok", "warn", "fail"]
OverallStatus = Literal["ok", "degraded", "unhealthy"]


def _snapshot_max_age_seconds() -> int:
    raw = os.environ.get("HEALTH_SNAPSHOT_MAX_AGE_SECONDS", "86400").strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return 86_400


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: CheckStatus
    detail: str
    meta: dict[str, Any]


def _iso_mtime(path: Path) -> str | None:
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def check_llm(settings: Settings) -> HealthCheck:
    try:
        client = create_openai_client(settings)
        client.models.list()
        return HealthCheck(
            name="llm",
            status="ok",
            detail="LLM API reachable",
            meta={
                "llm_base_url": settings.llm_base_url,
                "llm_model": settings.llm_model,
            },
        )
    except Exception as exc:
        return HealthCheck(
            name="llm",
            status="fail",
            detail=f"LLM API unreachable: {exc}",
            meta={
                "llm_base_url": settings.llm_base_url,
                "llm_model": settings.llm_model,
            },
        )


def check_snapshot_file(path: Path, *, label: str) -> HealthCheck:
    max_age = _snapshot_max_age_seconds()
    if not path.is_file():
        return HealthCheck(
            name=label,
            status="fail",
            detail=f"Missing snapshot file: {path}",
            meta={"path": str(path.resolve())},
        )
    age_s = max(0, int(datetime.now(tz=UTC).timestamp() - path.stat().st_mtime))
    status: CheckStatus = "ok" if age_s <= max_age else "warn"
    detail = "Snapshot present"
    if status == "warn":
        detail = f"Snapshot older than {max_age}s"
    return HealthCheck(
        name=label,
        status=status,
        detail=detail,
        meta={
            "path": str(path.resolve()),
            "age_seconds": age_s,
            "max_age_seconds": max_age,
            "modified_at_utc": _iso_mtime(path),
        },
    )


def check_rag_index(settings: Settings) -> HealthCheck:
    path = settings.rag_index_file
    runbooks = settings.runbooks_dir
    stale = index_is_stale(settings)
    meta: dict[str, Any] = {
        "rag_index_file": str(path.resolve()),
        "runbooks_dir": str(runbooks.resolve()),
        "embedding_model": settings.embedding_model,
        "index_exists": path.is_file(),
        "index_stale": stale,
    }
    if not path.is_file():
        return HealthCheck(
            name="rag_index",
            status="warn",
            detail="RAG index missing (will build on first search)",
            meta=meta,
        )
    try:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
        meta["record_count"] = len(payload.get("records") or [])
        meta["built_at_utc"] = payload.get("built_at_utc")
    except (json.JSONDecodeError, OSError) as exc:
        return HealthCheck(
            name="rag_index",
            status="warn",
            detail=f"RAG index unreadable: {exc}",
            meta=meta,
        )
    if stale:
        return HealthCheck(
            name="rag_index",
            status="warn",
            detail="RAG index stale vs runbooks or embedding model",
            meta=meta,
        )
    return HealthCheck(
        name="rag_index",
        status="ok",
        detail="RAG index present and fresh",
        meta=meta,
    )


def overall_status(checks: list[HealthCheck]) -> OverallStatus:
    if any(c.status == "fail" for c in checks):
        return "unhealthy"
    if any(c.status == "warn" for c in checks):
        return "degraded"
    return "ok"


def shallow_health_payload(settings: Settings) -> dict[str, str]:
    return {
        "status": "ok",
        "llm_model": settings.llm_model,
        "llm_base_url": settings.llm_base_url,
        "embedding_model": settings.embedding_model,
    }


def deep_health_payload(settings: Settings | None = None) -> dict[str, Any]:
    cfg = settings or get_settings()
    checks = [
        check_llm(cfg),
        check_snapshot_file(cfg.deployments_file, label="deployments_snapshot"),
        check_snapshot_file(cfg.slo_snapshot_file, label="slo_snapshot"),
        check_rag_index(cfg),
    ]
    status = overall_status(checks)
    return {
        "status": status,
        "llm_model": cfg.llm_model,
        "llm_base_url": cfg.llm_base_url,
        "embedding_model": cfg.embedding_model,
        "checked_at_utc": datetime.now(tz=UTC).isoformat(),
        "checks": [
            {
                "name": c.name,
                "status": c.status,
                "detail": c.detail,
                "meta": c.meta,
            }
            for c in checks
        ],
    }


def deep_health_http_status(payload: dict[str, Any]) -> int:
    if payload.get("status") == "unhealthy":
        return 503
    return 200
