from __future__ import annotations

from typing import Any

import httpx


class PrometheusError(RuntimeError):
    pass


def query_instant(
    base_url: str,
    promql: str,
    *,
    client: httpx.Client,
) -> list[dict[str, Any]]:
    """Run a Prometheus instant query; return [{labels, value}, ...]."""
    url = f"{base_url.rstrip('/')}/api/v1/query"
    try:
        response = client.get(url, params={"query": promql})
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PrometheusError(f"Prometheus request failed: {exc}") from exc

    body = response.json()
    if body.get("status") != "success":
        raise PrometheusError(body.get("error") or "Prometheus query failed")

    rows: list[dict[str, Any]] = []
    for item in body.get("data", {}).get("result", []):
        labels = dict(item.get("metric") or {})
        raw = item.get("value")
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        try:
            value = float(raw[1])
        except (TypeError, ValueError):
            continue
        rows.append({"labels": labels, "value": value})
    return rows
