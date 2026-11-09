import json

import httpx

from mlops_triage.config import Settings
from mlops_triage.sync.prometheus_adapter import PrometheusAdapter
from mlops_triage.sync.prometheus_client import PrometheusError, query_instant
from mlops_triage.sync.refresh import refresh_snapshots


def _prom_response(samples: list[dict]) -> dict:
    return {
        "status": "success",
        "data": {
            "result": [
                {
                    "metric": item["metric"],
                    "value": [1_700_000_000, str(item["value"])],
                }
                for item in samples
            ]
        },
    }


def test_query_instant_parses_vector():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/api/v1/query")
        return httpx.Response(
            200,
            json=_prom_response(
                [{"metric": {"service": "svc-a"}, "value": 42.5}],
            ),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    rows = query_instant("http://prom:9090", "up", client=client)
    assert rows[0]["labels"]["service"] == "svc-a"
    assert rows[0]["value"] == 42.5


def test_prometheus_adapter_builds_catalog_and_slo():
    queries: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        promql = request.url.params.get("query", "")
        queries[request.url.params.get("query", "")] = promql
        if promql == "mlops_deployment_traffic_pct":
            payload = _prom_response(
                [
                    {
                        "metric": {
                            "service": "rec-engine",
                            "version": "9.0.0",
                            "channel": "canary",
                            "deployed_at": "2026-03-09T12:00:00Z",
                        },
                        "value": 15,
                    },
                ]
            )
            return httpx.Response(200, json=payload)
        if "mlops_slo_latency_p99_ms" in promql:
            return httpx.Response(
                200,
                json=_prom_response([{"metric": {"service": "rec-engine"}, "value": 500}]),
            )
        if "mlops_slo_error_rate_503_pct" in promql:
            return httpx.Response(
                200,
                json=_prom_response([{"metric": {"service": "rec-engine"}, "value": 0.2}]),
            )
        raise AssertionError(f"unexpected promql: {promql}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(prometheus_services="rec-engine", prometheus_slo_query_mode="gauges")
    adapter = PrometheusAdapter(settings, client=client)

    deployments = adapter.pull_deployments()
    slo = adapter.pull_slo_snapshot()

    assert deployments["rec-engine"][0]["version"] == "9.0.0"
    assert slo["rec-engine"]["latency_p99"]["slo_breached"] is True
    assert slo["rec-engine"]["error_rate_503"]["slo_breached"] is True
    assert "mlops_deployment_traffic_pct" in queries.values()


def test_refresh_snapshots_prometheus_adapter(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        promql = request.url.params.get("query", "")
        if promql == "mlops_deployment_traffic_pct":
            return httpx.Response(200, json=_prom_response([]))
        if "latency" in promql:
            return httpx.Response(
                200,
                json=_prom_response([{"metric": {"service": "serving-prod-eu"}, "value": 90}]),
            )
        if "error" in promql:
            return httpx.Response(
                200,
                json=_prom_response([{"metric": {"service": "serving-prod-eu"}, "value": 0.01}]),
            )
        return httpx.Response(200, json={"status": "success", "data": {"result": []}})

    settings = Settings(
        deployments_file=tmp_path / "deployments.json",
        slo_snapshot_file=tmp_path / "slo.json",
        prometheus_services="serving-prod-eu",
        prometheus_slo_query_mode="gauges",
    )
    adapter = PrometheusAdapter(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))
    refresh_snapshots(settings=settings, adapter="prometheus", adapter_instance=adapter)

    slo = json.loads((tmp_path / "slo.json").read_text(encoding="utf-8"))
    assert slo["serving-prod-eu"]["latency_p99"]["slo_breached"] is False


def test_prometheus_adapter_request_traffic_deployments():
    def handler(request: httpx.Request) -> httpx.Response:
        promql = request.url.params.get("query", "")
        if "sum(rate" in promql and 'service="rec-engine"' in promql:
            return httpx.Response(
                200,
                json=_prom_response(
                    [
                        {"metric": {"version": "3.8.1"}, "value": 120},
                        {"metric": {"version": "3.8.0"}, "value": 880},
                    ]
                ),
            )
        return httpx.Response(200, json={"status": "success", "data": {"result": []}})

    settings = Settings(
        prometheus_services="rec-engine",
        prometheus_deployment_query_mode="request_traffic",
        prometheus_slo_query_mode="gauges",
        prometheus_latency_promql="mlops_slo_latency_p99_ms{service='{service}'}",
        prometheus_error_promql="mlops_slo_error_rate_503_pct{service='{service}'}",
    )
    adapter = PrometheusAdapter(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))
    catalog = adapter.pull_deployments()
    assert catalog["rec-engine"][0]["traffic_pct"] == 88
    assert catalog["rec-engine"][1]["version"] == "3.8.1"


def test_prometheus_adapter_kube_replica_deployments():
    def handler(request: httpx.Request) -> httpx.Response:
        promql = request.url.params.get("query", "")
        if "kube_deployment_status_replicas_available" in promql:
            return httpx.Response(
                200,
                json=_prom_response(
                    [
                        {"metric": {"deployment": "rec-engine-v381"}, "value": 2},
                        {"metric": {"deployment": "rec-engine-v380"}, "value": 8},
                    ]
                ),
            )
        return httpx.Response(200, json={"status": "success", "data": {"result": []}})

    settings = Settings(
        prometheus_services="rec-engine",
        prometheus_deployment_query_mode="kube_replicas",
        prometheus_kube_deployment_regex_template="rec-engine.*",
    )
    adapter = PrometheusAdapter(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))
    catalog = adapter.pull_deployments()
    assert catalog["rec-engine"][0]["traffic_pct"] == 80


def test_prometheus_adapter_histogram_mode():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        promql = request.url.params.get("query", "")
        captured.append(promql)
        if "histogram_quantile" in promql:
            return httpx.Response(200, json=_prom_response([{"metric": {}, "value": 2.5}]))
        if "clamp_min" in promql:
            return httpx.Response(200, json=_prom_response([{"metric": {}, "value": 0.05}]))
        return httpx.Response(200, json={"status": "success", "data": {"result": []}})

    settings = Settings(
        prometheus_services="serving-prod-eu",
        prometheus_slo_query_mode="histogram",
        prometheus_slo_window_minutes=15,
    )
    adapter = PrometheusAdapter(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))
    slo = adapter.pull_slo_snapshot()

    assert any("histogram_quantile" in q for q in captured)
    assert slo["serving-prod-eu"]["latency_p99"]["current_ms"] == 2.5
    assert slo["serving-prod-eu"]["latency_p99"]["slo_breached"] is False
    assert slo["serving-prod-eu"]["error_rate_503"]["slo_breached"] is False


def test_query_instant_raises_on_http_error():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    try:
        query_instant("http://prom:9090", "up", client=client)
    except PrometheusError as exc:
        assert "failed" in str(exc).lower()
    else:
        raise AssertionError("expected PrometheusError")
