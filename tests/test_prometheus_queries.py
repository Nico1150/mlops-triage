import pytest
from pydantic import ValidationError

from mlops_triage.config import Settings
from mlops_triage.sync.prometheus_queries import (
    histogram_error_rate_by_label_promql,
    histogram_latency_quantile_promql,
)


def test_histogram_latency_quantile_promql_shape():
    q = histogram_latency_quantile_promql(
        service="serving-prod-eu",
        window_minutes=15,
        duration_metric="http_request_duration_seconds_bucket",
    )
    assert "histogram_quantile(0.99" in q
    assert 'service="serving-prod-eu"' in q
    assert "[15m]" in q
    assert "* 1000" in q


def test_histogram_latency_quantile_custom_quantile():
    q = histogram_latency_quantile_promql(
        service="svc",
        window_minutes=15,
        duration_metric="http_request_duration_seconds_bucket",
        quantile=0.95,
    )
    assert "histogram_quantile(0.95" in q


def test_histogram_error_rate_by_label_promql_shape():
    q = histogram_error_rate_by_label_promql(
        service="rec-engine",
        window_minutes=5,
        requests_metric="http_requests_total",
    )
    assert 'status="503"' in q
    assert "clamp_min" in q
    assert "[5m]" in q


def test_histogram_error_rate_by_label_custom_filter():
    q = histogram_error_rate_by_label_promql(
        service="svc",
        window_minutes=15,
        requests_metric="rpc_server_duration_seconds_count",
        status_label="grpc_code",
        status_value="UNAVAILABLE",
    )
    assert 'grpc_code="UNAVAILABLE"' in q


def test_settings_slo_queries_histogram_default():
    settings = Settings(prometheus_slo_query_mode="histogram")
    lat = settings.slo_latency_query("rec-engine")
    err = settings.slo_error_query("rec-engine")
    assert "histogram_quantile" in lat
    assert "http_requests_total" in err


def test_settings_slo_queries_gauges_mode():
    settings = Settings(prometheus_slo_query_mode="gauges")
    assert "mlops_slo_latency_p99_ms" in settings.slo_latency_query("svc")
    assert "mlops_slo_error_rate_503_pct" in settings.slo_error_query("svc")


def test_settings_custom_promql_override():
    settings = Settings(
        prometheus_slo_query_mode="histogram",
        prometheus_latency_promql='custom_latency{{service="{service}"}}',
    )
    assert settings.slo_latency_query("x") == 'custom_latency{service="x"}'


def test_invalid_slo_query_mode_raises():
    with pytest.raises(ValidationError):
        Settings(prometheus_slo_query_mode="invalid")
