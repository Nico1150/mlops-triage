from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from mlops_triage.agent import AgentError
from mlops_triage.api import health as health_checks
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
def health(deep: bool = False):
    settings = get_settings()
    if not deep:
        return health_checks.shallow_health_payload(settings)
    payload = health_checks.deep_health_payload(settings)
    return JSONResponse(payload, status_code=health_checks.deep_health_http_status(payload))


@app.get("/ready")
def ready():
    """Readiness: deep checks; 503 when LLM or required snapshots are missing."""
    settings = get_settings()
    payload = health_checks.deep_health_payload(settings)
    return JSONResponse(payload, status_code=health_checks.deep_health_http_status(payload))


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
