from __future__ import annotations

from typing import Literal

PrometheusSloQueryMode = Literal["gauges", "histogram"]


def histogram_latency_p99_promql(
    *,
    service: str,
    window_minutes: int,
    duration_metric: str,
    service_label: str = "service",
    quantile: float = 0.99,
) -> str:
    window = f"{window_minutes}m"
    selector = f'{duration_metric}{{{service_label}="{service}"}}'
    return (
        f"histogram_quantile({quantile}, "
        f"sum(rate({selector}[{window}])) by (le)) * 1000"
    )


def histogram_error_rate_503_promql(
    *,
    service: str,
    window_minutes: int,
    requests_metric: str,
    service_label: str = "service",
    status_label: str = "status",
    status_value: str = "503",
) -> str:
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
