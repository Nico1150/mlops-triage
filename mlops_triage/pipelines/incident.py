from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from mlops_triage.agent import AgentError, run_agent
from mlops_triage.config import Settings, get_settings
from mlops_triage.llm import complete_structured, create_openai_client
from mlops_triage.rag.context import format_runbook_context, runbook_source_names
from mlops_triage.rag.search import ensure_runbook_index, search_runbooks
from mlops_triage.schemas.ml_incident import MLIncident
from mlops_triage.schemas.triage_report import TriageReport
from mlops_triage.tools import default_mlops_tools

TRIAGE_SYSTEM_PROMPT = """\
You are an on-call MLOps engineer triaging production ML serving incidents.

You receive a structured incident and runbook excerpts. Use tools to verify
deployment and SLO context (do not invent metrics). Call search_runbook if you
need more procedures beyond the excerpts. Align recommended_actions with runbooks
when applicable and list filenames in runbook_sources. Then submit_triage_report once.

Prefer service names rec-engine and serving-prod-eu for serving incidents.
"""


@dataclass(frozen=True)
class IncidentPipelineResult:
    incident: MLIncident
    triage: TriageReport
    runbook_hits: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def _runbook_context_for_alert(
    alert: str,
    *,
    client: OpenAI,
    settings: Settings,
    top_k: int,
) -> dict[str, object]:
    ensure_runbook_index(client=client, settings=settings)
    return search_runbooks(
        alert.strip(),
        top_k=top_k,
        client=client,
        settings=settings,
    )


def run_incident_pipeline(
    alert: str,
    *,
    client: OpenAI | None = None,
    settings: Settings | None = None,
    temperature: float = 0.2,
    max_agent_steps: int = 18,
    use_runbooks: bool = True,
    runbook_top_k: int = 3,
) -> IncidentPipelineResult:
    """Extract MLIncident, enrich with runbook RAG, then run tool-calling triage."""
    cfg = settings or get_settings()
    llm = client or create_openai_client(cfg)

    runbook_result: dict[str, object] | None = None
    runbook_block = ""
    if use_runbooks:
        runbook_result = _runbook_context_for_alert(
            alert,
            client=llm,
            settings=cfg,
            top_k=runbook_top_k,
        )
        runbook_block = format_runbook_context(runbook_result)

    extraction_user = (
        f"Extract an incident report from the following alert text:\n\n{alert.strip()}"
    )
    if runbook_block:
        extraction_user += (
            "\n\nRelevant runbook excerpts (use only as supporting context):\n\n"
            f"{runbook_block}"
        )

    incident = complete_structured(
        client=llm,
        model=cfg.llm_model,
        messages=[{"role": "user", "content": extraction_user}],
        response_model=MLIncident,
        temperature=temperature,
    )

    agent_user = (
        "Triage this structured incident and submit a report.\n\n"
        f"Alert (reference):\n{alert.strip()}\n\n"
        f"Structured incident:\n{incident.model_dump_json(indent=2)}"
    )
    if runbook_block:
        agent_user += (
            "\n\nRunbook excerpts (already retrieved):\n\n"
            f"{runbook_block}\n\n"
            f"Suggested runbook_sources if applicable: {runbook_source_names(runbook_result or {})}"
        )

    tools = default_mlops_tools()
    agent_result = run_agent(
        client=llm,
        model=cfg.llm_model,
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": agent_user},
        ],
        tools=tools,
        temperature=temperature,
        max_steps=max_agent_steps,
        terminal_tool="submit_triage_report",
    )

    if not isinstance(agent_result, TriageReport):
        raise AgentError("Pipeline agent finished without a TriageReport")

    hits = tuple((runbook_result or {}).get("hits") or ())
    return IncidentPipelineResult(incident=incident, triage=agent_result, runbook_hits=hits)
