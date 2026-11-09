from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mlops_triage.config import Settings, get_settings

def load_deployments_catalog(path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    file_path = path or get_settings().deployments_file
    if not file_path.is_file():
        raise FileNotFoundError(f"Deployments catalog not found: {file_path}")

    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Deployments catalog must be a JSON object: {file_path}")

    return data


def fetch_recent_deployments(
    service: str,
    limit: int,
    *,
    settings: Settings | None = None,
    catalog_path: Path | None = None,
) -> dict[str, object]:
    """Return recent deployments for a service from the on-disk catalog."""
    cfg = settings or get_settings()
    path = catalog_path or cfg.deployments_file
    catalog = load_deployments_catalog(path)
    rows = catalog.get(service, [])

    return {
        "service": service,
        "deployments": rows[:limit],
        "source": str(path.resolve()),
        "catalog_version": "file",
    }
