from __future__ import annotations

from typing import Literal

PrometheusSloQueryMode = Literal["gauges", "histogram"]


def histogram_latency_quantile_promql(
    *,
    service: str,
    window_minutes: int,
    duration_metric: str,
    service_label: str = "service",
    quantile: float = 0.99,
) -> str:
    """Latency from a histogram bucket metric; quantile is configurable (p50, p95, p99, …)."""
    window = f"{window_minutes}m"
    selector = f'{duration_metric}{{{service_label}="{service}"}}'
    return (
        f"histogram_quantile({quantile}, "
        f"sum(rate({selector}[{window}])) by (le)) * 1000"
    )


def histogram_error_rate_by_label_promql(
    *,
    service: str,
    window_minutes: int,
    requests_metric: str,
    service_label: str = "service",
    status_label: str = "status",
    status_value: str = "503",
) -> str:
    """Error share over request traffic; filter errors via any label pair (HTTP status, gRPC code, …)."""
    window = f"{window_minutes}m"
    errors = (
        f'sum(rate({requests_metric}{{{service_label}="{service}",'
        f'{status_label}="{status_value}"}}[{window}]))'
    )
    total = f'sum(rate({requests_metric}{{{service_label}="{service}"}}[{window}]))'
    return f"100 * {errors} / clamp_min({total}, 1e-9)"


def default_gauge_latency_promql(service: str) -> str:
    return f'mlops_slo_latency_p99_ms{{service="{service}"}}'


def default_gauge_error_promql(service: str) -> str:
    return f'mlops_slo_error_rate_503_pct{{service="{service}"}}'
