from __future__ import annotations

from collections import defaultdict
from typing import Any

import httpx

from mlops_triage.config import Settings, get_settings
from mlops_triage.sync.adapters import SnapshotAdapter
from mlops_triage.sync.prometheus_client import PrometheusError, query_instant


class PrometheusAdapter(SnapshotAdapter):
    """
    Pulls tool snapshots from Prometheus instant queries.

    Deployments: mlops_deployment_traffic_pct (or custom PromQL).
    SLO: gauges (mlops_slo_*) or histogram (histogram_quantile + rate); see Settings.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or httpx.Client(timeout=30.0)

    def pull_deployments(self) -> dict[str, list[dict[str, Any]]]:
        promql = self._settings.prometheus_deployment_promql
        try:
            rows = query_instant(
                self._settings.prometheus_base_url,
                promql,
                client=self._client,
            )
        except PrometheusError:
            return {}

        catalog: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            labels = row["labels"]
            service = labels.get("service")
            if not service:
                continue
            traffic = row["value"]
            catalog[service].append(
                {
                    "version": labels.get("version", "unknown"),
                    "channel": labels.get("channel", "stable"),
                    "traffic_pct": int(round(traffic)),
                    "deployed_at_utc": labels.get("deployed_at", "prometheus"),
                    "status": labels.get("status", "active"),
                }
            )

        for service in catalog:
            catalog[service].sort(key=lambda d: d["traffic_pct"], reverse=True)
        return dict(catalog)

    def pull_slo_snapshot(self) -> dict[str, dict[str, dict[str, Any]]]:
        snapshot: dict[str, dict[str, dict[str, Any]]] = {}
        window = self._settings.prometheus_slo_window_minutes
        latency_base = self._settings.prometheus_latency_baseline_ms
        error_base = self._settings.prometheus_error_baseline_pct

        for service in self._settings.prometheus_service_list():
            latency_q = self._settings.slo_latency_query(service)
            error_q = self._settings.slo_error_query(service)

            try:
                lat_rows = query_instant(
                    self._settings.prometheus_base_url,
                    latency_q,
                    client=self._client,
                )
                err_rows = query_instant(
                    self._settings.prometheus_base_url,
                    error_q,
                    client=self._client,
                )
            except PrometheusError:
                continue

            if not lat_rows and not err_rows:
                continue

            service_block: dict[str, dict[str, Any]] = {}
            if lat_rows:
                current_ms = float(lat_rows[0]["value"])
                service_block["latency_p99"] = {
                    "current_ms": current_ms,
                    "baseline_ms": latency_base,
                    "window_minutes": window,
                    "slo_breached": current_ms > latency_base,
                }
            if err_rows:
                current_pct = float(err_rows[0]["value"])
                service_block["error_rate_503"] = {
                    "current_pct": current_pct,
                    "baseline_pct": error_base,
                    "window_minutes": window,
                    "slo_breached": current_pct > error_base,
                }
            if service_block:
                snapshot[service] = service_block

        return snapshot
