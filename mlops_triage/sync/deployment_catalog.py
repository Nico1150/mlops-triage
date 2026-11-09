from __future__ import annotations

from typing import Any


def catalog_from_gauge_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Parse mlops_deployment_traffic_pct-style gauges (service label on each series)."""
    catalog: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        labels = row["labels"]
        service = labels.get("service")
        if not service:
            continue
        catalog.setdefault(service, []).append(
            {
                "version": labels.get("version", "unknown"),
                "channel": labels.get("channel", "stable"),
                "traffic_pct": int(round(float(row["value"]))),
                "deployed_at_utc": labels.get("deployed_at", "prometheus"),
                "status": labels.get("status", "active"),
            }
        )
    for service in catalog:
        catalog[service].sort(key=lambda d: d["traffic_pct"], reverse=True)
    return catalog


def _share_rows_to_deployments(
    rows: list[dict[str, Any]],
    *,
    version_key: str,
    channel_label: str | None,
    service: str,
    source: str,
) -> list[dict[str, Any]]:
    positive = [r for r in rows if float(r["value"]) > 0]
    total = sum(float(r["value"]) for r in positive)
    if total <= 0:
        return []

    shares = sorted(
        (
            {
                "labels": r["labels"],
                "traffic_pct": 100.0 * float(r["value"]) / total,
            }
            for r in positive
        ),
        key=lambda x: x["traffic_pct"],
        reverse=True,
    )
    rounded: list[dict[str, Any]] = []
    for idx, item in enumerate(shares):
        labels = item["labels"]
        pct = int(round(item["traffic_pct"]))
        version = labels.get(version_key) or labels.get("deployment", "unknown")
        if channel_label and labels.get(channel_label):
            channel = str(labels[channel_label])
        else:
            channel = "stable" if idx == 0 and pct >= 50 else ("canary" if pct > 0 else "stable")
        rounded.append(
            {
                "version": str(version),
                "channel": channel,
                "traffic_pct": pct,
                "deployed_at_utc": labels.get("deployed_at", source),
                "status": labels.get("status", "active"),
            }
        )
    return _normalize_traffic_pcts(rounded)


def _normalize_traffic_pcts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    total = sum(r["traffic_pct"] for r in rows)
    if total == 100 or total == 0:
        return rows
    rows[0]["traffic_pct"] += 100 - total
    return rows


def version_from_kube_deployment(deployment: str, service: str) -> str:
    prefix = f"{service}-"
    if deployment.startswith(prefix):
        suffix = deployment[len(prefix) :]
        return suffix or deployment
    return deployment


def catalog_from_request_traffic_rows(
    rows: list[dict[str, Any]],
    *,
    service: str,
    version_label: str,
    channel_label: str | None,
) -> list[dict[str, Any]]:
    return _share_rows_to_deployments(
        rows,
        version_key=version_label,
        channel_label=channel_label,
        service=service,
        source="prometheus-traffic",
    )


def catalog_from_kube_replica_rows(
    rows: list[dict[str, Any]],
    *,
    service: str,
    deployment_label: str,
    channel_label: str | None,
) -> list[dict[str, Any]]:
    for row in rows:
        dep = row["labels"].get(deployment_label, "")
        row["labels"] = {**row["labels"], "version": version_from_kube_deployment(dep, service)}
    return _share_rows_to_deployments(
        rows,
        version_key="version",
        channel_label=channel_label,
        service=service,
        source="prometheus-kube",
    )
