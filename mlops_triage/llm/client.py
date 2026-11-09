from openai import OpenAI

from mlops_triage.config import Settings, get_settings


def create_openai_client(settings: Settings | None = None) -> OpenAI:
    cfg = settings or get_settings()
    return OpenAI(
        base_url=cfg.llm_base_url,
        api_key=cfg.llm_api_key,
    )
