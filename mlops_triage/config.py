from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    prometheus_deployment_promql: str = "mlops_deployment_traffic_pct"
    prometheus_latency_promql: str = 'mlops_slo_latency_p99_ms{{service="{service}"}}'
    prometheus_error_promql: str = 'mlops_slo_error_rate_503_pct{{service="{service}"}}'

    def prometheus_service_list(self) -> list[str]:
        return [s.strip() for s in self.prometheus_services.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
