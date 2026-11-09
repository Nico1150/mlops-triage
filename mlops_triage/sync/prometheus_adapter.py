from __future__ import annotations

from typing import Any

import httpx

from mlops_triage.config import Settings, get_settings
from mlops_triage.sync.adapters import SnapshotAdapter
from mlops_triage.sync.deployment_catalog import (
    catalog_from_gauge_rows,
    catalog_from_kube_replica_rows,
    catalog_from_request_traffic_rows,
)
from mlops_triage.sync.prometheus_client import PrometheusError, query_instant


class PrometheusAdapter(SnapshotAdapter):
    """
    Pulls tool snapshots from Prometheus instant queries.

    Deployments: gauges, request-traffic by version, or kube-state replica share.
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
        mode = self._settings.prometheus_deployment_query_mode
        channel_label = self._settings.deployment_channel_label()

        try:
            if mode == "gauges":
                rows = query_instant(
                    self._settings.prometheus_base_url,
                    self._settings.deployment_gauge_query(),
                    client=self._client,
                )
                return catalog_from_gauge_rows(rows)

            catalog: dict[str, list[dict[str, Any]]] = {}
            for service in self._settings.prometheus_service_list():
                if mode == "request_traffic":
                    promql = self._settings.deployment_request_traffic_query(service)
                    rows = query_instant(
                        self._settings.prometheus_base_url,
                        promql,
                        client=self._client,
                    )
                    entries = catalog_from_request_traffic_rows(
                        rows,
                        service=service,
                        version_label=self._settings.prometheus_deployment_version_label,
                        channel_label=channel_label,
                    )
                elif mode == "kube_replicas":
                    promql = self._settings.deployment_kube_replicas_query(service)
                    rows = query_instant(
                        self._settings.prometheus_base_url,
                        promql,
                        client=self._client,
                    )
                    entries = catalog_from_kube_replica_rows(
                        rows,
                        service=service,
                        deployment_label=self._settings.prometheus_kube_deployment_label,
                        channel_label=channel_label,
                    )
                else:
                    entries = []

                if entries:
                    catalog[service] = entries
            return catalog
        except PrometheusError:
            return {}

    def pull_slo_snapshot(self) -> dict[str, dict[str, dict[str, Any]]]:
        snapshot: dict[str, dict[str, dict[str, Any]]] = {}
        latency_base = self._settings.prometheus_latency_baseline_ms
        error_base = self._settings.prometheus_error_baseline_pct
        window = self._settings.prometheus_slo_window_minutes

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
