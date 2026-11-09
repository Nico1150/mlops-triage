from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mlops_triage.sync.prometheus_queries import (
    PrometheusDeploymentQueryMode,
    PrometheusSloQueryMode,
    default_gauge_deployment_promql,
    default_gauge_error_promql,
    default_gauge_latency_promql,
    deployment_kube_replicas_by_name_promql,
    deployment_request_traffic_by_label_promql,
    histogram_error_rate_by_label_promql,
    histogram_latency_quantile_promql,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _default_deployments_file() -> Path:
    return _REPO_ROOT / "data" / "deployments.json"


def _default_slo_snapshot_file() -> Path:
    return _REPO_ROOT / "data" / "slo_snapshot.json"


def _default_runbooks_dir() -> Path:
    return _REPO_ROOT / "data" / "runbooks"


def _default_rag_index_file() -> Path:
    return _REPO_ROOT / "data" / "rag_index.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    deployments_file: Path = Field(default_factory=_default_deployments_file)
    slo_snapshot_file: Path = Field(default_factory=_default_slo_snapshot_file)
    runbooks_dir: Path = Field(default_factory=_default_runbooks_dir)
    rag_index_file: Path = Field(default_factory=_default_rag_index_file)
    embedding_model: str = "nomic-embed-text"

    prometheus_base_url: str = "http://localhost:9090"
    prometheus_services: str = "rec-engine,serving-prod-eu"
    prometheus_slo_window_minutes: int = 15
    prometheus_latency_baseline_ms: float = 120.0
    prometheus_error_baseline_pct: float = 0.1
    prometheus_deployment_promql: str = ""
    prometheus_deployment_query_mode: PrometheusDeploymentQueryMode = "gauges"
    prometheus_deployment_requests_metric: str = "http_requests_total"
    prometheus_deployment_version_label: str = "version"
    prometheus_deployment_channel_label: str = ""
    prometheus_kube_namespace: str = "default"
    prometheus_kube_deployment_label: str = "deployment"
    prometheus_kube_replicas_metric: str = "kube_deployment_status_replicas_available"
    prometheus_kube_deployment_regex_template: str = "{service}.*"
    prometheus_slo_query_mode: PrometheusSloQueryMode = "histogram"
    prometheus_latency_promql: str = ""
    prometheus_error_promql: str = ""
    prometheus_service_label: str = "service"
    prometheus_histogram_duration_metric: str = "http_request_duration_seconds_bucket"
    prometheus_histogram_requests_metric: str = "http_requests_total"
    prometheus_error_status_label: str = "status"
    prometheus_error_status_value: str = "503"
    prometheus_latency_quantile: float = 0.99

    @field_validator("prometheus_slo_query_mode", mode="before")
    @classmethod
    def _normalize_slo_query_mode(cls, value: object) -> str:
        raw = str(value or "histogram").strip().lower()
        if raw not in ("gauges", "histogram"):
            raise ValueError("prometheus_slo_query_mode must be 'gauges' or 'histogram'")
        return raw

    @field_validator("prometheus_deployment_query_mode", mode="before")
    @classmethod
    def _normalize_deployment_query_mode(cls, value: object) -> str:
        raw = str(value or "gauges").strip().lower()
        if raw not in ("gauges", "request_traffic", "kube_replicas"):
            raise ValueError(
                "prometheus_deployment_query_mode must be gauges, request_traffic, or kube_replicas"
            )
        return raw

    def prometheus_service_list(self) -> list[str]:
        return [s.strip() for s in self.prometheus_services.split(",") if s.strip()]

    def _format_custom_promql(self, template: str, service: str) -> str:
        return template.format(
            service=service,
            window_minutes=self.prometheus_slo_window_minutes,
            window=f"{self.prometheus_slo_window_minutes}m",
            quantile=self.prometheus_latency_quantile,
            error_label=self.prometheus_error_status_label,
            error_value=self.prometheus_error_status_value,
        )

    def slo_latency_query(self, service: str) -> str:
        custom = self.prometheus_latency_promql.strip()
        if custom:
            return self._format_custom_promql(custom, service)
        if self.prometheus_slo_query_mode == "histogram":
            return histogram_latency_quantile_promql(
                service=service,
                window_minutes=self.prometheus_slo_window_minutes,
                duration_metric=self.prometheus_histogram_duration_metric,
                service_label=self.prometheus_service_label,
                quantile=self.prometheus_latency_quantile,
            )
        return default_gauge_latency_promql(service)

    def slo_error_query(self, service: str) -> str:
        custom = self.prometheus_error_promql.strip()
        if custom:
            return self._format_custom_promql(custom, service)
        if self.prometheus_slo_query_mode == "histogram":
            return histogram_error_rate_by_label_promql(
                service=service,
                window_minutes=self.prometheus_slo_window_minutes,
                requests_metric=self.prometheus_histogram_requests_metric,
                service_label=self.prometheus_service_label,
                status_label=self.prometheus_error_status_label,
                status_value=self.prometheus_error_status_value,
            )
        return default_gauge_error_promql(service)

    def deployment_channel_label(self) -> str | None:
        label = self.prometheus_deployment_channel_label.strip()
        return label or None

    def _format_deployment_promql(self, template: str, service: str) -> str:
        return template.format(
            service=service,
            window_minutes=self.prometheus_slo_window_minutes,
            window=f"{self.prometheus_slo_window_minutes}m",
            namespace=self.prometheus_kube_namespace,
            version_label=self.prometheus_deployment_version_label,
        )

    def kube_deployment_match_regex(self, service: str) -> str:
        return self.prometheus_kube_deployment_regex_template.format(service=service)

    def deployment_gauge_query(self) -> str:
        custom = self.prometheus_deployment_promql.strip()
        return custom or default_gauge_deployment_promql()

    def deployment_request_traffic_query(self, service: str) -> str:
        custom = self.prometheus_deployment_promql.strip()
        if custom:
            return self._format_deployment_promql(custom, service)
        return deployment_request_traffic_by_label_promql(
            service=service,
            window_minutes=self.prometheus_slo_window_minutes,
            requests_metric=self.prometheus_deployment_requests_metric,
            service_label=self.prometheus_service_label,
            group_by_label=self.prometheus_deployment_version_label,
        )

    def deployment_kube_replicas_query(self, service: str) -> str:
        custom = self.prometheus_deployment_promql.strip()
        if custom:
            return self._format_deployment_promql(custom, service)
        return deployment_kube_replicas_by_name_promql(
            namespace=self.prometheus_kube_namespace,
            deployment_match_regex=self.kube_deployment_match_regex(service),
            replicas_metric=self.prometheus_kube_replicas_metric,
            deployment_label=self.prometheus_kube_deployment_label,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
