from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from mlops_triage.config import Settings

SyncScenario = Literal["incident", "healthy"]


def resolve_sync_scenario() -> SyncScenario:
    raw = os.environ.get("SYNC_SCENARIO", "incident").strip().lower()
    if raw == "healthy":
        return "healthy"
    return "incident"


class SnapshotAdapter(ABC):
    @abstractmethod
    def pull_deployments(self) -> dict[str, list[dict[str, Any]]]:
        raise NotImplementedError

    @abstractmethod
    def pull_slo_snapshot(self) -> dict[str, dict[str, dict[str, Any]]]:
        raise NotImplementedError


class StubAdapter(SnapshotAdapter):
    """Simulates CD + metrics exporters for local demos and cron dry-runs."""

    def __init__(self, *, scenario: SyncScenario | None = None, at: datetime | None = None) -> None:
        self._scenario = scenario if scenario is not None else resolve_sync_scenario()
        self._at = at if at is not None else datetime.now(UTC)

    def pull_deployments(self) -> dict[str, list[dict[str, Any]]]:
        stamp = self._at.strftime("%Y-%m-%dT%H:%M:%SZ")
        canary_traffic = 12 if self._scenario == "incident" else 5
        return {
            "rec-engine": [
                {
                    "version": "3.8.1",
                    "channel": "canary",
                    "traffic_pct": canary_traffic,
                    "deployed_at_utc": stamp,
                    "status": "active",
                },
                {
                    "version": "3.8.0",
                    "channel": "stable",
                    "traffic_pct": 100 - canary_traffic,
                    "deployed_at_utc": "previous stable",
                    "status": "active",
                },
            ],
            "serving-prod-eu": [
                {
                    "version": "3.8.1",
                    "channel": "canary",
                    "traffic_pct": canary_traffic,
                    "deployed_at_utc": stamp,
                    "status": "active",
                },
            ],
        }

    def pull_slo_snapshot(self) -> dict[str, dict[str, dict[str, Any]]]:
        breached = self._scenario == "incident"
        if breached:
            latency = {"current_ms": 4200.0, "baseline_ms": 120.0}
            errors = {"current_pct": 8.7, "baseline_pct": 0.1}
        else:
            latency = {"current_ms": 95.0, "baseline_ms": 120.0}
            errors = {"current_pct": 0.05, "baseline_pct": 0.1}

        window = {"window_minutes": 15, "slo_breached": breached}
        metric_latency = {**latency, **window}
        metric_errors = {**errors, **window}

        series = {
            "latency_p99": metric_latency,
            "error_rate_503": metric_errors,
        }
        return {
            "serving-prod-eu": dict(series),
            "rec-engine": dict(series),
        }


def get_adapter(name: str, *, settings: Settings | None = None) -> SnapshotAdapter:
    normalized = name.strip().lower()
    if normalized == "stub":
        return StubAdapter()
    if normalized == "prometheus":
        from mlops_triage.config import get_settings
        from mlops_triage.sync.prometheus_adapter import PrometheusAdapter

        cfg = settings or get_settings()
        return PrometheusAdapter(cfg)
    raise ValueError(f"Unknown sync adapter {name!r}; supported: stub, prometheus")
