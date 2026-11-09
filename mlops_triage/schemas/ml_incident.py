from typing import Literal

from pydantic import BaseModel, Field


class MLIncident(BaseModel):
    """Structured extraction from free-text ML platform logs or alerts."""

    severity: Literal["low", "medium", "high", "critical"]
    component: str = Field(
        description="Subsystem affected, e.g. training, serving, data, monitoring",
    )
    summary: str = Field(description="One-sentence incident summary")
    suggested_actions: list[str] = Field(
        min_length=1,
        description="Concrete next steps for an on-call engineer",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model self-rated confidence in the extraction",
    )
