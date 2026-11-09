from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from mlops_triage.config import Settings, get_settings

SloMetric = Literal["latency_p99", "error_rate_503"]


def load_slo_snapshot(path: Path | None = None) -> dict[str, dict[str, dict[str, Any]]]:
    file_path = path or get_settings().slo_snapshot_file
    if not file_path.is_file():
        raise FileNotFoundError(f"SLO snapshot not found: {file_path}")

    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"SLO snapshot must be a JSON object: {file_path}")

    return data


def fetch_slo_status(
    service: str,
    metric: SloMetric,
    *,
    settings: Settings | None = None,
    snapshot_path: Path | None = None,
) -> dict[str, object]:
    cfg = settings or get_settings()
    path = snapshot_path or cfg.slo_snapshot_file
    snapshot = load_slo_snapshot(path)

    service_metrics = snapshot.get(service)
    if not isinstance(service_metrics, dict):
        return {
            "service": service,
            "metric": metric,
            "found": False,
            "source": str(path.resolve()),
            "message": "No metrics for this service in the SLO snapshot.",
        }

    series = service_metrics.get(metric)
    if not isinstance(series, dict):
        return {
            "service": service,
            "metric": metric,
            "found": False,
            "source": str(path.resolve()),
            "message": "No metric series for this service/metric in the SLO snapshot.",
        }

    return {
        "service": service,
        "metric": metric,
        "found": True,
        "source": str(path.resolve()),
        **series,
    }
