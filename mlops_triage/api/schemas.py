from typing import Any

from pydantic import BaseModel, Field

from mlops_triage.schemas.ml_incident import MLIncident
from mlops_triage.schemas.triage_report import TriageReport


class TriageRequest(BaseModel):
    alert: str = Field(min_length=1, description="Raw alert or log text")
    use_runbooks: bool = True
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_agent_steps: int = Field(default=18, ge=4, le=40)


class RunbookHitOut(BaseModel):
    chunk_id: str
    source_file: str
    title: str
    score: float


class TriageResponse(BaseModel):
    incident: MLIncident
    triage: TriageReport
    runbook_hits: list[RunbookHitOut] = Field(default_factory=list)


def pipeline_result_to_response(result: Any) -> TriageResponse:
    hits = [
        RunbookHitOut(
            chunk_id=h["chunk_id"],
            source_file=h["source_file"],
            title=h["title"],
            score=float(h["score"]),
        )
        for h in result.runbook_hits
    ]
    return TriageResponse(
        incident=result.incident,
        triage=result.triage,
        runbook_hits=hits,
    )
