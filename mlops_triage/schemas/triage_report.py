from typing import Literal

from pydantic import BaseModel, Field


class TriageReport(BaseModel):
    """Final on-call triage after investigating an ML serving incident."""

    incident_summary: str
    root_cause_hypothesis: str
    recommended_actions: list[str] = Field(min_length=1)
    rollback_recommended: bool
    priority: Literal["P1", "P2", "P3", "P4"]
    runbook_sources: list[str] = Field(
        default_factory=list,
        description="Runbook markdown filenames cited for recommended actions",
    )
