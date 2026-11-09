from fastapi import FastAPI, HTTPException

from mlops_triage.agent import AgentError
from mlops_triage.api.schemas import TriageRequest, TriageResponse, pipeline_result_to_response
from mlops_triage.config import get_settings
from mlops_triage.llm.structured import StructuredOutputError
from mlops_triage.pipelines import run_incident_pipeline

app = FastAPI(
    title="mlops-triage",
    description="MLOps incident triage via local OpenAI-compatible LLM backends",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "llm_model": settings.llm_model,
        "llm_base_url": settings.llm_base_url,
        "embedding_model": settings.embedding_model,
    }


@app.post("/triage", response_model=TriageResponse)
def triage(request: TriageRequest) -> TriageResponse:
    try:
        result = run_incident_pipeline(
            request.alert,
            temperature=request.temperature,
            use_runbooks=request.use_runbooks,
            max_agent_steps=request.max_agent_steps,
        )
    except (AgentError, StructuredOutputError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return pipeline_result_to_response(result)
